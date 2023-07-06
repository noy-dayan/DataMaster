import pyodbc as odbc


class DataBase:
    # ----------------------------------------------------------------- #
    #                           Init DataBase                           #
    # ----------------------------------------------------------------- #

    def __init__(self, conn_string: str):
        self.conn_string = conn_string
        self.conn = self.conn_db()
        self.cursor = self.conn.cursor()

    # ----------------------------------------------------------------- #
    #                       Connection related Section                  #
    # ----------------------------------------------------------------- #

    # connect to the SQL server database
    def conn_db(self):
        # Create a connection to the database
        print(f"[+] Establishing connecting to data base")
        try:
            conn = odbc.connect(self.conn_string)
            if conn:
                print(f"[+] Connected established successfully")
            return conn

        except odbc.Error as e:
            print(f"[!] Connection failed: \n{e}")
            exit(1)

    # reset the connection with the database after each action to avoid unexpected errors
    def reset_conn(self):
        try:
            self.conn = odbc.connect(self.conn_string)
            self.cursor = self.conn.cursor()
            return True
        except odbc.Error as e:
            return False

    # close the connection with the database
    def close(self):
        # Close the cursor and the connection
        self.cursor.close()
        self.conn.close()

    # ----------------------------------------------------------------- #
    #                       Connection related Section                  #
    # ----------------------------------------------------------------- #

    # check if table exists in database
    def check_table_exists(self, table_name: str):
        table_list = self.cursor.tables(tableType='TABLE')
        if any(table.table_name == table_name for table in table_list):
            return True
        else:
            return False

    # check if instance exists in table
    def check_instance_exists(self, table_name: str, instance: ()):
        self.cursor.execute(f"SELECT COUNT(*) FROM {table_name} WHERE id=?", (instance[0],))
        count = self.cursor.fetchone()[0]
        return count > 0

    # ----------------------------------------------------------------- #
    #                             Queries                               #
    # ----------------------------------------------------------------- #

    # create and add new table to the database
    def create_table(self, table_info: list):
        try:
            # Check if table exists in database
            table_name = table_info[0]
            if not self.check_table_exists(table_name):
                columns = "("
                for column in table_info:
                    if type(column) == tuple:
                        if column[1] == "String":
                            columns += f"{column[0]} TEXT,"
                        elif column[1] == "Double":
                            columns += f"{column[0]} Float,"
                        else:
                            columns += f"{column[0]} {column[1]},"
                columns = columns[:-1]
                columns += ")"
                self.cursor.execute(f"CREATE TABLE {table_name} {columns}")
                print(f"[+] Table {table_info} created successfully")

                # Commit the transaction
                self.conn.commit()

            else:
                print(f"[-] Table '{table_name}' already exists")

        except odbc.Error as e:
            table_name = table_info[0]
            print(f"[!] Table creation '{table_name}' failed: \n{e}")

    # delete table from the database
    def delete_table(self, table_name):
        try:
            # check if table exists in database
            if self.check_table_exists(table_name):
                self.cursor.execute(f"DROP TABLE {table_name}")
                print(f"[+] Table '{table_name}' deleted successfully")

                self.conn.commit()

            else:
                print(f"[-] Table '{table_name}' does not exist")

        except odbc.Error as e:
            print(f"[!] Table '{table_name}' deletion failed: \n{e}")

    # create an instance and add it to the table
    def create_instance(self, table_name, instance):
        try:
            self.cursor.execute(f"SELECT TOP 1 * FROM {table_name}")

            # extract column names from the rows
            columns = tuple([column[0] for column in self.cursor.description])
            columns = "(" + ", ".join(columns) + ")"
            # execute the SQL statement
            self.cursor.execute(f"INSERT INTO {table_name} {columns} VALUES {instance}")

            self.conn.commit()
            return True
        except odbc.Error as e:
            print(f"[!] Instance {instance} creation in table '{table_name}' failed: \n{e}")

    # insert instance into table
    def insert_instance_into_table(self, table_name: str, instance: ()):
        try:
            # Check if table exists in database
            if self.check_table_exists(table_name):

                # Check if instance exists in table
                if not self.check_instance_exists(table_name, instance):
                    self.cursor.execute(f"INSERT INTO {table_name} VALUES {instance}")
                    print(f"[+] Instance {instance} added to'{table_name}' successfully")

                    # Commit the transaction
                    self.conn.commit()

                else:
                    print(f"[-] Instance with ID {instance[0]} already exists in '{table_name}'")

            else:
                print(f"[!] Table '{table_name}' doesn't exists")

        except odbc.Error as e:
            print(f"[!] Instance {instance} insertion into '{table_name}' failed: \n{e}")

    # calculate min/max/avg/sum of column according to user choice
    def get_min_max_avg_sum(self, choice_info):
        self.cursor.execute(choice_info)
        value = self.cursor.fetchone()[0]
        return value

    # remove instance from table
    def delete_instance(self, table_name: str, instance_id: int):
        try:
            # Check if table exists in database
            if self.check_table_exists(table_name):

                # Check if instance exists in table
                if self.check_instance_exists(table_name, (instance_id,)):
                    self.cursor.execute(f"DELETE FROM {table_name} WHERE id=?", (instance_id,))
                    print(f"[+] Instance with ID {instance_id} removed from '{table_name}' successfully")

                    # Commit the transaction
                    self.conn.commit()

                else:
                    print(f"[-] Instance with ID {instance_id} does not exist in '{table_name}'")

            else:
                print(f"[!] Table '{table_name}' doesn't exist")

        except odbc.Error as e:
            print(f"[!] Instance with ID {instance_id} removal from '{table_name}' failed: \n{e}")

    # calculate number of rows in table
    def count_rows(self, info):
        self.cursor.execute(info)
        value = self.cursor.fetchone()[0]
        return value

    # ----------------------------------------------------------------- #
    #                       Table info related Section                  #
    # ----------------------------------------------------------------- #

    # return all tables in the database
    def get_table_list(self):
        try:
            table_list = []
            for table_info in self.cursor.tables():
                if table_info.table_type == "TABLE":
                    table_list.append(str(table_info.table_name))
            return table_list

        except odbc.Error as e:
            print(f"[!] Retrieving table list failed: \n{e}")
            return []

    # return table info
    def get_table_info(self, table_name: str):
        try:
            table_info = []
            if table_name in self.get_table_list():
                # get the list of columns in the table
                self.cursor.execute(f"SELECT * FROM {table_name} WHERE 1=0")
                columns = [column[0:2] for column in self.cursor.description]
                table_info.append(columns)

                # get the data from the table
                self.cursor.execute(f"SELECT * FROM {table_name}")
                data = self.cursor.fetchall()
                table_info.append(data)
                table_info.insert(0, table_name)
                return table_info

        except odbc.Error as e:
            print(f"[!] Retrieving table list failed: \n{e}")
            return None

    # print all instances in table
    def print_instances_in_table(self, table_name: str):
        self.cursor.execute(f'SELECT * FROM {table_name}')
        rows = self.cursor.fetchall()
        for row in rows:
            print(row)
