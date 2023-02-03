from socket import *
import sys

from client import Client

if __name__ == "__main__":
    c = Client(("127.0.0.1", 55757))  # gethostbyname(gethostname())
    c.communicate()
    sys.exit()
