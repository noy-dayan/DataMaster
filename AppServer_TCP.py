#!/usr/bin/python3.11
# Author: Noy Dayan
import socket
from threading import Thread
import pickle
from DataBase import *

MAX_PACKET_SIZE = 4096

# In case Micorosoft SQL server database:
'''
DRIVER_NAME = 'SQL Server'
SERVER_NAME = 'DESKTOP-HNIMD1Q'
DATABASE_NAME = 'sql project'
conn_string = \
    f"""
    DRIVER={{{DRIVER_NAME}}};
    SERVER={SERVER_NAME};
    DATABASE={DATABASE_NAME};
    Trusted_Connection=yes;
    """
'''

# In case Micorosoft Access SQL database:
DRIVER_NAME = 'Microsoft Access Driver (*.mdb, *.accdb)'
LOCATION = 'DataBase\\Database.accdb'
conn_string = rf'Driver={{{DRIVER_NAME}}};DBQ={LOCATION};'


class AppServer:
    # ----------------------------------------------------------------- #
    #                           Init Server                             #
    # ----------------------------------------------------------------- #

    def __init__(self, ip, port, max_clients=-1, buffer_size=4096):
        self.server_addr = (ip, port)  # set server address
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create server socket
        self.threads = []

        self.buffer_size = buffer_size  # set the buffer size

        self.max_clients = max_clients  # set max clients (if -1: no limit)
        self.clients = []

        self.recv_window = []
        self.send_window = []

        # initialize variables related to ARQ

        # init database object and properties
        self.db = DataBase(conn_string)
        self.table_list = []
        self.db_access_flag = True

    # ----------------------------------------------------------------- #
    #                       Socket related Section                      #
    # ----------------------------------------------------------------- #

    # start the server
    def start(self):
        print(f'[+] TCP Server listening on {self.server_addr}...')
        self.server_sock.bind(self.server_addr)
        if self.max_clients == -1:
            self.server_sock.listen()
        else:
            self.server_sock.listen(self.max_clients)
        self.table_list = self.db.get_table_list()
        self.receive()

    # receive data from clients
    def receive(self):
        while True:
            try:
                clientsock, addr = self.server_sock.accept()
                self.clients.append((clientsock, addr))
                print(f"[+] Client ({addr}) connected to the server")
                self.send(["CONNECTED", self.table_list], clientsock, addr)
                recv_window_handle_thread = Thread(target=self.handle_recv_window, args=(clientsock, addr,))
                recv_window_handle_thread.start()
                self.threads.append(recv_window_handle_thread)
            except:
                pass

    # handle the received data from the clients
    def handle_recv_window(self, clientsock, addr):
        try:
            while True:
                data = clientsock.recv(self.buffer_size)
                data = pickle.loads(data)

                print(f"[*] Received packet: ({data}) from ({addr})")

                if data[0] == "DELETE_TABLE":
                    data[1] = int(data[1])
                    print(f"[+] Deleting table {self.table_list[data[1]]} at index {data[1]}")

                    self.db.reset_conn()
                    self.db.delete_table(self.table_list[data[1]])

                    self.table_list = self.db.get_table_list()
                    self.notify_all(["TABLE_LIST", self.table_list])

                if data[0] == "DELETE_INSTANCE":
                    table_name, instance_index = data[1]
                    print(f"[+] Deleting instance from {table_name} at index {instance_index}")

                    self.db.reset_conn()
                    self.db.delete_instance(str(table_name), int(instance_index))

                    table_info = self.db.get_table_info(table_name)
                    self.notify_all(["DELETE_INSTANCE", table_info])

                if data[0] == "CREATE_TABLE":
                    print(f"[+] Creating table {data[1]}")

                    self.db.reset_conn()
                    self.db.create_table(data[1])

                    self.table_list = self.db.get_table_list()
                    self.notify_all(["TABLE_LIST", self.table_list])

                if data[0] == "MIN_MAX_SUM_AVG":
                    print(f"[+] Sending choice answer to the client {addr}")

                    self.db.reset_conn()
                    value = self.db.get_min_max_avg_sum(data[1])
                    self.send(["MIN_MAX_SUM_AVG", str(format(value, ".2f"))], clientsock, addr)

                if data[0] == "COUNT_ROWS":
                    print(f"[+] Sending choice answer to the client {addr}")

                    self.db.reset_conn()
                    value = str(self.db.count_rows(data[1]))
                    self.send(["COUNT_ROWS", value], clientsock, addr)

                if data[0] == "CREATE_INSTANCE":
                    table_name, instance = data[1]

                    self.db.reset_conn()
                    if self.db.create_instance(table_name, instance):
                        print(f"[+] Creating instance {instance} in table {table_name}")
                        table_info = self.db.get_table_info(table_name)
                        self.notify_all(["CREATE_INSTANCE", table_info])

                if data[0] == "ACCESS_TABLE":
                    table_name = data[1]
                    print(f"[+] Sending {table_name} data to the client {addr}")

                    self.db.reset_conn()
                    table_info = self.db.get_table_info(table_name)
                    self.send(["TABLE_INFO", table_info], clientsock, addr)

                if data[0] == "CLOSE_CONN":
                    print(f"[+] Connection with client {addr} has been closed")
                    try:
                        del self.clients[addr]
                        break
                    except:
                        pass
        except:
            pass

    # send data to a client
    def send(self, data, clientsock, addr):
        try:
            print(f"[*] Sending packet:  {data} to {addr}")
            clientsock.sendall(pickle.dumps(data))

        except:
            pass

    # send data to all clients
    def notify_all(self, msg):
        print(f"[+] Notifying the clients about the update that occurred")
        for client in self.clients:
            self.send(msg, client[0], client[1])

    # ----------------------------------------------------------------- #
    #                               Main                                #
    # ----------------------------------------------------------------- #


def main():
    server = AppServer("localhost", 30743)
    server.start()
    server.db.close()

    return 0


if __name__ == "__main__":
    main()
