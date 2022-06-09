import socket
import sys

class RemoteDriver:

    def __init__(self, receiver_ip, receiver_port):
        self.s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        try:
            self.s.connect((receiver_ip, receiver_port))
        except:
            print("Connection to receiver failed")
            sys.exit(1)
    
    def _send(self, msg):
        self.s.sendall(f"{msg}\n".encode('utf-8'))

    def get(self, url):
        self._send(url)
    
    def set_page_load_timeout(self, timeout):
        self._send(f"biggerfish://set-timeout/{timeout}")
    
    def quit(self):
        self._send("biggerfish://restart")