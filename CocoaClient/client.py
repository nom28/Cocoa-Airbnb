import _tkinter
import datetime
from socket import *
import sys
from tkinter import *
from tkinter.filedialog import askopenfilenames
from tkinter import messagebox
import tkintermapview
import threading
import time
import os
from PIL import Image, ImageTk
from PIL import ImageFile

ImageFile.LOAD_TRUNCATED_IMAGES = True

class Client:
    client_socket = socket(AF_INET, SOCK_STREAM)
    is_ok = False
    is_up = True
    BUFF_SIZE = 4096
    image_queue = 0
    root = None
    mainframe = None
    log_popup = None
    log_frame = None
    map_popup = None
    map_widget = None
    apt_popup = None
    date_frame = None
    balance_label = None
    apt_listbox = None
    reserve_listbox = None
    my_apt_popup = None
    my_rsv_popup = None
    clients_listbox = None
    info = ()
    logged_in = ""
    i = 0
    picked_dates = ()
    filenames = ()
    sizes = []
    temp_data = None

    def __init__(self, ADDR):
        read_sockets = [self.client_socket]
        write_sockets = [self.client_socket]
        self.client_socket.connect(ADDR)  # (gethostbyname(gethostname()), 55757)

    def recvall(self, sock):
        """
        gets all the data sent from a socket.
        :param sock: socket of the origin of request
        :return: the data
        """
        data = b''
        while True:
            part = sock.recv(self.BUFF_SIZE)
            data += part
            if len(part) < self.BUFF_SIZE:
                # either 0 or end of data
                break
        return data

    def output_window(self):
        """
        this is the main window, that includes the map and all the buttons and entries.
        :return:
        """
        self.root = Tk()
        self.root.geometry("700x400")
        self.root.title("Cocoa")
        self.root.minsize(700, 400)
        self.mainframe = Frame(self.root, bg="#2D3047")
        self.mainframe.pack(expand=TRUE, fill=BOTH)
        self.log_frame = Frame(self.mainframe, bg="#2D3047")
        self.log_frame.pack(side=LEFT, expand=TRUE, fill=BOTH)
        register = Button(self.log_frame, text="Register", command=self.register_popup_win)
        register.place(x=10, y=10)
        login = Button(self.log_frame, text="Login", command=self.login_popup_win)
        login.place(x=70, y=10)

        self.map_widget = tkintermapview.TkinterMapView(self.mainframe, width=500, height=300, corner_radius=0,
                                                        max_zoom=18)
        self.map_widget.set_position(31.894470, 34.811467)  # Rehovot
        self.map_widget.set_zoom(13)
        self.map_widget.place(relx=0.4, rely=0.5, anchor=CENTER)
        self.map_widget.add_right_click_menu_command(label="Add Apartment",
                                                     command=self.add_apartment_event,
                                                     pass_coords=True)
        self.client_socket.send("(6, '*')".encode())

        '''map = Button(self.mainframe, text="View map", command=self.setup_map, height=5, width=15)
                map.place(x=300, y=150)'''

        Button(self.mainframe, text="Very important info!", command=self.info_popup).place(anchor=W, relx=0.8,
                                                                                           rely=0.06)

        Button(self.mainframe, text="My Apartments", command=self.get_my_apartments).place(anchor=W, relx=0.3, rely=0.06)
        Button(self.mainframe, text="My Reservations", command=self.get_my_reservations).place(anchor=W, relx=0.5, rely=0.06)

        self.balance_label = Label(self.mainframe, text="Balance: 0 credits", bg="#2D3047", fg="white")
        self.balance_label.place(anchor=W, relx=0.05, rely=0.9)

        self.date_frame = Frame(self.mainframe, bg="#2D3047", width=140, height=300)
        self.date_frame.place(anchor=E, relx=0.97, rely=0.5)

        from_var = StringVar()
        to_var = StringVar()
        Label(self.date_frame, text="Dates:", padx=5, pady=10, bg="#2D3047", fg="white").grid(column=0, row=0)
        Label(self.date_frame, text="From:", padx=5, pady=10, bg="#2D3047", fg="white").grid(column=0, row=1)
        Entry(self.date_frame, textvariable=from_var).grid(column=0, row=2)
        Label(self.date_frame, text="To:", padx=5, pady=10, bg="#2D3047", fg="white").grid(column=0, row=3)
        Entry(self.date_frame, textvariable=to_var).grid(column=0, row=4)
        b = Button(self.date_frame, text="Update", command=lambda: self.update_date(from_var.get(), to_var.get()))
        b.grid(column=0, row=5, pady=15)

        self.place_var = StringVar()
        e = Entry(self.mainframe, textvariable=self.place_var, width=30)
        e.place(anchor=W, relx=0.25, rely=0.94)
        e.bind("<Return>", self.search_event)
        Button(self.mainframe, text="Search", command=self.search_event).place(anchor=W, relx=0.55, rely=0.94)

        self.root.mainloop()

        self.is_up = False

    def search_event(self, event=None):
        self.map_widget.set_address(self.place_var.get())
        # self.slider_1.set(self.map_widget.zoom)

    def add_apartment_event(self, coords):
        """
        activates when a user right-clicks on the map and wishes to upload a new apartment
        :param coords:
        :return:
        """
        if self.logged_in == "":
            messagebox.showerror(None, "Error, you must be logged in")
            return
        # the idea is that the initial button in the mainframe will send the message to the server and the message from the server is going to trigger this popup
        # self.client_socket.send("(5, 1007)".encode())
        # line here to delete all previous files in temp_images / line could be in redirector
        print(coords)
        self.apt_popup = Toplevel(self.root)
        self.apt_popup.geometry("500x300")
        self.apt_popup.resizable(width=False, height=False)

        name_var = StringVar()
        Label(self.apt_popup, text="Name:", padx=2, pady=10).grid(column=0, row=0)
        Entry(self.apt_popup, textvariable=name_var).grid(column=1, row=0)  # rowspan=2?

        beds_var = StringVar()
        Label(self.apt_popup, text="Beds: ", padx=2, pady=10).grid(column=3, row=0)
        Entry(self.apt_popup, textvariable=beds_var).grid(column=4, row=0)

        baths_var = StringVar()
        Label(self.apt_popup, text="Bathrooms: ", padx=2, pady=10).grid(column=3, row=1)
        Entry(self.apt_popup, textvariable=baths_var).grid(column=4, row=1)

        price_var = StringVar()
        Label(self.apt_popup, text="Price per night: ", padx=2, pady=10).grid(column=0, row=1)
        Entry(self.apt_popup, textvariable=price_var).grid(column=1, row=1)
        Label(self.apt_popup, text="₪", padx=0, pady=5).grid(column=2, row=1)

        Label(self.apt_popup, text="Description: ", padx=2, pady=10).grid(column=0, row=2, columnspan=2)
        description = Text(self.apt_popup, height=8, width=30, padx=10, pady=10)
        description.grid(column=0, row=3, rowspan=4, columnspan=3, padx=10, pady=10)

        from_var = StringVar()
        Label(self.apt_popup, text="Available", padx=2, pady=10).grid(column=3, row=2)
        Label(self.apt_popup, text="from: ", padx=2, pady=10).grid(column=3, row=3)
        Entry(self.apt_popup, textvariable=from_var).grid(column=4, row=3)

        to_var = StringVar()
        Label(self.apt_popup, text="To: ", padx=2, pady=10).grid(column=3, row=4)
        Entry(self.apt_popup, textvariable=to_var).grid(column=4, row=4)

        Button(self.apt_popup, text="Upload pictures", command=self.upload_images).grid(column=4, row=5, padx=5,
                                                                                        pady=10)
        Button(self.apt_popup, text="Upload!",
               command=lambda: self.upload_apartment(name_var.get(), beds_var.get(), baths_var.get(), price_var.get(),
                                                     description.get('1.0', 'end-1c').replace("\n", " "), coords, from_var.get(),
                                                     to_var.get())).grid(column=4, row=6, padx=5, pady=10)

    def upload_images(self):
        """
        uploads the images to the app and prints the amount of pictures to the add apartment page.
        :return:
        """
        self.filenames = ()
        filetypes = (('PNG files', '*.png'),)

        self.filenames = askopenfilenames(title='Open files', initialdir='/', filetypes=filetypes)

        confirmation = str(len(self.filenames))+" uploaded"
        Label(self.apt_popup, text=confirmation, padx=2, pady=10).grid(column=3, row=5)

    def upload_apartment(self, name, beds, baths, price, desc, coords, from_var, to_var):
        """
        executes when pressed on the upload button of the add apartment screen,
        this def checks the information and changes in incase of irregularitys.
        then sends it to the server. if the server aproves, it shows a success message box and
        requests new markers.
        :param name:
        :param beds:
        :param baths:
        :param price:
        :param desc:
        :param coords: - tuple
        :param from_var: - date
        :param to_var: - date
        :return:
        """
        if not beds.isnumeric() or not baths.isnumeric() or not price.isnumeric():
            messagebox.showerror(None, "Error, at least one argument you entered is faulty")
            return
        # to test if the dates are valid
        try:
            junk1 = from_var.split(".")
            junk2 = to_var.split(".")
            junk1 = datetime.datetime(int(junk1[2]), int(junk1[1]), int(junk1[0]))
            junk2 = datetime.datetime(int(junk2[2]), int(junk2[1]), int(junk2[0]))
        except ValueError:
            messagebox.showerror(None, "Error, at least one date you entered is faulty")
            return
        if junk2.timestamp() - junk1.timestamp() <= 0:
            messagebox.showerror(None, "Error, date order is faulty")
            return

        name = self.clean_special_chars(name)
        desc = self.clean_special_chars(desc)

        data = f"""(1, ('{name}', '{desc}', ("{from_var}", "{to_var}"), ({price}, {beds}, {baths}), {str(coords)}, {len(self.filenames)}))"""
        self.client_socket.send(data.encode())

        initial_time = time.time()
        # if it takes too much time its conciderd as an error
        while not self.is_ok and time.time() - initial_time < 3:
            pass
        self.apt_popup.destroy()
        if self.is_ok:
            messagebox.showinfo(None, f"Success, {name} Has been uploaded! ")
        else:
            messagebox.showerror(None, "Error, Please try again later")
        self.is_ok = False

        for image in self.filenames:
            with open(image, 'rb') as f:
                self.client_socket.send(f.read())

            initial_time = time.time()
            # if it takes too much time its conciderd as an error
            while not self.is_ok and time.time() - initial_time < 5:
                pass
            self.apt_popup.destroy()
            if self.is_ok:
                print("image uploaded")
            else:
                print("error with image upload")
            self.is_ok = False

        self.client_socket.send("(6, '*')".encode())

    @staticmethod
    def clean_special_chars(data):
        """
        removes any potentially hazardous chars from given data.
        :param data:
        :return: clean data :)
        """
        special_chars = ")('\""

        for char in special_chars:
            data = data.replace(char, "")

        return data

    def update_date(self, from_var, to_var):
        """
        updates the class variable of selected_dates to show only the markers available on these dates.
        it removes any other markers and this date is the date that will
        be reserved when a user hits the reserve button.
        :param from_var:
        :param to_var:
        :return:
        """
        dates = str((from_var, to_var))
        from_var = from_var.split(".")
        to_var = to_var.split(".")
        try:
            from_var = datetime.datetime(int(from_var[2]), int(from_var[1]), int(from_var[0]))
            to_var = datetime.datetime(int(to_var[2]), int(to_var[1]), int(to_var[0]))
        except ValueError:
            messagebox.showerror(None, "Error, at least one of the dates you entered is faulty")
            return

        if to_var.timestamp() - from_var.timestamp() <= 0:
            messagebox.showerror(None, "Error, wrong date order")
            return

        self.picked_dates = dates
        # setting new markers for that date
        self.client_socket.send(("(6, " + str(dates) + ")").encode())
        messagebox.showinfo(None, "Success, dates set")

    def info_popup(self):
        """
        shows set text message i wrote to help get around the app.
        :return:
        """
        popup = Toplevel(self.root)
        popup.geometry("500x300")
        popup.resizable(width=False, height=False)

        text_widget = Text(popup, height=20, width=70)
        text_widget.pack(side=LEFT)

        path = os.path.dirname(os.path.abspath(__file__)) + "/Info.txt"
        with open(path, "r") as f:
            text_widget.insert(END, f.read())
        text_widget.configure(state=DISABLED)

    def setup_markers(self, data):
        """
        a message from the server activates this def, when this def is called it prints all the markers
        given to it, in cases the user is logged in, it shows in green this users apartments.
        :param data:
        :return:
        """
        data = eval(data)

        old_markers = self.map_widget.canvas_marker_list
        markers_to_delete = []
        for old_marker in old_markers:
            markers_to_delete.append(old_marker)
        for marker in markers_to_delete:
            marker.delete()

        for x in data:
            coords = eval(x[2])
            if coords is str:
                coords = eval(coords)
            print(x)
            if self.logged_in != "":
                if x[3]:
                    self.map_widget.set_marker(coords[0], coords[1], text=x[1], marker_color_circle='green')
                else:
                    temp = "(5, {})".format(x[0])
                    self.map_widget.set_marker(coords[0], coords[1], text=x[1], data=temp,
                                               command=lambda arg: self.page_request(arg))

            else:
                temp = "(5, {})".format(x[0])
                print(temp)
                self.map_widget.set_marker(coords[0], coords[1], text=x[1], data=temp,
                                           command=lambda arg: self.page_request(arg))

    def page_request(self, arg):
        print(arg)
        print(arg.data)
        self.client_socket.send(arg.data.encode())

    def apt_lookup_page(self, data):
        """
        when clicking on a marker this pops up with all the info on the apartment
        including pictures and a reserve button to reserve with the dates set from update_date()
        :param data:
        :return:
        """
        # the idea is that the initial button in the mainframe will send the message to the server and the message from the server is going to trigger this popup
        # self.client_socket.send("(5, 1007)".encode())
        # line here to delete all previous files in temp_images / line could be in redirector
        data = eval(data)
        self.apt_popup = Toplevel(self.root)
        self.apt_popup.geometry("500x300")
        self.apt_popup.resizable(width=False, height=False)

        Label(self.apt_popup, text=data[1], padx=5, pady=10).grid(column=0, row=0)

        details = eval(data[4])
        bed_bath_info = f"beds - {details[1]}, baths - {details[2]}"
        Label(self.apt_popup, text=bed_bath_info, padx=5, pady=10).grid(column=1, row=0)
        Label(self.apt_popup, text=f"Price per night: {details[0]}₪", padx=5, pady=10).grid(column=0, row=1, padx=80)

        rating = eval(data[7])
        rating = f"Rating: {str(rating[0])}/5 ({str(rating[1])}) "
        Label(self.apt_popup, text=rating, padx=5, pady=10).grid(column=1, row=1)

        Label(self.apt_popup, text="Description:\n" + data[2], padx=5, pady=10, justify=LEFT, relief='groove',
              wraplength=200).grid(column=0, row=2, rowspan=2)
        '''text_box = Text(self.apt_popup, height=12, width=40)
        text_box.grid(column=0, row=2, rowspan=2)
        text_box.insert('end', "Description:\n"+data[2])
        text_box.config(state='disabled')'''

        Button(self.apt_popup, text="View pictures", command=self.picture_window).grid(column=1, row=2, padx=5, pady=10)
        com = f"(4, ({data[0]}, {str(self.picked_dates)}))"
        Button(self.apt_popup, text="Reserve!", command=lambda: self.reserve_apt(com)).grid(column=1, row=3, padx=5,
                                                                                            pady=10)

    def picture_window(self):
        """
        when clicking look at pictures this window shows up to show the pictures.
        :return:
        """
        popup = Toplevel(self.root)
        popup.geometry("500x300")
        popup.resizable(width=False, height=False)
        self.i = 0

        def start():
            if self.i >= (len(images) - 1):
                self.i = 0
                slide_image.config(image=images[self.i])
            else:
                self.i = self.i + 1
                slide_image.configure(image=images[self.i])

        images = []
        path = os.path.dirname(os.path.abspath(__file__)) + "/temp_images"
        for x in os.listdir(path):
            image = Image.open(path + "/" + x)
            max_size_ratio = max(image.size[0] / 350, image.size[1] / 170)
            if max_size_ratio > 1:
                image = image.resize((int(image.size[0] / max_size_ratio), int(image.size[1] / max_size_ratio)))
            images.append(ImageTk.PhotoImage(image))
        try:
            slide_image = Label(popup, image=images[self.i])
            slide_image.pack(pady=20)
        except IndexError:
            popup.destroy()
            messagebox.showwarning(None, 'No images attached to this apartment')
            return
        # create buttons
        btn1 = Button(popup, text="next", relief=GROOVE, command=lambda: start())
        btn1.pack(side=LEFT, padx=50, pady=20)

    def reserve_apt(self, data):
        """
        activates when user clicks on the reserve button in apt_lookup_page()
        it uses dates set from update_date() and requests from the server to reserve apartment.
        :param data:
        :return:
        """
        if self.logged_in != "":
            print(data)
            if not self.picked_dates:
                self.apt_popup.destroy()
                messagebox.showerror(None, "Error, You didn't set dates")
                return
            if eval(data)[1][1] != "()":
                self.client_socket.send(data.encode())
            else:
                self.apt_popup.destroy()
                messagebox.showerror(None, "Error, You didn't prodive any dates")
                return
        else:
            self.apt_popup.destroy()
            messagebox.showerror(None, "Error, You aren't logged in")
            return
        initial_time = time.time()
        # if it takes too much time its conciderd as an error
        while not self.is_ok and time.time() - initial_time < 3:
            pass
        self.apt_popup.destroy()
        print(self.is_ok)
        if self.is_ok:
            messagebox.showinfo(None, "Success, apartment reserved")

        else:
            messagebox.showerror(None, "Error, Please try again later, make sure you have enough money")
        self.is_ok = False

        time.sleep(0.1)
        self.client_socket.send("(7,1)".encode())

    def register_popup_win(self):
        """
        popup that shows when a user clicks on the register button.
        it has the places to enter and register as a user.
        :return:
        """
        self.log_popup = Toplevel(self.root)
        self.log_popup.geometry("220x250")
        self.log_popup.resizable(width=False, height=False)
        Label(self.log_popup, text="First Name", padx=5, pady=10).grid(column=0, row=0)
        Label(self.log_popup, text="Second Name", padx=5, pady=10).grid(column=0, row=1)
        Label(self.log_popup, text="UserName", padx=5, pady=10).grid(column=0, row=2)
        Label(self.log_popup, text="Email", padx=5, pady=10).grid(column=0, row=3)
        Label(self.log_popup, text="Password", padx=5, pady=10).grid(column=0, row=4)
        answers = []
        for x in range(0, 5):
            answers.append(StringVar(self.log_popup, value=""))
            Entry(self.log_popup, textvariable=answers[x]).grid(column=1, row=x)

        b = Button(self.log_popup, text="submit",
                   command=lambda: self.send_log("(3, " + str(tuple([i.get() for i in answers])) + ")"))
        b.grid(column=0, row=5)

    def login_popup_win(self):
        """
        pop up that shows up when user clicks on the login button.
        has places for user to enter username and password.
        :return:
        """
        self.log_popup = Toplevel(self.root)
        self.log_popup.geometry("220x120")
        self.log_popup.resizable(width=False, height=False)
        Label(self.log_popup, text="UserName", padx=5, pady=10).grid(column=0, row=0)
        Label(self.log_popup, text="Password", padx=5, pady=10).grid(column=0, row=1)
        answers = []
        for x in range(0, 2):
            answers.append(StringVar(self.log_popup, value=""))
            Entry(self.log_popup, textvariable=answers[x]).grid(column=1, row=x)

        b = Button(self.log_popup, text="submit",
                   command=lambda: self.send_log("(2, " + str(tuple([i.get() for i in answers])) + ")"))
        b.grid(column=0, row=5)

    def send_log(self, data):
        """
        sends the login to the server, waits for an OK from the server and shows
        a message to the user accordingly.
        :param data:
        :return:
        """
        self.client_socket.send(data.encode())
        initial_time = time.time()
        # if it takes too much time its conciderd as an error
        while not self.is_ok and time.time() - initial_time < 5:
            pass
        self.log_popup.destroy()
        if self.is_ok:
            data = eval(data)[1]
            print(data)
            if len(data) == 2:
                self.logged_in = data[0]
            else:
                self.logged_in = data[2]
            messagebox.showinfo(None, "Success, logged as " + self.logged_in)
            self.client_socket.send("(17, '*')".encode())

            for widget in self.log_frame.winfo_children():
                widget.destroy()

            Label(self.log_frame, text="logged as: " + self.logged_in, padx=5, pady=5).place(x=10, y=5)

            # self.restore_main_win()
            # need to display on screen that i am logged in and remove the buttons of registration and login
        else:
            messagebox.showerror(None, "Error, Please try again later")

        self.is_ok = False

    def update_bal(self, data):
        self.balance_label.config(text=f"Balance: {data} credits")

    def save_images(self, data):
        """
        when gets an image this is called, it places the photo in the temp folder
        which deletes itself every time a user goes into a new apartment to look at.
        :param data: png image
        :return:
        """
        if self.temp_data != None:
            data = self.temp_data + data

        if self.sizes[0] == len(data):
            self.image_queue -= 1
            del self.sizes[0]
            path = os.path.dirname(os.path.abspath(__file__)) + "/temp_images"
            with open(path + "/{}.png".format("pn" + str(time.time()).replace(".", "")), 'wb') as f:
                f.write(data)
            self.temp_data = None
        else:
            self.temp_data = data





    def rate(self, data):
        """
        rating popup that shows the user a 1-5 scale to choose from.
        :param data:
        :return:
        """
        popup = Toplevel(self.root)
        popup.geometry("250x100")
        popup.resizable(width=False, height=False)
        data = data.split("!")
        for d in data:
            d = d.split("%")
            text = f"How did you enjoy your visit at {d[1]}?"
            Label(popup, text=text).pack(side=TOP)
            Button(popup, text=str(1), width=5, command=lambda: self.send_rating(1, d[0], popup)).pack(side=LEFT)
            Button(popup, text=str(2), width=5, command=lambda: self.send_rating(2, d[0], popup)).pack(side=LEFT)
            Button(popup, text=str(3), width=5, command=lambda: self.send_rating(3, d[0], popup)).pack(side=LEFT)
            Button(popup, text=str(4), width=5, command=lambda: self.send_rating(4, d[0], popup)).pack(side=LEFT)
            Button(popup, text=str(5), width=5, command=lambda: self.send_rating(5, d[0], popup)).pack(side=LEFT)

    def send_rating(self, data, sn, popup):
        self.client_socket.send(f"(8, ({data}, {sn}))".encode())
        popup.destroy()

    def get_my_apartments(self):
        """
        requests from the server to see all the apartments that are in the user's ownership
        :return:
        """
        if self.logged_in == "":
            messagebox.showerror(None, 'You must be logged in')
            return
        self.client_socket.send("(9, 1)".encode())

    def get_my_reservations(self):
        """
        requests from the server to see all the apartments the user has reserved
        :return:
        """
        if self.logged_in == "":
            messagebox.showerror(None, 'You must be logged in')
            return
        self.client_socket.send("(10, 1)".encode())

    def my_apartments_window(self, data):
        """
        presents all the apartment that are in ownership of the user.
        :param data:
        :return:
        """
        popup = Toplevel(self.root)
        popup.geometry("250x100")
        popup.resizable(width=False, height=False)
        popup.columnconfigure(0, weight=1)
        popup.rowconfigure(0, weight=1)

        apartments = StringVar(value=eval(data))
        self.apt_listbox = Listbox(popup, listvariable=apartments, height=9, selectmode=SINGLE)
        self.apt_listbox.grid( column=0, row=0, sticky='nwes')
        self.apt_listbox.bind('<<ListboxSelect>>', self.apt_items_selected)

    def my_reservations_window(self, data):
        """
        shows all the reserved apartments the user has.
        :param data:
        :return:
        """
        popup = Toplevel(self.root)
        popup.geometry("250x100")
        popup.resizable(width=False, height=False)
        popup.columnconfigure(0, weight=1)
        popup.rowconfigure(0, weight=1)

        apartments = StringVar(value=eval(data))
        self.reserve_listbox = Listbox(popup, listvariable=apartments, height=9, selectmode=SINGLE)
        self.reserve_listbox.grid( column=0, row=0, sticky='nwes')
        self.reserve_listbox.bind('<<ListboxSelect>>', self.rsv_items_selected)

    def apt_items_selected(self, event):
        """
        event of click on an apartment, requests to see it on a manager view
        :param event:
        :return:
        """
        try:
            apartment = self.apt_listbox.get(self.apt_listbox.curselection())
            self.client_socket.send(("(11, " + str(str(apartment).split("#")[1]) + ")").encode())
        except _tkinter.TclError:
            return

    def rsv_items_selected(self, event):
        """
        event of click on an apartment, requests to see it on a client view
        :param event:
        :return:
        """
        try:
            apartment = self.reserve_listbox.get(self.reserve_listbox.curselection())
            self.client_socket.send(("(12, " + str(str(apartment).split("#")[1]) + ")").encode())
        except _tkinter.TclError:
            return

    def my_apt_window(self, data):
        """
        this window shows all the info on the apartment that was clicked with the option to delete it.
        :param data:
        :return:
        """
        data = eval(data)
        self.my_apt_popup = Toplevel(self.root)
        self.my_apt_popup.geometry("500x300")
        self.my_apt_popup.resizable(width=False, height=False)

        Label(self.my_apt_popup, text=data[1], padx=5, pady=10).grid(column=0, row=0)

        details = eval(data[4])
        bed_bath_info = f"beds - {details[1]}, baths - {details[2]}"
        Label(self.my_apt_popup, text=bed_bath_info, padx=5, pady=10).grid(column=1, row=0)
        Label(self.my_apt_popup, text=f"Price per night: {details[0]}₪", padx=5, pady=10).grid(column=0, row=1, padx=80)

        rating = eval(data[7])
        rating = f"Rating: {str(rating[0])}/5 ({str(rating[1])}) "
        Label(self.my_apt_popup, text=rating, padx=5, pady=10).grid(column=1, row=1)

        Label(self.my_apt_popup, text="Description:\n" + data[2], padx=5, pady=10, justify=LEFT, relief='groove',
              wraplength=200).grid(column=0, row=2, rowspan=2)

        Button(self.my_apt_popup, text="View pictures", command=self.picture_window).grid(column=1, row=2, padx=5, pady=10)
        Button(self.my_apt_popup, text="Remove apartment", fg="red", command=lambda: self.remove_apt(data[0])).grid(column=1, row=3,
                                                                                                                    padx=5, pady=10)
        users = StringVar(value=eval(data[6]))
        self.clients_listbox = Listbox(self.my_apt_popup, listvariable=users, height=5, selectmode=SINGLE)
        self.clients_listbox.grid(column=0, row=4, columnspan=2, sticky='nwes')
        self.clients_listbox.bind('<<ListboxSelect>>', self.get_email_by_sn)

    def my_reservation_window(self, data):
        """
        this window shows all the info on the apartment that was clicked with the
        option to cancel reservation.
        :param data:
        :return:
        """
        data = eval(data)
        self.my_rsv_popup = Toplevel(self.root)
        self.my_rsv_popup.geometry("500x300")
        self.my_rsv_popup.resizable(width=False, height=False)

        Label(self.my_rsv_popup, text=data[1], padx=5, pady=10).grid(column=0, row=0)

        details = eval(data[4])
        bed_bath_info = f"beds - {details[1]}, baths - {details[2]}"
        Label(self.my_rsv_popup, text=bed_bath_info, padx=5, pady=10).grid(column=1, row=0)
        Label(self.my_rsv_popup, text=f"Price per night: {details[0]}₪", padx=5, pady=10).grid(column=0, row=1, padx=80)

        rating = eval(data[7])
        rating = f"Rating: {str(rating[0])}/5 ({str(rating[1])}) "
        Label(self.my_rsv_popup, text=rating, padx=5, pady=10).grid(column=1, row=1)

        dates = data[8]
        dates = f"You reserved between:\n {dates[1][0]} - {dates[1][1]} "
        Label(self.my_rsv_popup, text=dates, padx=5, pady=10).grid(column=0, row=4)

        Label(self.my_rsv_popup, text="Description:\n" + data[2], padx=5, pady=10, justify=LEFT, relief='groove',
              wraplength=200).grid(column=0, row=2, rowspan=2)

        Button(self.my_rsv_popup, text="View pictures", command=self.picture_window).grid(column=1, row=2, padx=5, pady=10)
        b = Button(self.my_rsv_popup, text="Cancel reserveation", fg="red", command=lambda: self.cancel_rsv(data[0]))
        b.grid(column=1, row=3, padx=5, pady=10)

    def remove_apt(self, data):
        """
        when clicking on the remove button in my_apt_window(), sends a request to the server.
        shows a message box according to the server's reaction.
        :param data:
        :return:
        """
        self.client_socket.send(("(13, " + str(data) + ")").encode())

        initial_time = time.time()
        # if it takes too much time its conciderd as an error
        while not self.is_ok and time.time() - initial_time < 5:
            pass
        self.my_apt_popup.destroy()
        if self.is_ok:
            messagebox.showinfo(None, "Success, apartment removed")

        else:
            messagebox.showerror(None, "Error, Please try again later or contact an admin")
        self.is_ok = False
        self.client_socket.send("(6, '*')".encode())

    def cancel_rsv(self, data):
        """
        when clicking on the cancel reservation button in my_reservation_window(),
        sends a request to the server.
        shows a message box according to the server's reaction.
        :param data:
        :return:
        """
        self.client_socket.send(("(14, " + str(data) + ")").encode())

        initial_time = time.time()
        # if it takes too much time its conciderd as an error
        while not self.is_ok and time.time() - initial_time < 5:
            pass
        self.my_rsv_popup.destroy()
        if self.is_ok:
            messagebox.showinfo(None, "Success, reservation canceled")

        else:
            messagebox.showerror(None, "Error, Please try again later or contact an admin")
        self.is_ok = False

    def get_email_by_sn(self, event):
        """
        requests name and email of a reserved person to the owner of the apartment.
        :param event:
        :return:
        """
        try:
            user = self.clients_listbox.get(self.clients_listbox.curselection())
            print(user)
            print(type(user))
            self.client_socket.send(("(15, " + str(user[0]) + ")").encode())
        except _tkinter.TclError:
            return

    def show_email(self, data):
        messagebox.showinfo(None, data)

    def add_admin_button(self):
        Button(self.mainframe, text="secret admin log", command=self.request_admin_log).place(anchor=E, relx=0.98,
                                                                                              rely=0.94)

    def request_admin_log(self):
        self.client_socket.send("(16, 1)".encode())

    def show_super_secret_admin_log(self, data):
        popup = Toplevel(self.root)
        popup.geometry("620x300")
        popup.resizable(width=False, height=False)

        text_widget = Text(popup, height=20, width=65)
        text_widget.pack(side=LEFT)
        text_widget.insert(END, data)
        text_widget.configure(state=DISABLED)

        f = Frame(popup)
        f.pack(side=LEFT)

        Button(f, text="Move time!", command=self.request_reservations).pack(side=TOP, padx=5, pady=10)
        Button(f, text="Balance log", command=self.request_bal_log).pack(side=TOP, padx=5, pady=10)

    def request_reservations(self):
        self.client_socket.send("(19, 1)".encode())

    def show_reservations(self, data):
        popup = Toplevel(self.root)
        popup.geometry("400x200")
        popup.resizable(width=False, height=False)

        reservations = StringVar(value=eval(data))
        listbox = Listbox(popup, listvariable=reservations, height=9, width=40, selectmode=SINGLE)
        listbox.grid(column=0, row=0, rowspan=3, sticky='nw')
        # self.apt_listbox.bind('<<ListboxSelect>>', self.apt_items_selected)

        Label(popup, text="days ('-' for behind):").grid(column=1, row=0)

        var = StringVar()
        e = Entry(popup, textvariable=var, width=10)
        e.grid(column=1, row=1, pady=10, padx=10)

        try:
            Button(popup, text="submit", command=lambda: self.change_dates(e.get(), listbox.get(listbox.curselection()[0]))).grid(column=1, row=2)
        except IndexError:
            messagebox.showerror(None, "select reservation before submitting!")

    def change_dates(self, days, info):
        is_negative = False
        if days[0] == "-":
            days = days[1:]
            is_negative = True
        if days.isnumeric():
            print(days)
            if is_negative:
                days = -1 * int(days)
            data = (int(days), int(info[0]), int(info[2][0]))
            print(data)
        else:
            messagebox.showerror(None, "Days must be a number")
            return
        self.client_socket.send(f"(20, {str(data)})".encode())

    def request_bal_log(self):
        self.client_socket.send("(18, 1)".encode())

    def show_bal_logs(self, data):
        popup = Toplevel(self.root)
        popup.geometry("500x300")
        popup.resizable(width=False, height=False)

        text_widget = Text(popup, height=20, width=65)
        text_widget.pack(side=LEFT)
        text_widget.insert(END, data)
        text_widget.configure(state=DISABLED)

    def get_sizes(self, data):
        print(data)
        self.sizes = eval(data)

    def listen(self):
        """
        gets the messages from the server and redirects them to the correct def.
        :return:
        """
        while self.is_up:
            try:
                data = self.recvall(self.client_socket)
                if data == "":
                    print("closed for some reason")
                    self.is_up = False
                else:
                    if self.image_queue != 0:
                        print("imaging")
                        if not self.sizes:
                            loc = data.decode(encoding='latin').find(']')
                            self.get_sizes(data.decode(encoding='latin')[:loc+1])
                            self.temp_data = data.decode(encoding='latin')[loc+1:].encode(encoding='latin')
                            print()
                        else:
                            self.save_images(data)
                    else:

                        data = data.decode(encoding='latin')
                        print(data)
                        print(type(data))
                        if data == "Ok":
                            self.is_ok = True
                            print("just okayed")
                            continue
                        if data[0] == "*":
                            self.image_queue = int(data[1])
                            data = data[2:]
                            dir = os.path.dirname(os.path.abspath(__file__)) + "/temp_images"
                            for f in os.listdir(dir):
                                os.remove(os.path.join(dir, f))
                            self.apt_lookup_page(data)
                            continue
                        if data[0] == "#":
                            self.setup_markers(data[1:])
                            continue
                        if data[0] == "$":
                            self.update_bal(data[1:])
                            continue
                        if data[0] == "!":
                            self.rate(data[1:])
                            continue
                        if data[0] == "@":
                            self.my_apartments_window(data[1:])
                            continue
                        if data[0] == "&":
                            self.my_reservations_window(data[1:])
                            continue
                        if data[0] == "^":
                            self.image_queue = int(data[1])
                            data = data[2:]
                            dir = os.path.dirname(os.path.abspath(__file__)) + "/temp_images"
                            for f in os.listdir(dir):
                                os.remove(os.path.join(dir, f))
                            self.my_apt_window(data)
                            continue
                        if data[0] == "%":
                            self.image_queue = int(data[1])
                            data = data[2:]
                            dir = os.path.dirname(os.path.abspath(__file__)) + "/temp_images"
                            for f in os.listdir(dir):
                                os.remove(os.path.join(dir, f))
                            self.my_reservation_window(data)
                            continue
                        if data[0] == ">":
                            self.show_email(data[1:])
                            continue
                        if data[0] == "A":
                            self.add_admin_button()
                            continue
                        if data[0] == "B":
                            self.show_super_secret_admin_log(data[1:])
                        if data[0] == "C":
                            self.show_bal_logs(data[1:])
                        if data[0] == "D":
                            self.show_reservations(data[1:])

            except ConnectionAbortedError:
                self.is_up = False

    def communicate(self):
        """
        starts the whole script
        :return:
        """

        print("starting up...")

        listening_thread = threading.Thread(target=self.listen)
        listening_thread.start()

        print("client is up and connected")

        self.output_window()

        self.client_socket.close()

        sys.exit()
