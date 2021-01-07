from asocket import ASocketServer
from multiprocessing import Process, Pipe
import consts
import os
import select
import socket


class DelegateProtocol:
    def connection_made(self, trans):
        print("connected on process")

    def connection_lost(self):
        print("lost connection")

    def data_received(self, data):
        print("got", data, "on process")


class Delegate:
    def __init__(self, master, delay, recv_size, prot):
        self.master = master
        self.delay = delay
        self.recv_size = recv_size
        self.prot = prot()
        self.ident = os.getpid()

        self.sockets = {}
        
        self.serve_forever()

    def serve_forever(self):
        while 1:
            if not self.master.poll(self.delay/1000):
                for fd, pair in self.sockets.copy().items():
                    sock, poll = pair
                    if not (ev := poll.poll(self.delay)):
                        continue
                    elif ev[0][1] & select.POLLHUP:
                        sock.close()
                        del self.sockets[fd]
                        self.prot.connection_lost()
                    elif ev[0][1] & select.POLLIN:
                        data = sock.recv(self.recv_size)
                        while (ev := poll.poll(self.delay)) and ev[0][1] & select.POLLIN:
                            data += sock.recv(self.recv_size)
                        self.prot.data_received(data)
                continue

            event = self.master.recv()
            if event['status'] == consts.MSTR_COMMS['new']:
                unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
                unix.connect(event['content'])

                self.master.send({
                    "status": consts.SLAVE_COMMS['ack']
                    })
                msg, fds, *_ = socket.recv_fds(unix, 1, 1)
                newfd = os.dup(fds[0])
                
                self.sockets[newfd] = [(s := socket.socket(fileno=newfd)), (p := select.poll())]
                p.register(s, select.POLLIN | select.POLLOUT)

                unix.close()
                self.master.send({
                    "status": consts.SLAVE_COMMS['ack']
                    })
                continue


class DelegatorProtocol:
    def __init__(self, bin_count, delay, recv_size):
        self.procs = []
        self.bin_count = bin_count
        for _ in range(bin_count):
            master, slave = Pipe()
            self.procs.append( ((p := Process(target=Delegate, args=(
                    slave, delay, recv_size, DelegateProtocol
                ))), master) )
            p.start()
        self.curr_idx = 0
    
    @staticmethod
    def ack(pipe):
        if not pipe.poll(1):
            return False
        return pipe.recv()['status'] == consts.SLAVE_COMMS['ack']

    def connection_made(self, trans):
        proc, pipe = self.procs[self.curr_idx]
        print("delegating socket to", proc.pid)
        socket_file = f"/tmp/{proc.pid}.socket"
        
        unix = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        unix.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        unix.bind(socket_file)
        unix.listen(1)

        pipe.send({
            "status": consts.MSTR_COMMS['new'],
            "content": socket_file
            })

        if not self.ack(pipe):
            trans.close()
            unix.close()
            return

        conn, _ = unix.accept()
        socket.send_fds(conn, [b'\0'], [trans.fileno()])
        if not self.ack(pipe):
            conn.close()
            unix.close()
            trans.close()
            return
        
        unix.close()
        os.remove(socket_file)
        trans.close()
        conn.close()
        
        self.curr_idx += 1
        self.curr_idx %= self.bin_count


def start_delegating(host, port, *args, bin_count=os.cpu_count(), **kwargs):
        server = ASocketServer(host, port, *args, **kwargs)
        server.listen_and_accept(DelegatorProtocol(bin_count, server.delay, server.recv_size))


if __name__ == "__main__":
    print("starting server")
    start_delegating('', 32768)
