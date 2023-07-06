import pickle
import socket
from threading import Thread


class ClientSocket:
    def __init__(self, server_ip, server_port):
        # ----------------------------------------------------------------- #
        #                         Init Client Socket                        #
        # ----------------------------------------------------------------- #

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)  # create client socket
        self.server_addr = (server_ip, server_port)  # set server address
        self.buffer_size = 4096  # set the buffer size
        self.client_source_port = 20075

        self.conn_flag = False  # is connected to server?
        self.recv_window = []
        self.send_window = []

        # initialize thread-related variables
        self.threads = []
        self.table_list = []
        self.curr_table = None

        self.curr_value = ""

    # ----------------------------------------------------------------- #
    #                       Socket related Section                      #
    # ----------------------------------------------------------------- #

    # start the client socket
    def start(self):
        print(f"[+] Establishing connection with the server at {self.server_addr}")
        self.client_socket.connect(self.server_addr)
        data = self.client_socket.recv(self.buffer_size)
        data = pickle.loads(data)
        if data[0] == "CONNECTED":
            print("[+] Connected to the server!")
            self.table_list = data[1]
            recv_window_handler_thread = Thread(target=self.handle_recv_window)

            recv_window_handler_thread.start()
            self.conn_flag = True
            self.threads.append(recv_window_handler_thread)

    # handle received data
    def handle_recv_window(self):
        while True:
            try:
                while True:
                    data = self.client_socket.recv(self.buffer_size)
                    data = pickle.loads(data)

                    print(f"[*] Received packet: {data}) from server")

                    if data[0] == "TABLE_LIST":
                        self.table_list = data[1]
                        print(f"[+] Table list updated: {self.table_list}")

                    if data[0] == "TABLE_INFO":
                        self.curr_table = data[1]
                        if self.curr_table is not None:
                            print(f"[+] Got table {self.curr_table[0]} data ")
                        else:
                            print(f"[-] Cannot access table")

                    if data[0] == "CREATE_INSTANCE" or data[0] == "DELETE_INSTANCE":
                        table_name = data[1][0]
                        instances = data[1][2],
                        if self.curr_table[0] == table_name:
                            print(f"[+] Updating current table list instances: {instances}")
                            self.curr_table[2] = instances

                    if data[0] == "MIN_MAX_SUM_AVG":
                        self.curr_value = str(data[1])
                        print(f"[+] Got desired choice value: {self.curr_value}")

                    if data[0] == "COUNT_ROWS":
                        self.curr_value = str(data[1])
                        print(f"[+] Got desired row value: {self.curr_value}")
            except:
                pass

    # send data to the server
    def send(self, data):
        try:
            print(f"[*] Sending packet:  {data} to server")
            self.client_socket.sendall(pickle.dumps(data))

        except:
            pass

    # disconnect from the server
    def disconnect(self):
        self.send(["CLOSE_CONN"])
        print(f"[+] Connection with server has been closed")

        self.client_socket.close()
        self.conn_flag = False

    # ----------------------------------------------------------------- #
    #                   Server request related Section                  #
    # ----------------------------------------------------------------- #

    # request the server to access table data from the database
    def access_table(self, table):
        self.send(["ACCESS_TABLE", str(table)])

    # request the server to delete table from the database
    def delete_table(self, table):
        self.send(["DELETE_TABLE", str(table)])

    def delete_instance(self, table_name, instance_index):
        print((table_name, instance_index))
        self.send(["DELETE_INSTANCE", (table_name, instance_index)])

    # request the server to create table and add to the database
    def create_table(self, table_info):
        self.send(["CREATE_TABLE", table_info])

    # request the server to create instance and add to the database table
    def create_instance(self, table_name, instance):
        self.send(["CREATE_INSTANCE", (table_name, instance)])

    # request the server to send an answer according to the desired choice
    def get_min_max_avg_sum(self, choice_info):
        self.send(["MIN_MAX_SUM_AVG", choice_info])

    def count_rows(self, info):
        self.send(["COUNT_ROWS", info])
