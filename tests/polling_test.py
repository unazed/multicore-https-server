import select, socket


sock = socket.socket()
poll = select.poll()
poll.register(sock, select.POLLIN)
sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
sock.bind(('', 32768))
sock.listen(10)

conns = []

while True:
    event = poll.poll(100)
    if not event:
        for conn in conns:
            client, addr, client_poll = conn
            event = client_poll.poll(100)
            if not event:
                continue
            elif event[0][1] & select.POLLIN:
                data = client.recv(1024)
                if not data:
                    print(addr, "closed abruptly")
                    client.close()
                    conns.remove(conn)
                    continue
                print("got", data, "from", addr)
        continue
    client, addr = sock.accept()
    client_poll = select.poll()
    client_poll.register(client, select.POLLIN | select.POLLOUT)
    conns.append( (client, addr, client_poll) )
    print("received connection", addr)
