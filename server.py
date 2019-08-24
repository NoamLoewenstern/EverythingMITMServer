from __future__ import print_function
import sys
from socket import socket, timeout, AF_INET, SOCK_STREAM
from threading import Thread, Event
from select import select
from Queue import Queue

from utils import recvall, vprint
from config import LISTEN_IP, LISTEN_PORT, TIMEOUT_CONNECTION, \
    EVERYTHING_SERVER_IP


class HandleConnectionThread(Thread):
    """Thread class with a stop() method. The thread itself has to check
    regularly for the stopped() condition."""

    def __init__(self, client_conn, client_addr, *args, **kargs):
        super(HandleConnectionThread, self).__init__(*args, **kargs)
        self._stop_event = Event()
        self.client_conn = client_conn
        self.client_addr = client_addr
        self.server_conn = socket()
        self.conns = [self.server_conn, self.client_conn]

    def stop(self):
        self.close_connection()
        self._stop_event.set()

    def stopped(self):
        return self._stop_event.is_set()

    def close_connection(self):
        print("[-] Closing Connection: " + str(self.client_addr),
              file=sys.stderr)
        for conn in self.conns:
            conn.close()
        self.conns.remove(self.server_conn)
        self.conns.remove(self.client_conn)

    def run(self):
        self.server_conn.connect((EVERYTHING_SERVER_IP, LISTEN_PORT))
        message_queues = {
            self.server_conn: Queue(),
            self.client_conn: Queue()
        }
        while self.conns:
            readable, writable, exceptional = select(
                self.conns, self.conns, [], TIMEOUT_CONNECTION)

            if not (readable or writable or exceptional):
                self.stop()
            for sck in readable:
                dst_socket = self.client_conn \
                    if sck is self.server_conn \
                    else self.server_conn
                data = recvall(sck)
                vprint("data -> " + str(data))
                message_queues[dst_socket].put(data)
                if not data:
                    self.stop()
                    break
            for sck in writable:
                try:
                    next_msg = message_queues[sck].get_nowait()
                    sck.send(next_msg)
                except Exception as e:
                    pass


def mitm_server():
    mitm_socket = socket(AF_INET, SOCK_STREAM)
    mitm_socket.bind((LISTEN_IP, LISTEN_PORT))
    mitm_socket.settimeout(2.0)
    # mitm_socket.setblocking(0)
    mitm_socket.listen(5)
    conns_threads = []
    print("[~] Started listening on %s..." % str((LISTEN_IP, LISTEN_PORT)))
    try:
        while True:
            try:
                client_conn, addr = mitm_socket.accept()
                print("[+] New Connection: " + str(addr))
                new_conn_thread = HandleConnectionThread(
                    client_conn,
                    addr,
                    name="Conn: " + str(addr))
                new_conn_thread.start()
                conns_threads.append(new_conn_thread)
            except timeout:
                continue
            except Exception as e:
                print("[!] Exception: " + str(e), file=sys.stderr)
    except KeyboardInterrupt:  # closing manually via ^C
        for thread in conns_threads:
            thread.stop()
        for thread in conns_threads:
            thread.join()

    print("[~] Closing Everything-MITM Server...")
    mitm_socket.close()


def main():
    mitm_server()


if __name__ == "__main__":
    main()
