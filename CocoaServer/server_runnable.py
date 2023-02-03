from server import Server
import socket as s

if __name__ == "__main__":
    s = Server("127.0.0.1", 55757)
    s.open_socket()
    s.run()
