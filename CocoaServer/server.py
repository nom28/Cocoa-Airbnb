import datetime
import socket as s
import select
import os
from os.path import isfile, join
import time
import threading
import shutil

from CocoaData.data import DataBase

"""
Cocoa - COmfortable COsy Apartments
Author: Noam Schuldiner
the objective of this project is to make an airBnB sort of app.
to enable a person to place an apartment in a location, and let users enjoy
renting apartments as in airBnB

"""


class Server:
    """
    Server class
    this class runs a Cocoa server, it enables Mulitple port connections to the same server comuter
    at ease becouse of it being OOP.
    """
    write_sockets = []
    read_sockets = []
    messages = {}
    photo_queue = {}
    socket_user = {}
    admin_log_path = os.path.dirname(os.path.abspath(__file__)) + "/CocoaData/adminlog.txt"
    previus_day = None
    users_ended_visit = []
    check_ratings = False

    def __init__(self, host, port):
        self.ADDR = (host, port)
        self.server_socket = s.socket(s.AF_INET, s.SOCK_STREAM)
        self.server_socket.bind(self.ADDR)
        self.read_sockets.append(self.server_socket)
        self.is_up = True
        # Uses index to call the function from this list
        self.directory = [self.echo_com, self.add_apt_com, self.connect_com, self.create_user_com, self.reserve_apt,
                          self.send_info_on_apt, self.send_apts_to_map, self.send_balance, self.rate,
                          self.send_his_apartments, self.send_his_reservations, self.open_his_apt, self.open_his_rsv,
                          self.delete_apartment, self.cancel_reservation, self.return_email, self.send_admin_log,
                          self.send_bal_n_markers, self.send_bal_log, self.send_reservations,
                          self.update_reservation_date_admin]

    def open_socket(self):
        self.server_socket.listen(3)

    def echo_com(self, data, sock):
        self.messages[sock].append(("echoed " + data).encode())

    def create_user_com(self, data, sock):
        """
        This function creates a new user at request and confirms if the proccess has been done successfuly.
        as well as appends the creation of the user to admin log
        :param data: the data transfered to this def
        :param sock: socket of the origin of request
        :return: -> sends 'Ok' if creation is successful
        """
        db = DataBase()

        db.add_item('users', data[0], data[1], data[2], data[3], data[4], '()', '()', 500)

        result = db.show_one('users', 'serialNumber', 'userName="{}" and password="{}"'.format(data[2], data[4]))
        if result == -1:
            self.messages[sock].append("Error".encode())
        else:
            self.socket_user[sock] = result
            self.messages[sock].append("Ok".encode())

        with open(self.admin_log_path, 'a') as f:
            f.write(f"\n{s.gethostbyname(s.gethostname())} created new user #{result}")

        db.close()

    def connect_com(self, data, sock):
        """
        This function checks if password matches username and confirms if correct
        as well as appends the login to admin log
        :param data: the data transfered to this def
        :param sock: socket of the origin of request
        :return: -> sends 'Ok' if login is successful
        """
        db = DataBase()
        result = db.show_one('users', 'serialNumber', 'userName="{}" and password="{}"'.format(data[0], data[1]))
        if result == -1:
            self.messages[sock].append("Error".encode())
        else:
            self.socket_user[sock] = result
            with open(self.admin_log_path, 'a') as f:
                f.write(f"\n{s.gethostbyname(s.gethostname())} logged into user #{result}")
            self.messages[sock].append("Ok".encode())
            if result == 1:
                self.messages[sock].append("A".encode())
            self.check_for_rating()

        db.close()

    def add_apt_com(self, data, sock):
        """
        Adds apartment to database due to a request, and creates a new folder for the pictures.
        the original message is accounted with a photo number which will be added to queue and
        the next x messages from this socket will be considerd as images.
        which will be sent to add_photos_com().
        as well as appends the creation of a new apartment to the adminlog
        :param data: the data transfered to this def
        :param sock: socket of the origin of request
        :return: -> sends 'Ok' if addition is successful
        """
        if sock not in self.socket_user:
            self.messages[sock].append("Error".encode())
            return False

        db = DataBase()
        sernum = str(db.last_serial[0])
        photopath = os.path.dirname(os.path.abspath(__file__)) + "/AptPhotos/p"+sernum
        if not os.path.exists(photopath):
            os.mkdir(photopath)
        x = str((self.socket_user[sock], data[2]))
        # add data[8] to the photo loc
        ser = db.add_item('apartments', data[0], data[1], x, str(data[3]), str(data[4]), "()", "(0,0)", photopath)

        my_apartments = eval(db.show_one('users', 'myApartments', 'serialNumber={}'.format(self.socket_user[sock])))
        my_apartments = list(my_apartments)
        my_apartments.append(sernum)
        my_apartments = tuple(my_apartments)

        db.update_by('users', 'myApartments="{}"'.format(str(my_apartments)), 'serialNumber={}'.format(self.socket_user[sock]))

        print(db.show_one('users', '*', 'serialNumber={}'.format(self.socket_user[sock])))
        print(db.show_all('users', '*'))

        if data[5] != 0:
            print(data[5])
            self.photo_queue[self.socket_user[sock]] = [int(data[5]), sernum]

        db.close()

        with open(self.admin_log_path, 'a') as f:
            f.write(f"\nuser #{self.socket_user[sock]} uploaded new apartment #{ser}")

        self.messages[sock].append('Ok'.encode())
        return True

    def add_photos_com(self, data, sock):
        """
        In case of a socket sending a message to server when it has a photo queue it will be sent
        to this function to save the photo in the according folder. and confirms to get another picture.
        it writes bytes into a new file created in the according folder.
        :param data: the data transfered to this def
        :param sock: socket of the origin of request
        :return: -> sends 'Ok' if photos added successfully
        """
        if sock not in self.socket_user:
            self.messages[sock].append("Error".encode())
            return
        db = DataBase()

        print(self.photo_queue)
        values = self.photo_queue[self.socket_user[sock]]
        photos_left, sernum = values
        if photos_left - 1 <= 0:
            del self.photo_queue[self.socket_user[sock]]
        else:
            self.photo_queue[self.socket_user[sock]] = [photos_left-1, sernum]

        photopath = db.show_one('apartments', 'imglocation', 'serialNumber=' + sernum)
        with open(photopath + '/{}.png'.format("pn" + str(time.time()).replace(".", "")), 'wb') as f:
            f.write(data.encode(encoding='latin'))

        self.messages[sock].append('Ok'.encode())
        db.close()

    def reserve_apt(self, data, sock):
        """
        Recives a serial number of an apartment and dates and checks if dates are in fact free
        and if the client has enough money.
        if so, rents it to the socket that requested the reservation and OK's it.
        it also transfers the money from the requester to the owner of the apartment.
        as well as saves the reservation in admin log
        :param data: the data transfered to this def
        :param sock: socket of the origin of request
        :return: -> sends 'Ok' if reservation is successful
        """
        # data: (aptSN, (dates))
        db = DataBase()
        balance = db.show_one('users', 'balance', 'serialNumber={}'.format(self.socket_user[sock]))
        price_per_night = eval(db.show_one('apartments', 'details', 'serialNumber={}'.format(data[0])))[0]

        x, y = data[1]
        x = x.split('.')
        y = y.split('.')
        dates = (datetime.datetime(int(x[2]), int(x[1]), int(x[0])), datetime.datetime(int(y[2]), int(y[1]), int(y[0])))
        days = dates[1] - dates[0]
        days = days.days
        d_dates = dates

        if price_per_night * days > balance:
            self.messages[sock].append("Bal Error".encode())
            return

        dates = self.date_to_timestamp(data[1])
        owner, availability = eval(db.show_one('apartments', 'availability', 'serialNumber={}'.format(data[0])))
        taken = eval(db.show_one('apartments', 'taken', 'serialNumber={}'.format(data[0])))
        availability = self.date_to_timestamp(availability)

        if dates[0] > dates[1]:
            self.messages[sock].append("Date Error".encode())
            return

        if not (dates[0] > availability[0] and dates[1] < availability[1]):
            self.messages[sock].append("Date Error".encode())
            return

        for date in taken:
            d = self.date_to_timestamp(date[1])
            if not (dates[0] > d[1] or dates[1] < d[0]):
                self.messages[sock].append("Date Error".encode())
                return

        taken = list(taken)
        taken.append((self.socket_user[sock], data[1]))
        taken = tuple(taken)
        db.update_by('apartments', 'taken="{}"'.format(taken), 'serialNumber={}'.format(data[0]))

        renting_apt = db.show_one('users', 'rentingApartments', 'serialNumber={}'.format(self.socket_user[sock]))
        renting_apt = eval(renting_apt)
        renting_apt = list(renting_apt)
        renting_apt.append((data[0], data[1]))
        renting_apt = tuple(renting_apt)
        db.update_by('users', 'rentingApartments="{}"'.format(renting_apt), 'serialNumber={}'.format(self.socket_user[sock]))

        db.update_by('users', 'balance={}'.format(balance-(price_per_night*days)),
                     'serialNumber={}'.format(self.socket_user[sock]))

        owner_balance = db.show_one('users', 'balance', 'serialNumber={}'.format(owner))
        db.update_by('users', 'balance={}'.format(owner_balance + (price_per_night * days)),
                     'serialNumber={}'.format(owner))

        with open(self.admin_log_path, 'a') as f:
            f.write(f"\nuser #{self.socket_user[sock]} has rented apartment #{data[0]}, {d_dates[0]} - {d_dates[1]}")

        with open(os.path.dirname(os.path.abspath(__file__)) + "/CocoaData/balLog.txt", 'a') as f:
            f.write(f"Transactions from {self.socket_user[sock]} to {owner}, credits transfered: {price_per_night * days}\n")

        self.messages[sock].append("Ok".encode())
        db.close()

    def send_info_on_apt(self, data, sock):
        """
        recieves a serial number of an aprtment and sends all the data needed about the apartment
        to the socket. as well as sends the images to the client.
        :param data: the data transfered to this def
        :param sock: socket of the origin of request
        :return: -> sends all the data of an appartment
        """
        db = DataBase()
        info = db.show_one_fully('apartments', '*', 'serialNumber={}'.format(data))
        # to not send photo directory
        info = list(info)
        path = info.pop(8)
        info = tuple(info)
        images = [f for f in os.listdir(path) if isfile(join(path, f))]
        self.messages[sock].append((f"*{len(images)}"+str(info)).encode())
        sizes = []
        for image in images:
            with open(path+"/"+image, 'rb') as f:
                sizes.append(len(f.read()))
        self.messages[sock].append(str(sizes).encode())
        for image in images:
            with open(path+"/"+image, 'rb') as f:
                self.messages[sock].append(f.read())
        db.close()

    def send_apts_to_map(self, data, sock):
        """
        when this def is called it sends the requester the serial number, name, location and if it is
        your apartment to create markers on client side and so he knows which apartments are his.
        if there are dates included in data, it only sends apartments free on those dates.
        :param data: dates
        :param sock: socket of the origin of request
        :return: -> sends all the 'markers' of the map
        """
        db = DataBase()
        apartments = db.show_all('apartments', 'serialNumber, name, coords')
        apts_to_remove = []
        print(data)

        print("the apartments" + str(apartments))
        if data[0] != "*":
            dates = self.date_to_timestamp(data)
            for apartment in apartments:
                availability = eval(db.show_one('apartments', 'availability', 'serialNumber={}'.format(apartment[0])))[1]

                taken = eval(db.show_one('apartments', 'taken', 'serialNumber={}'.format(apartment[0])))
                availability = self.date_to_timestamp(availability)

                if not (dates[0] > availability[0] and dates[1] < availability[1]):
                    apts_to_remove.append(apartment)
                    continue

                for date in taken:
                    d = self.date_to_timestamp(date[1])
                    if not (dates[0] > d[1] or dates[1] < d[0]):
                        apts_to_remove.append(apartment)
                        continue

            for apt in apts_to_remove:
                apartments.remove(apt)

        print(apartments)

        if sock in self.socket_user:
            my_apartments = eval(db.show_one('users', 'myApartments', 'serialNumber={}'.format(self.socket_user[sock])))
            apartments_to_send = []
            for apartment in apartments:
                for apt in my_apartments:
                    if apartment[0] == int(apt):
                        temp_apartment = list(apartment)
                        temp_apartment.append(1)
                        apartments_to_send.append(temp_apartment)
                        break
                else:
                    temp_apartment = list(apartment)
                    temp_apartment.append(0)
                    apartments_to_send.append(temp_apartment)
                    print(apartments_to_send)
        else:
            apartments_to_send = apartments

        print(apartments_to_send)
        self.messages[sock].append(("#"+str(apartments_to_send)).encode())

    def send_his_apartments(self, data, sock):
        """
        sends the names and serial numbers of the apartments that are owned by the requester.
        :param data: irrelevant
        :param sock: socket of the origin of request
        :return: -> sends a tuple of - 'name #sernum'
        """
        db = DataBase()
        apts = eval(db.show_one('users', 'myApartments', 'serialNumber={}'.format(self.socket_user[sock])))
        to_send = []
        for apt in apts:
            x = db.show_one('apartments', 'name', 'serialNumber={}'.format(int(apt)))
            to_send.append(str(str(x) + " #" + str(apt)))
        to_send = str(tuple(to_send))
        self.messages[sock].append(("@"+to_send).encode())
        db.close()

    def send_his_reservations(self, data, sock):
        """
        sends all the current reservations of the requested
        :param data: irrelevant
        :param sock: socket of the origin of request
        :return: -> sends a tuple of - 'name #sernum'
        """
        db = DataBase()
        apts = eval(db.show_one('users', 'rentingApartments', 'serialNumber={}'.format(self.socket_user[sock])))
        to_send = []
        for apt in apts:
            x = db.show_one('apartments', 'name', 'serialNumber={}'.format(int(apt[0])))
            to_send.append(str(str(x) + " #" + str(apt[0])))
        to_send = str(tuple(to_send))
        self.messages[sock].append(("&"+to_send).encode())
        db.close()

    def open_his_apt(self, data, sock):
        """
        sends all the info of the apartment given in data as serial number.
        in order to open manager window to be able to delete apartment
        :param data: apartment serial number
        :param sock: socket of the origin of request
        :return: -> sends info about a specific apartment
        """
        db = DataBase()
        info = db.show_one_fully('apartments', '*', 'serialNumber={}'.format(data))
        if not info:
            return
        # to not send photo directory
        info = list(info)
        path = info.pop(8)
        info = tuple(info)
        images = [f for f in os.listdir(path) if isfile(join(path, f))]
        self.messages[sock].append((f"^{len(images)}" + str(info)).encode())
        for image in images:
            with open(path + "/" + image, 'rb') as f:
                self.messages[sock].append(f.read())
        db.close()

    def open_his_rsv(self, data, sock):
        """
        sends all the info of the apartment given in data as serial number.
        in order to open user window to be able to cancel reservation
        :param data: apartment serial number
        :param sock: socket of the origin of request
        :return: -> sends info about a specific apartment
        """
        db = DataBase()
        info = db.show_one_fully('apartments', '*', 'serialNumber={}'.format(data))
        if not info:
            return
        # to not send photo directory
        info = list(info)
        path = info.pop(8)
        for x in eval(info[6]):
            if x[0] == self.socket_user[sock]:
                info.append(x)
                break
        info = tuple(info)
        images = [f for f in os.listdir(path) if isfile(join(path, f))]
        self.messages[sock].append((f"%{len(images)}" + str(info)).encode())
        for image in images:
            with open(path + "/" + image, 'rb') as f:
                self.messages[sock].append(f.read())
        db.close()

    def delete_apartment(self, data, sock):
        """
        checks if the socket sending this request is the owner of the apartment.
        only then it will procceed in deleting the apartment and removing any remenence of it from
        other users.
        :param data: apartment serial number
        :param sock: socket of the origin of request
        :return: -> sends 'Ok' if it was successful
        """
        db = DataBase()
        data = int(data)
        avail = db.show_one('apartments', 'availability', 'serialNumber={}'.format(data))
        if eval(avail)[0] == self.socket_user[sock]:
            db.delete_items('apartments', 'serialNumber={}'.format(data))

            my_apts = eval(db.show_one('users', 'myApartments', 'serialNumber={}'.format(self.socket_user[sock])))
            for apt in my_apts:
                if data == int(apt):
                    my_apts = list(my_apts)
                    my_apts.remove(apt)
                    my_apts = tuple(my_apts)

            db.update_by('users', 'myApartments="{}"'.format(str(my_apts)), 'serialNumber={}'.format(self.socket_user[sock]))

            # deletes folder and its contents
            photo_folder = os.path.dirname(os.path.abspath(__file__)) + "/AptPhotos/p" + str(data)
            shutil.rmtree(photo_folder)

            all_users = db.show_all('users', 'serialNumber, rentingApartments')
            for user in all_users:
                reservations = eval(user[1])
                rsvs_to_delete = []
                for reservation in reservations:
                    if reservation[0] == data:
                        rsvs_to_delete.append(reservation)
                for rsv in rsvs_to_delete:
                    reservations = list(reservations)
                    reservations.remove(rsv)
                    reservation = tuple(reservations)

                db.update_by('users', 'rentingApartments="{}"'.format(str(reservations)), 'serialNumber={}'.format(user[0]))


            with open(self.admin_log_path, 'a') as f:
                f.write(f"\nApartment #{data} was deleted")

            self.messages[sock].append("Ok".encode())

        db.close()

    def cancel_reservation(self, data, sock):
        """
        removes the last regestration of the apartment given and cancels reservation.
        :param data: apartment serial number
        :param sock: socket of the origin of request
        :return: -> sends 'Ok' if it was successful
        """
        db = DataBase()
        data = int(data)
        taken = eval(db.show_one('apartments', 'taken', 'serialNumber={}'.format(data)))
        for took in taken:
            if took[0] == self.socket_user[sock]:
                dates = took[1]
                taken = list(taken)
                taken.remove(took)
                taken = tuple(taken)


                db.update_by('apartments', 'taken="{}"'.format(str(taken)), 'serialNumber={}'.format(data))

                reservations = eval(db.show_one('users', 'rentingApartments', 'serialNumber={}'.format(self.socket_user[sock])))
                for reservation in reservations:
                    if int(reservation[0]) == data:
                        reservations = list(reservations)
                        reservations.remove(reservation)
                        reservations = tuple(reservations)
                        break

                db.update_by('users', 'rentingApartments="{}"'.format(str(reservations)),
                             'serialNumber={}'.format(self.socket_user[sock]))

                with open(self.admin_log_path, 'a') as f:
                    f.write(
                        f"\nUser #{self.socket_user[sock]} removed reservation at #{data} in {dates[0]} - {dates[1]}")

                print('removed reservation')
                self.messages[sock].append("Ok".encode())

                break

        db.close()

    def send_balance(self, data, sock):
        """
        sends the requester the money it has
        :param data: irrelevant
        :param sock: socket of the origin of request
        :return: -> sends balance of user
        """
        db = DataBase()
        bal = db.show_one('users', 'balance', 'serialNumber={}'.format(self.socket_user[sock]))
        print(bal)
        self.messages[sock].append(("$"+str(bal)).encode())

    @staticmethod
    def date_to_timestamp(datetup):
        """
        :param datetup: a tuple containing 2 dates
        :return: a tuple containing the timestamps of these dates
        """
        x, y = datetup
        x = tuple(map(int, tuple(x.split('.'))))
        y = tuple(map(int, tuple(y.split('.'))))
        dates = (datetime.datetime(x[2], x[1], x[0]).timestamp(), datetime.datetime(y[2], y[1], y[0]).timestamp())
        return dates

    @staticmethod
    def rate(data, sock):
        """
        gets a rating and serial number of an apartment and calcultes new rating of that specific apartment.
        :param data: rating and serial number
        :param sock: socket of the origin of request
        :return: None
        """
        apt = data[1]
        db = DataBase()
        current_rating = eval(db.show_one('apartments', 'rating', 'serialNumber={}'.format(apt)))
        score = (current_rating[0]*current_rating[1] + data[0])/(current_rating[1]+1)
        score = str((score, current_rating[1]+1))
        db.update_by('apartments', "rating='{}'".format(score), 'serialNumber={}'.format(apt))
        db.close()

    def return_email(self, data, sock):
        """
        an owner of an apartment can request the email and name of a renter to make contact with him.
        :param data: serial number of client
        :param sock: socket of the origin of request
        :return: name and email
        """
        db = DataBase()
        first_name = db.show_one('users', 'firstName', 'serialNumber={}'.format(data))
        last_name = db.show_one('users', 'lastName', 'serialNumber={}'.format(data))
        email = db.show_one('users', 'email', 'serialNumber={}'.format(data))
        data = ">" + first_name + " " + last_name + ": " + email
        self.messages[sock].append(data.encode())
        db.close()

    def send_admin_log(self, data, sock):
        """
        checks if requester is logged in as admin, if so, sends adminlog.
        :param data: irrelevant
        :param sock: socket of the origin of request
        :return: the entire admin log
        """
        if self.socket_user[sock] != 1:
            return
        with open(self.admin_log_path, 'rb') as f:
            self.messages[sock].append("B".encode() + f.read())

    def send_bal_n_markers(self, data, sock):
        """
        easy call of 2 functions when a client logs in and needs to refresh balance and markers.
        :param data: the data transfered to this def
        :param sock: socket of the origin of request
        :return: None
        """
        self.send_balance(data, sock)
        self.send_apts_to_map(data, sock)

    def send_bal_log(self, data, sock):
        if self.socket_user[sock] != 1:
            return
        path = os.path.dirname(os.path.abspath(__file__)) + "/CocoaData/balLog.txt"
        with open(path, 'rb') as f:
            self.messages[sock].append("C".encode() + f.read())

    def send_reservations(self, data, sock):
        if self.socket_user[sock] != 1:
            return
        all_reservations = []
        db = DataBase()
        reservations = db.show_all("users", "serialNumber, userName, rentingApartments")
        for reservation in reservations:
            for apt in eval(reservation[2]):
                all_reservations.append((reservation[0], reservation[1], apt))  # apt = (SN apt, (dates))

        self.messages[sock].append("D".encode() + str(all_reservations).encode())

    def update_reservation_date_admin(self, data, sock):
        number_of_days = data[0]
        apt = data[2]
        user = data[1]
        if self.socket_user[sock] != 1:
            return
        db = DataBase()
        print(apt)
        print(type(apt))
        taken = eval(db.show_one("apartments", "taken", "serialNumber={}".format(int(apt))))
        rented = eval(db.show_one("users", "rentingApartments", "serialNumber={}".format(int(user))))
        for x, usr in enumerate(taken):
            if int(usr[0]) == int(user):
                dates = usr[1]
                from_date = dates[0].split(".")
                to_date = dates[1].split(".")
                from_date = datetime.datetime(int(from_date[2]), int(from_date[1]), int(from_date[0]))
                to_date = datetime.datetime(int(to_date[2]), int(to_date[1]), int(to_date[0]))
                from_date = from_date + datetime.timedelta(days=int(number_of_days))
                to_date = to_date + datetime.timedelta(days=int(number_of_days))
                from_date = from_date.strftime("%d.%m.%Y")
                to_date = to_date.strftime("%d.%m.%Y")

                usr = list(usr)
                usr[1] = (from_date, to_date)
                usr = tuple(usr)

                taken = list(taken)
                taken[x] = usr
                taken = tuple(taken)

                db.update_by("apartments", 'taken="'+str(taken)+'"', "serialNumber={}".format(apt))
                break

        for x, apartment in enumerate(rented):
            if int(apartment[0]) == int(apt):
                dates = apartment[1]
                from_date = dates[0].split(".")
                to_date = dates[1].split(".")
                from_date = datetime.datetime(int(from_date[2]), int(from_date[1]), int(from_date[0]))
                to_date = datetime.datetime(int(to_date[2]), int(to_date[1]), int(to_date[0]))
                from_date = from_date + datetime.timedelta(days=int(number_of_days))
                to_date = to_date + datetime.timedelta(days=int(number_of_days))
                from_date = from_date.strftime("%d.%m.%Y")
                to_date = to_date.strftime("%d.%m.%Y")

                apartment = list(apartment)
                apartment[1] = (from_date, to_date)
                apartment = tuple(apartment)

                rented = list(rented)
                rented[x] = apartment
                rented = tuple(rented)

                db.update_by("users", 'rentingApartments="' + str(rented) + '"', "serialNumber={}".format(user))
                break

        db.close()
        self.check_ratings = True
        self.messages[sock].append("Ok".encode())

    def redirector(self, socket, data):
        """
        The heart of the server. this redirects any message to the correct function using an
        index that the client has sent.
        or redirects messages to be images incase of photo queue
        :param data: the data transfered to this def
        :param socket: socket of the origin of request
        :return: None
        """

        try:
            if socket in self.socket_user:
                if self.socket_user[socket] in self.photo_queue:
                    self.add_photos_com(data, socket)
                    return
            print(data)
            data = eval(str(data))
            print(data)
            self.directory[data[0]](data[1], socket)
        except (NameError, TypeError, SyntaxError, ValueError, IndexError):
            self.messages[socket].append("Error".encode())
            raise

        """
        data = (code, data)
        code = 0 -> echo
                1 -> add apt
                2 -> connect
                3 -> create user
                4 -> make a reservation
                5 -> send info on apt
                6 -> send all apartments
                7 -> request bal
                8 -> rate
                9 -> get my apartments
                10 -> get my reservations
                11 -> open single apt
                12 -> open single reservation
                13 -> delete apartment
                14 -> cancel reservation
                15 -> get email by sn
                16 -> send admin log
                17 -> send bal and markers for map
                18 -> send bal log
                19 -> send all reservations
                20 -> change apt date
        """

    @staticmethod
    def recvall(sock):
        """
        gets all the data sent from a socket.
        :param sock: socket of the origin of request
        :return: the data
        """
        data = b''
        while True:
            part = sock.recv(4096)
            data += part
            if len(part) < 4096:
                # either 0 or end of data
                break
        return data

    def time_control(self):
        """
        I promise this is not back from the future.
        this function monitors need to delete apartments incase of availability time passing
        or summons people to rate on apartments after their visit.
        :return: None
        """
        apts_to_remove = []
        while True:
            if self.previus_day != datetime.datetime.day or self.check_ratings:
                if self.check_ratings:
                    self.check_ratings = False
                self.previus_day = datetime.datetime.day
                db = DataBase()
                apts = db.show_all('apartments', 'availability, taken, serialNumber')
                for apt in apts:
                    avail = eval(apt[0])
                    last_date = avail[1][1].split('.')
                    last_date = datetime.datetime(int(last_date[2]), int(last_date[1]), int(last_date[0])).timestamp()
                    if datetime.datetime.now().timestamp() > last_date:
                        apts_to_remove.append(apt)

                    taken = eval(apt[1])
                    for took in taken:
                        last_date = took[1][1].split('.')
                        last_date = datetime.datetime(int(last_date[2]), int(last_date[1]), int(last_date[0]))
                        print(last_date)
                        last_date = last_date.timestamp()
                        if datetime.datetime.now().timestamp() > last_date:
                            self.users_ended_visit.append((took[0], apt[2]))

                for apt in apts_to_remove:
                    db.delete_items('apartments', 'serialNumber={}'.format(apt[2]))
                    photo_folder = os.path.dirname(os.path.abspath(__file__)) + "/AptPhotos/p"+str(apt[2])
                    shutil.rmtree(photo_folder)
                    with open(self.admin_log_path, 'a') as f:
                        f.write(f"\nApartment #{apt[2]} surpassed availability - removed from database")

                self.check_for_rating()

                db.close()
        pass

    def get_key(self, val):
        """
        :param val: user serial number
        :return: socket of the user
        """
        for key, value in self.socket_user.items():
            if val == value:
                return key

        return "key doesn't exist"

    def check_for_rating(self):
        """
        every time a user logs on, checks if he had passed a reservation he had,
        and sends him a request to rate the apartment.
        :return: request to rate.
        """
        db = DataBase()
        to_be_removed = []
        for user in self.users_ended_visit:
            if user[0] in self.socket_user.values():
                name = db.show_one('apartments', 'name', 'serialNumber={}'.format(user[1]))
                key = self.get_key(user[0])
                print(key)
                self.messages[key].append(("!" + str(user[1]) + "%" + name).encode())
                to_be_removed.append(user)

                renting_apts = list(eval(db.show_one('users', 'rentingApartments', 'serialNumber={}'.format(user[0]))))
                for apt in renting_apts:
                    if apt[0] == user[1]:
                        renting_apts.remove(apt)
                        break
                print(renting_apts)
                renting_apts = str(tuple(renting_apts))
                print(renting_apts)
                db.update_by('users', 'rentingApartments="{}"'.format(renting_apts), 'serialNumber={}'.format(user[0]))

                taken = list(eval(db.show_one('apartments', 'taken', 'serialNumber={}'.format(user[1]))))

                for took in taken:
                    if took[0] == user[0]:
                        taken.remove(took)
                        break

                taken = str(tuple(taken))
                db.update_by('apartments', 'taken="{}"'.format(taken), 'serialNumber={}'.format(user[1]))

        for user in to_be_removed:
            self.users_ended_visit.remove(user)

        db.close()

    def run(self):
        """
        The main thread, runs as long as the server is up, it receives and sends all the info
        :return:
        """
        # self.send_info_on_apt(1007, "asnjd")
        time_thread = threading.Thread(target=self.time_control)
        time_thread.daemon = True
        time_thread.start()
        while self.is_up:
            try:
                readable, writeable = select.select(self.read_sockets, self.write_sockets, [])[:-1]
            except KeyboardInterrupt:
                raise
                quit()
            for socket in readable:
                if socket == self.server_socket:
                    sock, addr = socket.accept()
                    self.read_sockets.append(sock)
                    self.write_sockets.append(sock)
                    self.messages[sock] = []
                    print(addr[0] + " connected")
                    with open(self.admin_log_path, 'a') as f:
                        f.write(f"\n{addr[0]} connected")

                else:
                    try:
                        data = self.recvall(socket).decode(encoding='latin')
                        if data != '':
                            self.redirector(socket, data)
                        else:
                            print(str(s.gethostbyname(s.gethostname())) + ' has disconnected.')
                            self.read_sockets.remove(socket)
                            self.write_sockets.remove(socket)
                            if socket in self.socket_user:
                                del self.socket_user[socket]
                            with open(self.admin_log_path, 'a') as f:
                                f.write(f"\n{str(s.gethostbyname(s.gethostname()))} disconnected")
                            socket.close()
                    except (ConnectionResetError, ConnectionAbortedError, ValueError):
                        # raise
                        print(str(s.gethostbyname(s.gethostname())) + ' has disconnected.')
                        self.read_sockets.remove(socket)
                        self.write_sockets.remove(socket)
                        if socket in self.socket_user:
                            del self.socket_user[socket]
                        with open(self.admin_log_path, 'a') as f:
                            f.write(f"\n{str(s.gethostbyname(s.gethostname()))} disconnected")
                        socket.close()

            for socket in writeable:
                while self.messages[socket]:
                    print(self.messages[socket][0])
                    try:
                        socket.send(self.messages[socket][0])
                    except OSError:
                        print(socket)
                        # raise
                        print("OSError")
                    if self.messages[socket]:
                        self.messages[socket] = self.messages[socket][1:]

                # when exiting this will disconnect all sockets before shutting down.
                if not self.is_up:
                    socket.close()

        self.server_socket.close()