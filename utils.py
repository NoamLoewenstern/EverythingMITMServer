from __future__ import print_function
from config import VERBOSE


def recvall(sock):
    BUFF_SIZE = 4096  # 4 KiB
    data = b''
    while True:
        part = sock.recv(BUFF_SIZE)
        data += part
        if len(part) < BUFF_SIZE:
            # either 0 or end of data
            break
    return data


def vprint(*args, **kargs):
    if VERBOSE:
        print(*args, **kargs)
