import sys
from socket import socket
from utils import recvall
from threading import Thread
from select import select
from Queue import Queue

IP = "0.0.0.0"
PORT = 21

TIMEOUT_CONNECTION = 5 * 60

SERVER_IP = "noaml-laptop"

client_socket = socket()
client_socket.bind((IP, PORT))
# client_socket.setblocking(0)
client_socket.listen(5)


def handle_connection(client_conn, addr):
    server_conn = socket()
    server_conn.connect((SERVER_IP, PORT))

    conns = [server_conn, client_conn]
    message_queues = {
        server_conn: Queue(),
        client_conn: Queue()
    }

    def close_connection():
        print >> sys.stderr, "[-] Closing Connection: " + str(addr)
        for s in conns:
            s.close()
        conns.remove(server_conn)
        conns.remove(client_conn)

    while conns:
        readable, writable, exceptional = select(
            conns, conns, [], TIMEOUT_CONNECTION)

        for sck in readable:
            dst_socket = client_conn if sck is server_conn else server_conn
            data = recvall(sck)
            print "data -> ", data
            message_queues[dst_socket].put(data)
            if not data:
                close_connection()
                break
        for sck in writable:
            try:
                next_msg = message_queues[sck].get_nowait()
                sck.send(next_msg)
            except Exception as e:
                pass
        if not (readable or writable or exceptional):
            close_connection()


threads = []
print "[=] Starting listening for connections..."
while True:
    client_conn, addr = client_socket.accept()
    print "[+] New Connection: " + str(addr)
    new_conn_thread = Thread(name="Conn: " + str(addr),
                             target=handle_connection,
                             args=(client_conn, addr,))
    new_conn_thread.start()
    threads.append(new_conn_thread)

print "[=] Closing MITM Server..."
