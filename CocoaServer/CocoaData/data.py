import sqlite3


class DataBase:
    def __init__(self):
        self.conn = sqlite3.connect('C:\Python_Projects\Cocoa - ya project\CocoaData\database.db')
        self.c = self.conn.cursor()
        with open('C:/Python_Projects/Cocoa - ya project/CocoaData/serials.txt', 'r') as file:
            self.last_serial = list(map(int, file.readline().split('.')))

    def add_item(self, tablename, *args):
        """
        :param tablename:
        :param args: should have all the info for that kind of new item
        :return:
        """
        if tablename == 'apartments':
            x = 0
        elif tablename == 'users':
            x = 1

        try:
            self.c.execute("INSERT INTO {} VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)".format(tablename),
                           (self.last_serial[x], args[0], args[1], args[2], args[3], args[4], args[5], args[6],
                            args[7]))
        except:
            raise
            return False

        self.last_serial[x] += 1
        self.conn.commit()
        return self.last_serial[x] - 1

    def show_one(self, table, what, where):
        self.c.execute("SELECT {} FROM {} WHERE {}".format(what, table, where))
        try:
            return self.c.fetchone()[0]
        except TypeError:
            return -1

    def show_one_fully(self, table, what, where):
        self.c.execute("SELECT {} FROM {} WHERE {}".format(what, table, where))
        try:
            return self.c.fetchone()
        except TypeError:
            return -1

    def show_all(self, table, what):
        self.c.execute("SELECT {} FROM {}".format(what, table))
        return self.c.fetchall()

    def update_by(self, table, what, where):
        self.c.execute("UPDATE {} SET {} WHERE {}".format(table, what, where))
        self.conn.commit()
        return 1

    def delete_items(self, table, where):
        try:
            self.c.execute("DELETE FROM {} WHERE {}".format(table, where))
            self.conn.commit()
            return 1
        except:
            return -1

    def drop_table(self):
        self.c.execute("DROP TABLE users")
        self.conn.commit()

    def close(self):
        with open('C:\Python_Projects\Cocoa - ya project\CocoaData\serials.txt', 'w') as file:
            file.write(str(self.last_serial[0]) + "." + str(self.last_serial[1]) + "." + str(self.last_serial[2]))

        self.conn.close()


if __name__ == '__main__':
    # THE example of how to add an item.
    # add_item(tablename, name, desc, (renterSn, avail), (details), (coords: x, y), ((takenby, timespan)), (rating, count), imgsloc)
    '''print(db.add_item('apartments', 'Testhouse', 'this house is beutiful and i like it very much',
                      '(1002,"1203218123 - 1803218123")',
                      '(True, False, True, True, 5, 3, 1 ,2)', '(45.3232,33.5422)',
                      '((10482, "12832-82721"), ((48, "47-8")))',
                      '(4.5,19)', 'C:/Python_Projects/Cocoa - ya project/CocoaData'))'''

    '''print(db.add_item('users', 'Noam', 'Schuldiner',
                      'nschuldi', 'noamschuldiner@gmail.com', '123456789',
                      '(1009, 1010)', '((1011, "81328 - 127321"),(1012, ":)"))', 89975))'''

    db = DataBase()
    # db.drop_table()


    '''db.update_by('users', 'rentingApartments="()"', 'serialNumber=1001')
    db.update_by('users', 'rentingApartments="()"', 'serialNumber=1002')
    db.update_by('users', 'myApartments="()"', 'serialNumber=1001')
    db.update_by('users', 'myApartments="()"', 'serialNumber=1002')'''
    # db.update_by('users', 'myApartments="()"', 'serialNumber=1001')
    # taken = eval(db.show_one('apartments', 'taken', 'serialNumber={}'.format(1007)))
    # print(taken)
    # print(db.delete_items('apartments', 'serialNumber="1009"'))
    # print(db.show_all('apartments', "serialNumber"))
    # print(db.delete_items('apartments', 'serialNumber=1016'))
    # print(db.show_one_fully('apartments', '*', 'serialNumber=1007'))
    '''x = "this house is beautiful, it has the view of the weizmann institute, it is hadicap friendly and pet " \
        "friendly.\n It has an esspresso machine and a dishwasher.\n towels are included "
    print(db.update_by('apartments', 'description="{}"'.format(x), 'serialNumber=1007'))'''
    # print(db.update_by('apartments', 'taken="((1001, (\'18.05.2022\', \'21.05.2022\')),)"', 'serialNumber=1005'))

    print(db.show_all('users', '*'))
    print(db.show_all('apartments', '*'))

    print(db.show_one('apartments', 'rating', "name='asd'"))
    # photopath = db.show_one('apartments', 'imglocation', 'serialNumber=?')
    # print(photopath)
    # DELETE query
    # print(db.delete_items('apartments', 'name="Testhouse"'))

    db.close()

    '''conn = sqlite3.connect('database.db')
    c = conn.cursor()
    
    c.execute("""CREATE TABLE apartments (
                    serialNumber integer,
                    name text,
                    description text,
                    availability text,
                    details text,
                    coords text,
                    taken text,
                    rating text,
                    imglocation text
                    )""")
    
    conn.commit()
    conn.close()
    '''

    '''conn = sqlite3.connect('database.db')
    c = conn.cursor()

    c.execute("""CREATE TABLE users (
                    serialNumber integer,
                    firstName text,
                    lastName text,
                    userName text,
                    email text,
                    password text,
                    myApartments text,
                    rentingApartments text,
                    balance integer
                    )""")

    conn.commit()
    conn.close()'''
