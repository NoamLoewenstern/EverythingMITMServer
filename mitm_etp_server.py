from __future__ import print_function
import sys
from socket import socket, timeout as SOCKET_TIMEOUT, AF_INET, SOCK_STREAM

from config import LISTEN_IP, ETP_PORT
from handle_connection import HandleConnectionThread


def mitm_server():
    mitm_socket = socket(AF_INET, SOCK_STREAM)
    mitm_socket.bind((LISTEN_IP, ETP_PORT))
    mitm_socket.settimeout(3.0)
    # mitm_socket.setblocking(0)
    mitm_socket.listen(5)
    conns_threads = []
    print("[~] Started listening on %s..." % str((LISTEN_IP, ETP_PORT)))
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
            except SOCKET_TIMEOUT:
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
