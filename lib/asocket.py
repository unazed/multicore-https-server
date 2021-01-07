import select, socket


class ASocketServer:
    def __init__(self, host, port, backlog=10, delay=100, recv_size=1024):
        self.socket = socket.socket()
        self.socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.socket.bind((host, port))
        
        self.backlog = backlog
        self.delay = delay
        self.recv_size = recv_size

        self.server_poll = select.poll()
        self.server_poll.register(self.socket, select.POLLIN)

        self.receivers = []

    def listen_and_accept(self, protocol):
        self.socket.listen(self.backlog)
        while 1:
            if not self.server_poll.poll(self.delay):
                for receiver in self.receivers:
                    prot, conn, poll = receiver
                    event = poll.poll(self.delay)
                    if not event:
                        continue
                    elif event[0][1] & select.POLLHUP or event[0][1] & select.POLLRDHUP:
                        self.receivers.remove(receiver)
                        conn.close()
                        prot.connection_lost()
                    elif event[0][1] & select.POLLIN:
                        data = conn.recv(self.recv_size)
                        while (ev := poll.poll(self.delay)) and ev[0][1] & select.POLLIN:
                            print("receiving chunk")
                            data += conn.recv(self.recv_size)
                        prot.data_received(data)
                continue
            conn, _ = self.socket.accept()
            poll = select.poll()
            poll.register(conn, select.POLLIN | select.POLLHUP | select.POLLRDHUP)
            self.receivers.append( [protocol, conn, poll] )
            protocol.connection_made(conn)

