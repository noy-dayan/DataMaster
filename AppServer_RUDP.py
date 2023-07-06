#!/usr/bin/python3.11
# Author: Noy Dayan
import socket
import struct
import time
from threading import Thread
import random
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
        self.server_sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)  # create server socket
        self.server_sock.bind(self.server_addr)  # bind server socket

        self.buffer_size = buffer_size  # set the buffer size

        self.max_clients = max_clients  # set max clients (if -1: no limit)
        self.clients = {}

        # initialize variables related to ARQ
        self.timeout = 10  # time pending before timeout
        self.retransmission = self.timeout / 3  # time pending before retransmission of packet

        # set the size of the receive and send windows sliders
        self.recv_window_size = 5
        self.recv_window = []
        self.send_window = []

        # initialize variables related to ARQ
        self.timeout_clients = {}  # list of clients that are currently being checked for timeout

        # init database object and properties
        self.db = DataBase(conn_string)
        self.table_list = []
        self.db_access_flag = True

    # ----------------------------------------------------------------- #
    #                       Socket related Section                      #
    # ----------------------------------------------------------------- #

    # start the server
    def start(self):
        print(f'[+] RUDP Server listening on {self.server_addr}...')
        recv_thread = Thread(target=self.receive)
        send_thread = Thread(target=self.send)
        recv_window_handle_thread = Thread(target=self.handle_recv_window)
        timeout_check_thread = Thread(target=self.timeout_check)
        retransmission_packet_thread = Thread(target=self.retransmission_packet)
        self.table_list = self.db.get_table_list()

        recv_thread.start()
        send_thread.start()
        recv_window_handle_thread.start()
        timeout_check_thread.start()
        retransmission_packet_thread.start()

    # receive data from clients
    def receive(self):
        while True:
            try:
                data, addr = self.server_sock.recvfrom(self.buffer_size)
                if len(self.recv_window) < self.recv_window_size:
                    self.recv_window.append((data, addr))
            except:
                pass

    # handle the received data from the clients
    def handle_recv_window(self):
        while True:
            try:
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
                        f"[*] Received packet: ({packet_type}, {seq_no}, {ack_no}, {dup_ack}, "
                        f"{payload_readable}) from ({addr})")

                    if packet_type == "SYN":
                        ack_no = random.randint(2, 1 * (10 ** 4))  # random sequence number
                        if len(self.clients) < self.max_clients or self.max_clients == -1:
                            syn_ack_packet = self.pack_packet("SYN-ACK", ack_no, seq_no + 1,
                                                              payload=pickle.dumps(self.table_list))
                            self.send_window.append((syn_ack_packet, addr))
                            print(f"[+] New client connection {addr}")

                            self.clients[addr] = {'seq_no': seq_no,
                                                  'ack_no': ack_no,
                                                  'last_packet_time': time.time(),
                                                  'last_packet_sent': syn_ack_packet}
                            self.timeout_clients[addr] = self.clients[addr]

                    if packet_type == "ACK":
                        del self.timeout_clients[addr]
                        last_packet_sent = self.clients[addr]['last_packet_sent']
                        self.clients[addr] = {'seq_no': seq_no,
                                              'ack_no': ack_no,
                                              'last_packet_time': time.time(),
                                              'last_packet_sent': last_packet_sent}

                    if packet_type == "FIN":
                        syn_ack_packet = self.pack_packet("FIN-ACK", ack_no, seq_no + 1)
                        self.send_window.append((syn_ack_packet, addr))
                        self.timeout_clients[addr] = self.clients[addr]
                        self.clients[addr] = {'seq_no': seq_no,
                                              'ack_no': ack_no,
                                              'last_packet_time': time.time(),
                                              'last_packet_sent': syn_ack_packet}

                    if packet_type == "DELETE_TABLE":
                        table = payload.decode()
                        table = int(table)
                        print(f"[+] Deleting table {self.table_list[table]} at index {table}")

                        self.db.reset_conn()
                        self.db.delete_table(self.table_list[table])

                        self.table_list = self.db.get_table_list()
                        table_list_packet = self.pack_packet("TABLE_LIST", ack_no, seq_no + 1,
                                                             payload=pickle.dumps(self.table_list))
                        self.notify_all(table_list_packet, ack_no, seq_no)

                    if packet_type == "DELETE_INSTANCE":
                        table_name, instance_index = pickle.loads(payload)
                        print(f"[+] Deleting instance from {table_name} at index {instance_index}")

                        self.db.reset_conn()
                        self.db.delete_instance(str(table_name), int(instance_index))

                        table_info = self.db.get_table_info(table_name)
                        table_info_packet = self.pack_packet("DELETE_INSTANCE", ack_no, seq_no + 1,
                                                             payload=pickle.dumps(table_info))
                        self.notify_all(table_info_packet, ack_no, seq_no)

                    if packet_type == "CREATE_TABLE":
                        table_info = pickle.loads(payload)
                        print(f"[+] Creating table {table_info}")

                        self.db.reset_conn()
                        self.db.create_table(table_info)

                        self.table_list = self.db.get_table_list()
                        table_list_packet = self.pack_packet("TABLE_LIST", ack_no, seq_no + 1,
                                                             payload=pickle.dumps(self.table_list))
                        self.notify_all(table_list_packet, ack_no, seq_no)

                    if packet_type == "MIN_MAX_SUM_AVG":
                        choice_info = payload.decode()
                        print(f"[+] Sending choice answer to the client {addr}")

                        self.db.reset_conn()
                        value = self.db.get_min_max_avg_sum(choice_info)

                        value_packet = self.pack_packet("MIN_MAX_SUM_AVG", ack_no, seq_no + 1,
                                                        payload=str(format(value, ".2f")).encode())
                        self.send_window.append((value_packet, addr))
                        self.timeout_clients[addr] = self.clients[addr]
                        self.clients[addr] = {'seq_no': seq_no,
                                              'ack_no': ack_no,
                                              'last_packet_time': time.time(),
                                              'last_packet_sent': value_packet}

                    if packet_type == "COUNT_ROWS":
                        info = payload.decode()
                        print(f"[+] Sending choice answer to the client {addr}")

                        self.db.reset_conn()
                        value = str(self.db.count_rows(info))

                        value_packet = self.pack_packet("COUNT_ROWS", ack_no, seq_no + 1,
                                                        payload=value.encode())
                        self.send_window.append((value_packet, addr))
                        self.timeout_clients[addr] = self.clients[addr]
                        self.clients[addr] = {'seq_no': seq_no,
                                              'ack_no': ack_no,
                                              'last_packet_time': time.time(),
                                              'last_packet_sent': value_packet}

                    if packet_type == "CREATE_INSTANCE":
                        table_name, instance = pickle.loads(payload)

                        self.db.reset_conn()
                        if self.db.create_instance(table_name, instance):
                            print(f"[+] Creating instance {instance} in table {table_name}")
                            table_info = self.db.get_table_info(table_name)
                            table_info_packet = self.pack_packet("CREATE_INSTANCE", ack_no, seq_no + 1,
                                                                 payload=pickle.dumps(table_info))
                            self.notify_all(table_info_packet, ack_no, seq_no)

                    if packet_type == "ACCESS_TABLE":
                        table_name = payload.decode()
                        print(f"[+] Sending {table_name} data to the client {addr}")

                        self.db.reset_conn()
                        table_info = self.db.get_table_info(table_name)

                        table_info_packet = self.pack_packet("TABLE_INFO", ack_no, seq_no + 1,
                                                             payload=pickle.dumps(table_info))
                        self.send_window.append((table_info_packet, addr))
                        self.timeout_clients[addr] = self.clients[addr]
                        self.clients[addr] = {'seq_no': seq_no,
                                              'ack_no': ack_no,
                                              'last_packet_time': time.time(),
                                              'last_packet_sent': table_info_packet}

                    if packet_type == "CLOSE_CONN":
                        print(f"[+] Connection with client {addr} has been closed")
                        try:
                            del self.timeout_clients[addr]
                            del self.clients[addr]
                        except:
                            pass
                    if packet_type == "CONN_TIMEOUT":
                        print(f"[-] Connection failed, connection timeout has occurred with client {addr}")
                        try:
                            del self.timeout_clients[addr]
                            del self.clients[addr]
                        except:
                            pass

            except Exception as e:
                print(f"[-] Error while trying to handle receive: {e}")

    # send data to a client
    def send(self):
        while True:
            try:
                while len(self.send_window) > 0:
                    data, addr = self.send_window.pop(0)
                    self.server_sock.sendto(data, addr)
                    print(f"[*] Sending packet:  {self.unpack_packet(data)}")

            except Exception as e:
                print(f"[-] Error while trying to send: {e}")

    # send data to all clients
    def notify_all(self, msg, ack_no, seq_no):
        print(f"[+] Notifying the clients about the update that occurred")
        for c in self.clients.keys():
            self.send_window.append((msg, c))
            self.clients[c] = {'seq_no': seq_no,
                               'ack_no': ack_no,
                               'last_packet_time': time.time(),
                               'last_packet_sent': msg}
            self.timeout_clients[c] = self.clients[c]

    # ----------------------------------------------------------------- #
    #                       RUDP related Section                        #
    # ----------------------------------------------------------------- #

    # check for connection timeout error
    def timeout_check(self):
        while True:
            try:
                for s in self.timeout_clients:
                    # Check for inactive clients
                    client = self.clients[s]
                    if time.time() - client['last_packet_time'] > self.timeout:
                        try:
                            timeout_packet = self.pack_packet("CONN_TIMEOUT", client["seq_no"], client["ack_no"] + 1)
                            self.send_window.append((timeout_packet, s))
                        except:
                            pass

                        del self.clients[s]
                        del self.timeout_clients[s]
                        time.sleep(1)
                        print(f"[-] Connection timeout for client {s} ")
                    elif time.time() - client['last_packet_time'] > self.timeout:
                        pass

            except:
                pass

    # retransmission last packet sent to the client
    def retransmission_packet(self):
        while True:
            time.sleep(self.retransmission)
            try:
                for s in self.timeout_clients:
                    client = self.clients[s]

                    if time.time() - client['last_packet_time'] > self.retransmission:
                        print(client['last_packet_sent'])
                        try:
                            packet_type, seq_no, ack_no, dup_ack, payload = self.unpack_packet(client['last_packet_sent'])
                            dup_ack = True
                            dup_packet = self.pack_packet(packet_type, seq_no, ack_no, dup_ack, payload)

                        except:
                            dup_packet = client['last_packet_sent']

                        print(f"[+] Retransmission for packet {dup_packet}")
                        try:
                            self.send_window.append(dup_packet)
                        except:
                            pass
            except:
                pass

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
