#!/usr/bin/python3.11
# Author: Noy Dayan
import time
import tkinter as tk
from threading import Thread
from tkinter import *
from tkinter import ttk

from ClientSocket_TCP import ClientSocket


class Client:
    # ----------------------------------------------------------------- #
    #                          Init Client GUI                          #
    # ----------------------------------------------------------------- #

    def __init__(self):
        self.client = None
        self.conn_flag = False

        self.app = Tk()  # init app window
        self.style = ttk.Style()  # init style
        self.top = None

        self.curr_frame = None  # current window
        self.conn_frame = Frame(self.app)  # connection window
        self.table_selection_frame = Frame(self.app)  # table selection window
        self.table_view_frame = Frame(self.app)  # table view window

        self.table_listbox = None
        self.table_list = []  # list of all available tables in the database
        self.curr_table = None  # current accessed table
        self.curr_tree_view_table = None

        self.app_config()  # configure app settings
        self.style_config()  # configure style settings
        self.error_label = None  # label that pops up when an error occurred
        self.curr_value_label = None
        self.curr_value = ""
        self.update_label = None

    # run the application
    def run(self):
        table_list_update = Thread(target=self.get_table_update)
        table_list_update.start()

        self.conn_frame_setup()
        self.app.mainloop()

    # ----------------------------------------------------------------- #
    #                       App related Section                         #
    # ----------------------------------------------------------------- #

    # configure application properties
    def app_config(self):
        self.app.title("DataMaster_Client")  # set the window's name
        self.app.geometry("972x648")  # set the window resolution
        self.app.wm_geometry("+{}+{}".format(self.app.winfo_screenheight() // 2 - 150, 200))  # set window spawn point

        self.app.resizable(False, False)  # disable resize
        self.conn_frame.configure(background="#333333")  # set the background color of connection window
        self.table_selection_frame.configure(background="#333333")  # set the background color of table selection window
        self.table_view_frame.configure(background="#333333")  # set the background color of table view window

        self.app.iconphoto(False, PhotoImage(file="assets\\icon.png"))  # set window icon

    # configure application style properties
    def style_config(self):
        # Use a dark mode theme
        self.style.theme_use("clam")
        self.style.configure("TLabel", foreground="white", background="#333333")
        self.style.configure("TEntry", foreground="black", background="#444444")
        self.style.configure("TButton", foreground="white", background="#4CAF50")

    # init and configure pop up window dialog
    def top_config(self, title, bg_color):
        self.top = Toplevel()  # init pop up window
        self.top.title(title)  # set pop up title
        self.top.resizable(False, False)  # disable resize
        self.top.configure(background=bg_color)  # set background color of pop up window
        self.top.wm_geometry("+{}+{}".format(self.curr_frame.winfo_screenheight() // 2 + 150,
                                             self.curr_frame.winfo_screenheight() // 2 - 100))  # set pop up spawn point

    # pop up dialog for confirmation
    def confirmation_dialog(self, message):
        # get confirmation widgets
        def get_widgets():
            msg_label_ = Label(self.top, text=message, padx=20, pady=10, font=("Arial Rounded MT Bold", 10),
                               bg="#333333", fg="white")
            ok_button_ = Button(self.top, text="OK", command=ok, bg="#4CAF50", fg="white")
            cancel_button_ = Button(self.top, text="Cancel", command=cancel, bg="#4CAF50", fg="white")
            return msg_label_, ok_button_, cancel_button_

        def ok():
            result.set(True)
            self.top.destroy()

        def cancel():
            result.set(False)
            self.top.destroy()
            self.top = None

        self.top_config("Confirmation", "#333333")
        msg_label, ok_button, cancel_button = get_widgets()

        msg_label.pack()

        result = BooleanVar()

        ok_button.pack(side=RIGHT, padx=10, pady=3)
        cancel_button.pack(side=LEFT, padx=10, pady=3)

        self.top.transient(master=self.app)
        self.top.grab_set()

        self.app.wait_window(self.top)

        return result.get()

    # remove the current showed frame
    def unpack_curr_frame(self):
        if self.curr_frame is None:
            return
        else:
            self.curr_frame.pack_forget()

    # reset the error label for re-use
    def reset_error_label(self):
        if self.error_label is not None:
            self.error_label.destroy()

    # reset the update label for re-use
    def reset_update_label(self):
        if self.update_label is not None:
            self.update_label.destroy()

    # reset the current chosen action (max,min,sum,avg) label
    def reset_curr_value_label(self):
        if self.curr_value_label is not None:
            self.curr_value_label.destroy()

    # thread that constantly updated the table info if changed in the client socket
    def get_table_update(self):
        while True:
            if self.client is not None:
                try:
                    if self.table_list != self.client.table_list:
                        self.table_list = self.client.table_list
                        self.table_listbox.delete(0, END)
                        for table in self.table_list:
                            self.table_listbox.insert(END, table)
                except:
                    self.table_list = []

                try:
                    if self.curr_table != self.client.curr_table:
                        tmp = self.curr_table
                        self.curr_table = self.client.curr_table
                        if self.curr_table is not None:
                            if tmp is None:
                                self.table_view_frame_setup()
                            else:
                                self.update_label = ttk.Label(self.curr_frame, text="An update is available, "
                                                                                    "please restart the table view",
                                                              font=("Arial Rounded MT Bold", 15))
                                self.update_label.pack(pady=10)

                except:
                    self.curr_table = None

                if self.curr_value != self.client.curr_value:
                    self.curr_value = self.client.curr_value
                    self.reset_curr_value_label()
                    try:
                        self.curr_value_label = ttk.Label(self.curr_frame, text=str(self.curr_value),
                                                          font=("Arial Rounded MT Bold", 15))
                        self.curr_value_label.place(x=200, y=360)
                    except:
                        self.reset_curr_value_label()

    # disconnect client from the server and go back to connection frame
    def server_disconnect(self):
        self.conn_frame_setup()
        self.client.disconnect()
        self.conn_flag = False
        self.table_list = []  # list of all available tables in the database
        self.curr_table = None  # current accessed table
        self.table_listbox = None

    # ----------------------------------------------------------------- #
    #                       Connection Section                          #
    # ----------------------------------------------------------------- #

    # generate the connection frame widgets (labels, buttons, etc...)
    def init_conn_frame_widgets(self, attempt_conn):
        # get connection frame widgets
        def get_widgets():
            ip_label_ = ttk.Label(self.curr_frame, text="Server IP:", font=("Arial Rounded MT Bold", 20))
            ip_entry_ = ttk.Entry(self.curr_frame, width=15, font=("Arial Rounded MT Bold", 20))
            port_label_ = ttk.Label(self.curr_frame, text="Port:", font=("Arial Rounded MT Bold", 20))
            port_entry_ = ttk.Entry(self.curr_frame, width=15, font=("Arial Rounded MT Bold", 20))
            connect_button_ = ttk.Button(self.curr_frame, text="Connect", width=20, padding=15,
                                         command=lambda: [attempt_conn(ip_entry.get(), port_entry.get())])
            logo = tk.PhotoImage(file="assets/logo_bg.png")
            logo_label_ = tk.Label(self.curr_frame, image=logo, bg="#333333")
            logo_label_.image = logo  # keep a reference to the PhotoImage object

            return ip_label_, ip_entry_, port_label_, port_entry_, connect_button_, logo_label_

        ip_label, ip_entry, port_label, port_entry, connect_button, logo_label = get_widgets()

        logo_label.place(x=130, y=20)
        ip_label.place(x=290, y=445)
        ip_entry.place(x=430, y=445)
        port_label.place(x=355, y=495)
        port_entry.place(x=430, y=495)

        # Create the button to connect to the server
        connect_button.place(x=410, y=550)

    # set up the connection frame window
    def conn_frame_setup(self):
        # attempt connecting to the server
        def attempt_conn(ip, port):

            if self.error_label is not None:
                self.error_label.destroy()

            if ip == "" or port == "":
                self.error_label = ttk.Label(self.curr_frame, text="Both IP and Port must be filled, please try again",
                                             font=("Arial Rounded MT Bold", 10))
                self.error_label.place(x=335, y=610)
                return

            elif port.isdigit() is False:
                self.error_label = ttk.Label(self.curr_frame, text="Port must be an integer, please try again",
                                             font=("Arial Rounded MT Bold", 10))
                self.error_label.place(x=350, y=610)
                return

            else:
                if self.conn_flag is False:
                    self.client = ClientSocket(ip, int(port))
                    try:
                        self.client.start()
                        self.conn_flag = True
                        time.sleep(1)
                    except:
                        self.error_label = ttk.Label(self.curr_frame,
                                                     text="Connection failed, timeout error has occurred",
                                                     font=("Arial Rounded MT Bold", 10))
                        self.error_label.place(x=330, y=610)
                        self.client = None
                        self.conn_flag = False

                while self.client is not None:
                    if self.client.conn_flag is True:
                        self.table_list = self.client.table_list
                        print(f"[+] Got table list {self.table_list} from the server")
                        self.table_selection_frame_setup()
                        break
                    else:
                        self.error_label = ttk.Label(self.curr_frame,
                                                     text="Connection failed, timeout error has occurred",
                                                     font=("Arial Rounded MT Bold", 10))
                        self.error_label.place(x=330, y=610)
                        self.client = None
                        self.conn_flag = False

        self.unpack_curr_frame()
        self.curr_frame = self.conn_frame

        self.init_conn_frame_widgets(attempt_conn)

        self.curr_frame.pack(fill=BOTH, expand=True)
        self.curr_frame.tkraise()

    # ----------------------------------------------------------------- #
    #                   Table Selection Section                         #
    # ----------------------------------------------------------------- #

    # pop up dialog for table creation
    def table_creation_dialog(self):
        # get table creation global widgets
        def get_widgets():
            name_label_ = Label(self.top, text="Enter table name:", padx=20, pady=10,
                                font=("Arial Rounded MT Bold", 20), bg="#333333", fg="white")
            name_entry_ = ttk.Entry(self.top, width=17, font=("Arial Rounded MT Bold", 20))
            column_num_label_ = Label(self.top, text="Enter number of columns:", padx=20, pady=10,
                                      font=("Arial Rounded MT Bold", 20), bg="#333333", fg="white")
            column_num_entry_ = ttk.Entry(self.top, width=17, font=("Arial Rounded MT Bold", 20))

            return name_label_, name_entry_, column_num_label_, column_num_entry_

        # create new table
        def create(name, column_num):
            # get create widgets
            def get_create_widgets():
                create_button_ = Button(self.top, text="Create", command=check_entries, bg="#4CAF50", fg="white")
                table_name_label_ = Label(self.top, text=f"Table: {name}", pady=5, padx=20,
                                          font=("Arial Rounded MT Bold", 20), bg="#333333", fg="white")
                return create_button_, table_name_label_

            # check if all item [0] in list of tuples is different
            def check_all_different(final_column_list):
                names = [name_ for name_, _ in final_column_list]
                return len(names) == len(set(names))

            # check if all the entries are valid
            def check_entries():
                self.reset_error_label()

                for column in column_list:
                    if column[0].get() == "":
                        self.error_label = Label(self.top,
                                                 text="Not all names are filled, please fill all of the names "
                                                      "and try again", padx=7, pady=10,
                                                 font=("Arial Rounded MT Bold", 8),
                                                 bg="#333333", fg="white")
                        self.error_label.pack()
                        return

                # Save all the answers to a list
                final_column_list = [(column[0].get(), column[1].get()) for column in column_list]
                if check_all_different(final_column_list):
                    final_column_list.insert(0, name.replace(" ", "_"))
                    self.client.create_table(final_column_list)

                    self.top.destroy()
                    self.top = None
                    return final_column_list
                else:
                    self.error_label = Label(self.top,
                                             text="Column names can't be the same, please write a unique name for "
                                                  "each column and try again", padx=7, pady=10,
                                             font=("Arial Rounded MT Bold", 8),
                                             bg="#333333", fg="white")
                    self.error_label.pack()
                return

            column_list = []
            create_button, table_name_label = get_create_widgets()
            create_button.pack(side=RIGHT, padx=10)
            table_name_label.pack()

            options = ["Integer", "Double", "String"]

            for i in range(column_num):
                # create a new frame for each row of widgets
                row_frame = Frame(self.top, bg="#333333")

                selected_option = StringVar()
                selected_option.set(options[0])

                if i == 0:
                    selected_option.set(options[0])
                    # add the widgets for this row in the frame
                    column_name_label = Label(row_frame, text="Primary Key Name:", font=("Arial Rounded MT Bold", 10),
                                              bg="#333333",
                                              fg="white")
                    column_name_entry = Entry(row_frame)
                    column_type_label = Label(row_frame, text="Type:", font=("Arial Rounded MT Bold", 10), bg="#333333",
                                              fg="white")
                    column_type_entry = OptionMenu(row_frame, selected_option, *["Integer"])
                else:
                    # add the widgets for this row in the frame
                    column_name_label = Label(row_frame, text="Name:", font=("Arial Rounded MT Bold", 10), bg="#333333",
                                              fg="white")
                    column_name_entry = Entry(row_frame)
                    column_type_label = Label(row_frame, text="Type:", font=("Arial Rounded MT Bold", 10), bg="#333333",
                                              fg="white")
                    column_type_entry = OptionMenu(row_frame, selected_option, *options)

                # pack the widgets in the row frame
                column_name_label.pack(side=LEFT, padx=5, pady=5)
                column_name_entry.pack(side=LEFT, padx=5, pady=5)
                column_type_label.pack(side=LEFT, padx=5, pady=5)
                column_type_entry.pack(side=LEFT, padx=5, pady=5)

                # add the name and type widgets to the column_list
                column_list.append((column_name_entry, selected_option))

                # pack the row frame in the main frame
                row_frame.pack()

        # continue to next stage of creation
        def continue_():
            self.reset_error_label()

            if name_entry.get() == "" or column_num_entry.get() == "":
                self.error_label = Label(self.top,
                                         text="Both name and number of columns must be filled, please try again",
                                         padx=7, pady=10, font=("Arial Rounded MT Bold", 8), bg="#333333", fg="white")
                self.error_label.pack()
                return

            if column_num_entry.get().isnumeric() is False or int(column_num_entry.get()) <= 1:
                self.error_label = Label(self.top,
                                         text="Number of columns must a positive integer > 1, please try again",
                                         padx=7, pady=10, font=("Arial Rounded MT Bold", 8), bg="#333333", fg="white")
                self.error_label.pack()
                return

            continue_button.pack_forget()

            create(name_entry.get(), int(column_num_entry.get()))
            name_label.pack_forget()
            name_entry.pack_forget()
            column_num_label.pack_forget()
            column_num_entry.pack_forget()

        # cancel creation and close pop up
        def cancel():
            self.top.destroy()
            self.top = None
            return

        self.top_config("Table Creation", "#333333")
        self.reset_error_label()
        name_label, name_entry, column_num_label, column_num_entry = get_widgets()

        name_label.pack()
        name_entry.pack()

        column_num_label.pack()
        column_num_entry.pack()

        continue_button = Button(self.top, text="Continue", command=continue_, bg="#4CAF50", fg="white")
        cancel_button = Button(self.top, text="Cancel", command=cancel, bg="#4CAF50", fg="white")

        continue_button.pack(side="right", padx=10, pady=10)
        cancel_button.pack(side="left", padx=10, pady=10)

        self.top.transient(master=self.app)
        self.top.grab_set()

        self.app.wait_window(self.top)

    # generate the table selection frame widgets (labels, buttons, etc...)
    def init_table_selection_frame_widgets(self):
        # get table selection frame widgets
        def get_widgets():
            create_table_button_ = ttk.Button(self.curr_frame, text="Create Table", padding=15, width=40,
                                              command=lambda: [self.table_creation_dialog()])
            delete_table_button_ = ttk.Button(self.curr_frame, text="Delete Table", padding=15, width=19,
                                              command=lambda: [delete_table()])

            access_table_button_ = ttk.Button(self.curr_frame, text="Access Table", padding=15, width=67,
                                              command=lambda: [access_table()])

            disconnect_button_ = ttk.Button(self.curr_frame, text="Disconnect", padding=15, width=67,
                                            command=lambda: [self.server_disconnect()])

            table_list_label_ = ttk.Label(self.curr_frame, text="___________Table List____________",
                                          font=("Arial Rounded MT Bold", 20, "bold", "underline"))

            table_listbox_ = Listbox(self.curr_frame, width=40, height=23, font=("Arial Rounded MT Bold", 15),
                                     bg="gray", fg="white")

            return create_table_button_, delete_table_button_, disconnect_button_, table_list_label_, table_listbox_, access_table_button_

        # get selected table
        def get_selected_table(listbox):
            if not listbox.curselection():
                return None
            return listbox.curselection()[0]

        # delete table from table list
        def delete_table():
            try:
                table = get_selected_table(table_listbox)
                self.reset_error_label()

                if table is None:
                    self.error_label = ttk.Label(self.curr_frame, text="Table not selected, "
                                                                       "please select a table and try again",
                                                 font=("Arial", 10))
                    self.error_label.place(x=520, y=120)
                    return
                else:
                    choice = self.confirmation_dialog(f"Delete table {table_listbox.get(table)}?")
                    if choice is False:
                        return
                    else:
                        self.client.delete_table(table)
            except:
                pass

        # access table info
        def access_table():
            try:
                table = self.client.table_list[get_selected_table(table_listbox)]
                self.reset_error_label()

                if table is None:
                    self.error_label = ttk.Label(self.curr_frame, text="Table not selected, "
                                                                       "please select a table and try again",
                                                 font=("Arial", 10))
                    self.error_label.place(x=520, y=200)
                    return
                else:
                    self.client.access_table(table)
            except:
                pass

        create_table_button, delete_table_button, disconnect_button, table_list_label, table_listbox, access_table_button = get_widgets()
        self.table_listbox = table_listbox

        for table in self.table_list:
            self.table_listbox.insert(END, table)

        table_list_label.place(x=15, y=15)
        table_listbox.place(x=15, y=62)

        create_table_button.place(x=520, y=62)
        delete_table_button.place(x=810, y=62)
        access_table_button.place(x=520, y=127)

        disconnect_button.place(x=520, y=568)

    # set up the table selection frame window
    def table_selection_frame_setup(self, label=None, tree_view=None):
        self.unpack_curr_frame()
        if label is not None and tree_view is not None:
            label.pack_forget()
            tree_view.pack_forget()
        self.reset_update_label()
        self.reset_curr_value_label()
        self.curr_frame = self.table_selection_frame

        self.curr_table = None
        self.client.curr_table = None
        self.init_table_selection_frame_widgets()

        self.curr_frame.pack(fill=BOTH, expand=True)
        self.curr_frame.tkraise()

    # ----------------------------------------------------------------- #
    #                     Table View Section                            #
    # ----------------------------------------------------------------- #

    # set up the table view frame window
    def table_view_frame_setup(self):
        self.unpack_curr_frame()
        self.curr_frame = self.table_view_frame

        self.init_table_view_frame_widgets()

        self.curr_frame.pack(fill=BOTH, expand=True)
        self.curr_frame.tkraise()

    # generate the table view frame widgets (labels, buttons, etc...)
    def init_table_view_frame_widgets(self):
        # get table selection frame widgets
        def get_widgets():

            previous_page_button_ = ttk.Button(self.curr_frame, text="Previous Page", padding=15, width=144,
                                               command=lambda: [
                                                   self.table_selection_frame_setup(table_name_label,
                                                                                    self.curr_tree_view_table)])

            create_instance_button_ = ttk.Button(self.curr_frame, text="Create Instance", padding=15, width=67,
                                                 command=lambda: [self.instance_creation_dialog(self.curr_table[1])])

            delete_instance_button_ = ttk.Button(self.curr_frame, text="Delete Instance", padding=15, width=67,
                                                 command=lambda: [delete_instance()])

            table_name_label_ = ttk.Label(self.curr_frame, text=str(self.curr_table[0]), padding=15,
                                          font=("Arial Rounded MT Bold", 20))

            max_button_ = ttk.Button(self.curr_frame, text="Get Maximum", padding=15, width=30,
                                     command=lambda: [action("MAX", selected_column_name.get())])

            min_button_ = ttk.Button(self.curr_frame, text="Get Minimum", padding=15, width=30,
                                     command=lambda: [action("MIN", selected_column_name.get())])

            sum_button_ = ttk.Button(self.curr_frame, text="Get Sum", padding=15, width=30,
                                     command=lambda: [action("SUM", selected_column_name.get())])

            avg_button_ = ttk.Button(self.curr_frame, text="Get Average", padding=15, width=30,
                                     command=lambda: [action("AVG", selected_column_name.get())])

            count_button_ = ttk.Button(self.curr_frame, text="Count Instances", padding=15, width=30,
                                       command=lambda: [count_rows()])

            return previous_page_button_, table_name_label_, create_instance_button_, delete_instance_button_, max_button_, min_button_, sum_button_, avg_button_, count_button_

        # get selected row
        def get_selected_row():
            try:
                selected_row = self.curr_tree_view_table.selection()[0]
                data = self.curr_tree_view_table.item(selected_row)['values']
                return data
            except:
                pass

        # delete instance from table list
        def delete_instance():
            try:
                row = get_selected_row()
                self.reset_error_label()

                if row is None:
                    self.error_label = ttk.Label(self.curr_frame, text="Row not selected, "
                                                                       "please select a row and try again",
                                                 font=("Arial", 10))
                    self.error_label.place(x=40, y=625)
                    return
                else:
                    choice = self.confirmation_dialog(f"Delete instance {row}?")
                    if choice is False:
                        return
                    else:
                        self.client.delete_instance(self.curr_table[0], row[0])
                        self.curr_tree_view_table.delete(self.curr_tree_view_table.selection()[0])


            except:
                pass

        def action(choice, selected_column_name):
            if selected_column_name != "":
                choice_info = f"SELECT {choice}({selected_column_name}) FROM {self.curr_table[0]}"
                self.client.get_min_max_avg_sum(choice_info)

        def count_rows():
            choice_info = f"SELECT COUNT(*) FROM {self.curr_table[0]}"
            self.client.count_rows(choice_info)

        previous_page_button, table_name_label, create_instance_button, delete_instance_button, max_button, min_button, sum_button, avg_button, count_button = get_widgets()

        previous_page_button.place(x=40, y=568)
        create_instance_button.place(x=40, y=500)
        delete_instance_button.place(x=500, y=500)
        max_button.place(x=40, y=432)
        min_button.place(x=270, y=432)
        sum_button.place(x=500, y=432)
        avg_button.place(x=730, y=432)
        count_button.place(x=270, y=364)

        selected_column_name = tk.StringVar()

        # Create label and dropdown menu for selecting column name
        column_label = tk.Label(self.curr_frame, text="Select A Column:", font=("Arial Rounded MT Bold", 12),
                                foreground="white", background="#333333")
        column_label.place(x=50, y=400)

        column_menu = tk.OptionMenu(self.curr_frame, selected_column_name, *[
            column[0] for column in self.curr_table[1] if
            column[1] in [int, float] and self.curr_table[1][0] != column])

        column_menu.place(x=200, y=390)
        table_name_label.pack()

        self.curr_tree_view_table = ttk.Treeview(self.curr_frame, columns=[column[0] for column in
                                                                           self.curr_table[1]], show='headings')

        for row in self.curr_tree_view_table.get_children():
            self.curr_tree_view_table.delete(row)

        # add the column headings to the table
        for column in self.curr_table[1]:
            self.curr_tree_view_table.heading(column[0], text=column[0])

        # add the rows to the table
        for row in self.curr_table[2]:
            self.curr_tree_view_table.insert('', 'end', values=tuple(row))
        self.curr_tree_view_table.pack()

    # pop up dialog for instance creation
    def instance_creation_dialog(self, columns):

        # check if all entries are valid
        def validate_entry(entry, column_type):
            self.reset_error_label()
            try:
                if column_type == int:
                    int(entry.get())

                elif column_type == float:
                    float(entry.get())

                elif column_type == str:
                    str(entry.get())

                else:
                    self.error_label = ttk.Label(self.top, text="Can't complete creation, "
                                                                "please check your entries and try again",
                                                 font=("Arial", 10), padding=5)
                    self.error_label.pack()
                    raise TypeError

            except (ValueError, TypeError):
                self.error_label = ttk.Label(self.top, text="Can't complete creation, "
                                                            "please check your entries and try again",
                                             font=("Arial", 10), padding=5)
                self.error_label.pack()
                return False

            return True

        # create instance
        def create_instance():
            values = []
            for entry, column_type in zip(entries, column_types):
                if validate_entry(entry, column_type):
                    if column_type == int:
                        values.append(int(entry.get()))

                    elif column_type == float:
                        values.append(float(entry.get()))

                    elif column_type == str:
                        values.append(entry.get())

                    for tup in self.curr_table[2]:
                        if tup[0] == values[0]:
                            self.error_label = ttk.Label(self.top, text="Can't complete creation, "
                                                                        "primary key value is already been taken",
                                                         font=("Arial", 10), padding=5)
                            self.error_label.pack()
                            return
                else:
                    return
            self.client.create_instance(str(self.curr_table[0]), tuple(values))
            self.curr_tree_view_table.insert('', 'end', values=tuple(values))

            cancel()

        # close popup
        def cancel():
            self.top.destroy()
            self.top = None

        self.top_config("Create Instance", "#333333")
        self.reset_error_label()

        continue_button = tk.Button(self.top, text='Continue', command=create_instance, pady=10, foreground="white",
                                    background="#4CAF50")
        cancel_button = tk.Button(self.top, text='Cancel', command=cancel, pady=10, foreground="white",
                                  background="#4CAF50")
        labels = []
        entries = []
        column_types = []
        for column_name, column_type in columns:
            row_frame = Frame(self.top, bg="#333333", padx=200, pady=7)

            column_name_label = tk.Label(row_frame, text=column_name, bg="#333333", fg="white",
                                         font=("Arial Rounded MT Bold", 10), )
            entry = tk.Entry(row_frame, font=("Arial Rounded MT Bold", 10))

            column_name_label.pack(side=LEFT)
            entry.pack(side=LEFT)

            labels.append(column_name_label)
            entries.append(entry)
            column_types.append(column_type)
            row_frame.pack()

        continue_button.pack(side=RIGHT, padx=10, pady=10)
        cancel_button.pack(side=LEFT, padx=10, pady=10)

        self.top.transient(master=self.app)
        self.top.grab_set()

        self.top.mainloop()

    # ----------------------------------------------------------------- #
    #                               Main                                #
    # ----------------------------------------------------------------- #


def main():
    client = Client()
    client.run()

    return 0


if __name__ == "__main__":
    main()
