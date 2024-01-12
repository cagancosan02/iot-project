import sqlite3
from sqlite3 import Error
import os
import argparse
import sys
import time
from datetime import datetime, timedelta


class DBHandlerAnalyzer:
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

    def read_last_x_records(self, number):
        query = """
        SELECT * FROM signals ORDER BY id DESC LIMIT (?)
        """
        data = (number, )
        try:
            cursor = self.connection.cursor()
            cursor.execute(query, data)
            rows = cursor.fetchall()
            self.__debug_printer("Odczytane dane:")
            for row in rows:
                self.__debug_printer(row)
            return rows
        except Error as e:
            self.__debug_printer(f"Błąd {e}")
        
    def read_last_records_by_date(self, seconds):
        time_change = datetime.now() - timedelta(seconds=seconds)
        time_change = time_change.replace(microsecond=0)
        query = "SELECT * FROM signals WHERE date >= '" + str(time_change) + "'"
        print(query)
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

def analyze_data(data):
    pass

def main():
    parser = argparse.ArgumentParser(description="Sub-1GHz detection system")
    parser.add_argument('--db', '-d', type=str, help='Baza danych')
    parser.add_argument('--debug', type=bool, help="Przejdź w tryb debug")
    parser.add_argument('--records', '-n', type=int, help="Liczba rekordów do cyklicznego pobierania", default=500)
    parser.add_argument('--seconds', '-s', type=int, help="Ustaw czasowy przedział ostatnich rekordów, podany w sekundach", default=None)
    parser.add_argument('--interval', '-i', type=int, help="Interwał czasowy pobierania danych do analizy w sekundach", default=10)


    args = parser.parse_args()

    if not args.db:
        print("Musisz podać nazwę bazy danych, switch --db/-d")
        sys.exit(0)
    
    if args.debug:
        newDBHandler = DBHandlerAnalyzer(debug=True)
    else:
        newDBHandler = DBHandlerAnalyzer()

    newDBHandler.create_connection(args.db)

    if args.interval:
        interval = args.interval
    else:
        interval

    if args.seconds:
            while True:
                data = newDBHandler.read_last_records_by_date(args.seconds)
                analyze_data(data)
                print(data)
                time.sleep(interval)
    else:
            while True:
                data = newDBHandler.read_last_x_records(args.records)
                analyze_data(data)
                print(data)
                time.sleep(interval)




if __name__ == '__main__':
    main()