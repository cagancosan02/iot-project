"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import sys
import json
import sqlite3
from sqlite3 import Error
import os


data_set = np.array([])
start = int(0)
stop = int(0)
size = int(0)
state = int(1)
keep_track_flag = int(0)
old_message = []
number_of_bits = 25 # TODO - ustawić to bardziej w dynamiczny sposob

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
        self.__debug_printer("Ścieżka do bazy to: " + os.path.join(os.getcwd(), db_name))
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

    def delete_rows_table(self, table_name):
        query = "DELETE FROM " + table_name
        try:
            cursor = self.connection.cursor()
            cursor.execute(query)
        except Error as e:
            self.__debug_printer(f"Błąd {e}")


class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""

    def __init__(self, preamble_bits=1, edge_offset=1, dead_space=1):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='OOK Custom Decoder',   # will show up in GRC
            in_sig=[np.float32],
            out_sig=None
        )
        # if an attribute with the same name as a parameter is found,11
        # a callback is registered (properties work, too).
        self.preamble_bits = preamble_bits
        self.edge_offset = edge_offset
        self.dead_space = dead_space
        self.db_name = "ook_demod_db.db"

        self.DBHandler = DBHandler(debug=True)
        self.DBHandler.create_db(self.db_name)
        

    @staticmethod
    def return_distances(signal):

        last_rising_edge = None
        distances = []

        for i in range(1, len(signal)):
            # Check if the current value is 1 and the previous value is 0 (rising edge)
            if signal[i] == 1 and signal[i-1] == 0:

                # Calculate and annotate the distance from the last rising edge, if it exists
                if last_rising_edge is not None:
                    distance = i - last_rising_edge
                    distances.append(distance)
                last_rising_edge = i
        return distances
    
    @staticmethod
    def group_distances(distances, tolerance=0.1):
        groups = {}
        for d in distances:
            placed = False
            for center in groups:
                if (1 - tolerance) * center <= d <= (1 + tolerance) * center:
                    groups[center].append(d)
                    placed = True
                    break
            if not placed:
                groups[d] = [d]
        return groups

    @staticmethod
    def find_average_of_most_frequent_group(distances, tolerance=0.15):
        # Group the distances
        groups = blk.group_distances(distances, tolerance)

        # Find the most frequent group
        most_frequent_group = max(groups, key=lambda k: len(groups[k]))

        # Calculate the average of the most frequent group
        average_of_group = sum(groups[most_frequent_group]) / len(groups[most_frequent_group])

        return average_of_group
    
    @staticmethod
    def return_distances_and_count_highs(signal, artificial_bin_width):

        last_rising_edge = None
        distances_and_counts = []

        for i in range(1, len(signal)):
            if signal[i] == 1 and signal[i-1] == 0:
                if last_rising_edge is not None:
                    distance = i - last_rising_edge
                    high_states_count = sum(signal[last_rising_edge:i])
                    distances_and_counts.append((distance, high_states_count))
                    
                last_rising_edge = i

        # Obliczanie odległości i ilości jedynek dla sztucznego binu
        if last_rising_edge is not None:
            artificial_distance = artificial_bin_width
            # Liczenie jedynek w sztucznym binie
            end_of_artificial_bin = last_rising_edge + artificial_distance
            high_states_count = sum(signal[last_rising_edge:end_of_artificial_bin])
            distances_and_counts.append((artificial_distance, high_states_count))

        return distances_and_counts

    @staticmethod
    def filter_tuples_within_range(tuples_list, center_value, percentage=10):
        # Obliczanie zakresu
        range_min = center_value - (center_value * percentage / 100)
        range_max = center_value + (center_value * percentage / 100)

        # Filtrowanie tupli
        filtered_list = [t for t in tuples_list if range_min <= t[0] <= range_max]
        return filtered_list

    @staticmethod
    def decode(tuples_list):
        results = []
        for first, second in tuples_list:
            if first != 0:  # Aby uniknąć dzielenia przez zero
                ratio = second / first
                flag = 1 if ratio > 0.5 else 0
            else:
                flag = 0  # W przypadku gdy pierwszy element jest równy 0
            results.append(flag)
        return results

    @staticmethod
    def get_message_from_dataset(data_set):
        
        distances = blk.return_distances(data_set)
        average_of_most_frequent = blk.find_average_of_most_frequent_group(distances)
        distances_and_counts = blk.return_distances_and_count_highs(data_set, int(average_of_most_frequent))
        filtered_list = blk.filter_tuples_within_range(distances_and_counts, int(average_of_most_frequent))
        message = blk.decode(filtered_list)
        
        return message

    def work(self, input_items, output_items):
        """example: multiply with constant"""
        in0 = np.array(input_items[0])
        
        global state
        global data_set
        global start
        global stop
        global size
        global keep_track_flag
        global old_message
        
        if state == 1:
            #Looking for a blank space before the message.
            if np.any(in0 > 0.5):
                #Reset size and start over. 
                size = 0
            else:
                size = size + len(in0)
                #Once enough blank space has gone by start looking for the message.
                if size > self.dead_space: #This value is imperically found. 
                    size = 0
                    state = 2
        
        #look for a leading edge
        if state == 2:
            #Calculate sample 1 minus sample 2. This looks for any edge positive or negative. 
            leading_edge = np.abs(in0[:-1] - in0[1:]) > .5
            #Check if any edge is found. 
            if np.any(leading_edge == True):
                #When edge is found start looking for the trailing edge
                state = 3
                #Store the data because it will span several frames.
                data_set = np.append(data_set, in0)
                
            
            
        #look for a trailing edge (looking for silence)
        if state == 3:
            """
            #Keep storing the data while looking for the trailing edge. 
            data_set = np.append( data_set, in0)
            #Calculate sample 1 minus sample 2. This looks for any edge positive or negative.
            trailing_edge = np.abs(in0[:-1] - in0[1:]) > 0.5
            #Check if any go positive. 
            if np.any(trailing_edge == True):
                size = 0
            else:
                size = size + len(in0)
                #if a long enough stretch is found after the message the it ended. 
                if size > self.dead_space: #This value is imperically found.
                    size = 0
                    state = 4
                    """
            # Keep storing the data while looking for the trailing edge.
            data_set = np.append(data_set, in0)
            # Calculate sample 1 minus sample 2. This looks for any edge positive or negative.
            trailing_edge = np.abs(in0[:-1] - in0[1:]) > 0.5
            # Check if any go positive.
            if np.any(trailing_edge == True):
                size = 0
            else:
                size = size + len(in0)
                # if a long enough stretch is found after the message then it ended.
                if size > self.dead_space:  # This value is empirically found.
                    size = 0
                    state = 4
                    # Convert numpy array to list for JSON serialization
                    data_list = data_set.tolist()
                    # Write data_list to a JSON file
                    with open('data_set_drogi_pilot.json', 'w') as file:
                        json.dump(data_list, file)
            
        #analyze the data
        if state == 4:
            
            data = blk.get_message_from_dataset(data_set)
            print(data)
            self.DBHandler.create_connection(self.db_name)
            self.DBHandler.add_data("".join(str(one) for one in data))
            
            #Reset all the variable for another go around
            state = 1
            size = 0
            start = 0
            stop = 0
            data_set = np.array([])
        
        
        return len(input_items[0])