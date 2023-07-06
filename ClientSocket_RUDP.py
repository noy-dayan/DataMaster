import pickle
import random
import socket
import struct
import time
from threading import Thread

class ClientSocket:
    def __init__(self, server_ip, server_port):
        # ----------------------------------------------------------------- #
        #                         Init Client Socket                        #
        # ----------------------------------------------------------------- #

        self.client_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # create client socket
        self.server_addr = (server_ip, server_port)  # set server address
        self.buffer_size = 4096  # set the buffer size
        self.client_source_port = 20075

        self.conn_flag = False  # is connected to server?

        # set the size of the receive and send windows sliders
        self.recv_window_size = 5
        self.recv_window = []
        self.send_window_size = 5
        self.send_window = []

        # set the sequence and acknowledgment numbers
        self.seq_no = random.randint(2, 1 * (10 ** 4))  # random sequence number
        self.ack_no = 1

        # initialize variables related to ARQ
        self.last_ack_time = time.time()
        self.last_packet_time = 0
        self.last_packet_sent = None

        self.timeout = 10  # set timeout to 10 seconds
        self.retransmission = self.timeout / 3  # time pending before retransmission of packet
        self.timeout_flag = False

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
        # try bind source port to client (would work only with the first client or if he disconnects)
        try:
            self.client_socket.bind((self.server_addr[0], self.client_source_port))
        except:
            pass
        # send "SYN" packet to establish 3-way handshake with the server
        syn_packet = self.pack_packet("SYN", self.seq_no, self.ack_no)
        self.send_window.append(syn_packet)
        self.timeout_flag = True

        recv_thread = Thread(target=self.receive)
        recv_window_handler_thread = Thread(target=self.handle_recv_window)
        send_thread = Thread(target=self.send)
        timeout_thread = Thread(target=self.timeout_check)
        retransmission_thread = Thread(target=self.retransmission_packet)

        recv_thread.start()
        recv_window_handler_thread.start()
        send_thread.start()
        timeout_thread.start()
        retransmission_thread.start()

        self.threads.append(recv_thread)
        self.threads.append(recv_window_handler_thread)
        self.threads.append(send_thread)
        self.threads.append(timeout_thread)
        self.threads.append(retransmission_thread)

    # receive data from the server
    def receive(self):
        while True:
            try:
                data, addr = self.client_socket.recvfrom(self.buffer_size)
                if len(self.recv_window) < self.recv_window_size:
                    self.recv_window.append((data, addr))
                    self.last_packet_time = time.time()
            except:
                pass

    # handle received data
    def handle_recv_window(self):
        while True:
            while len(self.recv_window) > 0:
                data, addr = self.recv_window.pop(0)
                packet_type, seq_no, ack_no, dup_ack, payload = self.unpack_packet(data)
                packet_type = packet_type.decode().strip("_")

                try:
                    try:
                        payload_readable = pickle.dumps(payload)
                    except:
                        payload_readable = payload.decode()
                except:
                    payload_readable = payload
                print(
                    f"[*] Received packet: ({packet_type}, {seq_no}, {ack_no}, {dup_ack}, {payload_readable}) from server")

                if packet_type == "SYN-ACK":
                    self.seq_no = ack_no
                    self.ack_no = seq_no + 1

                    packet = self.pack_packet("ACK", self.seq_no, self.ack_no)
                    self.send_window.append(packet)
                    self.last_packet_sent = packet
                    print(f"[+] Connection to the server established successfully")

                    if payload is not None:
                        self.table_list = pickle.loads(payload)
                    self.conn_flag = True
                    self.timeout_flag = False

                if packet_type == "ACK":
                    self.timeout_flag = False
                    self.last_ack_time = time.time()

                if packet_type == "FIN-ACK":
                    self.seq_no = ack_no
                    self.ack_no = seq_no + 1

                    packet = self.pack_packet("CLOSE_CONN", self.seq_no, self.ack_no)
                    self.send_window.append(packet)
                    print(f"[-] Connection closed")
                    self.timeout_flag = False
                    self.table_list = []
                    self.curr_table = None
                    for thread in self.threads:
                        thread.join()

                if packet_type == "TABLE_LIST":
                    self.table_list = pickle.loads(payload)
                    print(f"[+] Table list updated: {self.table_list}")
                    packet = self.pack_packet("ACK", self.seq_no, self.ack_no)
                    self.send_window.append(packet)
                    self.timeout_flag = False

                if packet_type == "TABLE_INFO":
                    self.curr_table = pickle.loads(payload)
                    if self.curr_table is not None:
                        print(f"[+] Got table {self.curr_table[0]} data ")
                    else:
                        print(f"[-] Cannot access table")
                    packet = self.pack_packet("ACK", self.seq_no, self.ack_no)
                    self.send_window.append(packet)
                    self.timeout_flag = False

                if packet_type == "CREATE_INSTANCE" or packet_type == "DELETE_INSTANCE":
                    table_name, columns, instances = pickle.loads(payload)
                    if self.curr_table[0] == table_name:
                        print(f"[+] Updating current table list instances: {instances}")
                        self.curr_table[2] = instances
                    packet = self.pack_packet("ACK", self.seq_no, self.ack_no)
                    self.send_window.append(packet)
                    self.timeout_flag = False

                if packet_type == "MIN_MAX_SUM_AVG":
                    self.curr_value = str(payload.decode())

                    print(f"[+] Got desired choice value: {self.curr_value}")
                    packet = self.pack_packet("ACK", self.seq_no, self.ack_no)
                    self.send_window.append(packet)
                    self.timeout_flag = False

                if packet_type == "COUNT_ROWS":
                    self.curr_value = str(payload.decode())

                    print(f"[+] Got desired row value: {self.curr_value}")
                    packet = self.pack_packet("ACK", self.seq_no, self.ack_no)
                    self.send_window.append(packet)
                    self.timeout_flag = False

                if packet_type == "CONN_TIMEOUT":
                    print(f"[-] Connection failed, connection timeout has occurred")
                    self.conn_flag = False
                    self.timeout_flag = False

                    for thread in self.threads:
                        thread.join()

    # send data to the server
    def send(self):
        while True:
            try:
                while 0 < len(self.send_window):
                    data = self.send_window.pop(0)
                    if len(self.send_window) < self.send_window_size:
                        self.client_socket.sendto(data, self.server_addr)
                        self.last_packet_sent = data
                        print(f"[*] Sending packet:  {self.unpack_packet(data)}")
                        _, _, _, dup_ack, _ = self.unpack_packet(data)
                        if not dup_ack:
                            self.last_packet_time = time.time()

            except:
                pass

    # disconnect from the server
    def disconnect(self):
        fin_packet = self.pack_packet("FIN", self.seq_no, self.ack_no)
        self.send_window.append(fin_packet)
        self.conn_flag = False
        self.last_packet_sent = fin_packet

    # ----------------------------------------------------------------- #
    #                       RUDP related Section                        #
    # ----------------------------------------------------------------- #

    # check for connection timeout error
    def timeout_check(self):
        while True:
            time.sleep(2)
            try:
                if self.timeout_flag is True:
                    if time.time() - self.last_packet_time > self.timeout:
                        print(f"[-] Connection failed, connection timeout has occurred")
                        try:
                            conn_timeout_packet = self.pack_packet("CONN_TIMEOUT", self.seq_no, self.ack_no + 1)
                            self.send_window.append(conn_timeout_packet)
                            self.conn_flag = False
                            self.timeout_flag = False

                        except:
                            pass

                        time.sleep(1)

            except:
                pass

    # retransmission last packet sent to the server
    def retransmission_packet(self):
        while True:
            time.sleep(self.retransmission)
            try:
                if self.timeout_flag is True:
                    if time.time() - self.last_packet_time > self.retransmission:
                        packet_type, seq_no, ack_no, dup_ack, payload = self.unpack_packet(self.last_packet_sent)
                        dup_ack = True
                        dup_packet = self.pack_packet(packet_type, seq_no, ack_no, dup_ack, payload)
                        print(f"[+] Retransmission for packet {{type:{packet_type}; seq_no:{seq_no}}}")
                        try:
                            self.send_window.append(dup_packet)
                        except:
                            pass


            except:
                pass

    # ----------------------------------------------------------------- #
    #                   Server request related Section                  #
    # ----------------------------------------------------------------- #

    # request the server to access table data from the database
    def access_table(self, table):
        access_table_packet = self.pack_packet("ACCESS_TABLE", self.seq_no, self.ack_no + 1,
                                               payload=str(table).encode())
        self.send_window.append(access_table_packet)
        self.last_packet_sent = access_table_packet
        self.timeout_flag = True

    # request the server to delete table from the database
    def delete_table(self, table):
        delete_table_packet = self.pack_packet("DELETE_TABLE", self.seq_no, self.ack_no + 1,
                                               payload=str(table).encode())
        self.send_window.append(delete_table_packet)
        self.last_packet_sent = delete_table_packet
        self.timeout_flag = True

    def delete_instance(self, table_name, instance_index):
        delete_instance_packet = self.pack_packet("DELETE_INSTANCE", self.seq_no, self.ack_no + 1,
                                               payload=pickle.dumps((table_name, instance_index)))
        print((table_name, instance_index))
        self.send_window.append(delete_instance_packet)
        self.last_packet_sent = delete_instance_packet
        self.timeout_flag = True

    # request the server to create table and add to the database
    def create_table(self, table_info):
        table_info = pickle.dumps(table_info)
        create_table_packet = self.pack_packet("CREATE_TABLE", self.seq_no, self.ack_no + 1, payload=table_info)
        self.send_window.append(create_table_packet)
        self.last_packet_sent = create_table_packet
        self.timeout_flag = True

    # request the server to create instance and add to the database table
    def create_instance(self, table_name, instance):
        info = pickle.dumps((table_name, instance))
        create_instance_packet = self.pack_packet("CREATE_INSTANCE", self.seq_no, self.ack_no + 1, payload=info)
        self.send_window.append(create_instance_packet)
        self.last_packet_sent = create_instance_packet
        self.timeout_flag = True

    # request the server to send an answer according to the desired choice
    def get_min_max_avg_sum(self, choice_info):
        get_min_max_avg_sum_packet = self.pack_packet("MIN_MAX_SUM_AVG", self.seq_no, self.ack_no + 1,
                                                  payload=choice_info.encode())
        self.send_window.append(get_min_max_avg_sum_packet)
        self.last_packet_sent = get_min_max_avg_sum_packet
        self.timeout_flag = True

    def count_rows(self, info):
        count_rows_packet = self.pack_packet("COUNT_ROWS", self.seq_no, self.ack_no + 1,
                                                  payload=info.encode())
        self.send_window.append(count_rows_packet)
        self.last_packet_sent = count_rows_packet
        self.timeout_flag = True

    # ----------------------------------------------------------------- #
    #                   Packet analysis related Section                 #
    # ----------------------------------------------------------------- #

    # pack packet of length of 20 chars, 2 integers and 1 boolean + payload
    @staticmethod
    def pack_packet(packet_type, seq_no, ack_no, dup_ack=False, payload=None):
        if type(packet_type) is not bytes:
            packet_type = packet_type.ljust(20, "_")
            packet_type = packet_type.encode()
        packet = struct.pack('20s 2i ?', packet_type, seq_no, ack_no, dup_ack)
        if payload is not None:
            packet += payload
        return packet

    # unpack packet of length of 20 chars, 2 integers and 1 boolean + payload
    @staticmethod
    def unpack_packet(packet):
        header_size = struct.calcsize("20s 2i ?")
        header = packet[:header_size]
        payload = packet[header_size:]
        packet_type, seq_no, ack_no, dup_ack = struct.unpack("20s 2i ?", header)
        return packet_type, seq_no, ack_no, dup_ack, payload
