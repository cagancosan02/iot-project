import sqlite3
from sqlite3 import Error
import os

"""
Narazie kod do bazy danych znajduje się tutaj
Potem pewnie będzie trzeba zintegrować ją do kodu w GNURadio
bo wydaje się że parser pythonowy nie obsługuje tam za dobrze osobnych plików
Ale można również odpalić (poprzez importy) kod z osobnego pliku poprzez odpalenie kodu CLI
"""

TABLE_STRUCTURE = """
    CREATE TABLE IF NOT EXISTS signals (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        bits TEXT NOT NULL
    );
"""

class DBHandler:
    def __init__(self, debug=None):
        self.connection = None
        self.debug = debug

    def __get_current_db_path(self, db_name):
        return os.path.join(os.getcwd(), db_name)

    def __db_exists(self, db_name):
        return os.path.exists(self.__get_current_db_path(db_name))
    
    def __debug_printer(self, message):
        if self.debug:
            print(message)
        else:
            print("", end="")

    def create_db(self, db_name):
        if not self.__db_exists(db_name):
            try:
                self.create_connection(db_name)
                cursor = self.connection.cursor()
                cursor.execute(TABLE_STRUCTURE)
                self.connection.commit()
                self.__debug_printer("Tabela została utworzona")
            except Error as e:
                self.__debug_printer(f"Błąd {e}")
        else:
            self.__debug_printer("Baza danych już istnieje")
            self.connection = sqlite3.connect(self.__get_current_db_path(db_name))

    def create_connection(self, db_name):
        try:
            self.connection = sqlite3.connect(db_name)
            self.__debug_printer(f"Połączenie z bazą danych {db_name} udane")
        except Error as e:
            self.__debug_printer(f"Błąd {e}")

    def add_data(self, value):
        query = "INSERT INTO signals (bits) VALUES (?);"
        data = (value, )
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, data)
            self.connection.commit()
        except Error as e:
            self.__debug_printer(f"Błąd {e}")

    def read_data_all(self):
        query = "SELECT * FROM signals;"
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
            rows = cursor.fetchall()
            self.__debug_printer("Odczytane dane:")
            for row in rows:
                self.__debug_printer(row)
            return rows
        except Error as e:
            self.__debug_printer(f"Błąd {e}")

    def read_data_single_row(self, index):
        query = "SELECT * FROM signals WHERE id = ?;"
        data = (index, )
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, data)
            rows = cursor.fetchall()
            return rows
        except Error as e:
            self.__debug_printer(f"Błąd {e}")



db_name = "db.db"

newDBHandler = DBHandler(debug=True)
newDBHandler.create_db(db_name)
newDBHandler.add_data("1000101")
newDBHandler.read_data_all()
newDBHandler.read_data_single_row(1)