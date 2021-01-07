from lib.delegation import BaseProtocol, start_delegating
from lib.consts import CRLF
import json, ssl


class HTTPSProtocol(BaseProtocol):
    def __init__(self):
        with open("config/ssl.json") as ssl_cfg:
            self.ssl_cfg = json.load(ssl_cfg)

    def connection_made(self):
        sock, poll = self.delegate.sockets[self.trans.fileno()]
        poll.unregister(sock)
        try:
            sock = ssl.wrap_socket(sock, server_side=True,
                    certfile=self.ssl_cfg['cert'],
                    keyfile=self.ssl_cfg['key'])
        except ssl.SSLError as exc:
            print(exc)
        poll.register(sock)
        self.delegate.sockets[sock.fileno()] = [sock, poll]

    def data_received(self, data):
        queries = data.split(2 * CRLF)[0].split(CRLF)
        self.trans.send(b"HTTP/1.1 200 OK\r\n\r\n<html>bitch nigga</html>")


if __name__ == "__main__":
    try:
        start_delegating('', 32768, HTTPSProtocol)
    except KeyboardInterrupt:
        print("closing...")
