"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""

import numpy as np
from gnuradio import gr
import sys

data_set = np.array([])
start = int(0)
stop = int(0)
size = int(0)
state = int(1)
keep_track_flag = int(0)
old_message = []

class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    """Embedded Python Block example - a simple multiply const"""
    

    def __init__(self, preamble_bits=1, edge_offset=1, dead_space=1):  # only default arguments here
        """arguments to this function show up as parameters in GRC"""
        gr.sync_block.__init__(
            self,
            name='Custom Data Decoder',   # will show up in GRC
            in_sig=[np.float32],
            out_sig=None
        )
        # if an attribute with the same name as a parameter is found,
        # a callback is registered (properties work, too).
        self.preamble_bits = preamble_bits
        self.edge_offset = edge_offset
        self.dead_space = dead_space

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
                
            
            
        #look for a trailing edge
        if state == 3:
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
            
            
        #analyze the data
        if state == 4:
            
            
            #file = open('C:\logs\data_set.txt','a')
            #intermediate = data_set.astype(int)
            #intermediate2 = ",\r".join(intermediate.astype(str))
            #file.write(intermediate2)
            #file.write("\r,space\r,")
            #file.close()
            
            
            #If the data set is greater than 70000 the it is the first packet
            #The first packet has a wake up signal of 72 bits and then the message.
            if len(data_set) > 30000:
                #Find the edges
                edges = np.abs(data_set[:-1] - data_set[1:]) > 0.5
                #Grab the locations of the edges.
                edge_locations = np.where(edges)[0]
                #Find the difference between the edges.
                edge_difference = edge_locations[1:] - edge_locations[:-1]
                #debug
                #print 'data length', len(data_set)
                #print 'edge diferences', edge_difference[:20]
                #Grab the edge difference into the packet preamble.
                try:
                    #Sometime this picks up garbadge and the try helps to keep it from crashing
                    average = edge_difference[self.preamble_bits * 2]
                    average_found = True
                except:
                    average_found = False
                #Make sure that there are enough edges to do something usefull. 
                if average_found and len(edge_difference) > (self.preamble_bits * 2):
                    #Trim down how big the edge difference is.
                    edge_difference = edge_difference[:self.preamble_bits * 2]
                    #print 'average', average
                    #Filter edge_difference to eliminate everything greater than 110% and less than 90%
                    #This should eliminate everything at the begining that is not the preable. 
                    looking_for_start_edge_positive = edge_difference < (average * 1.1)
                    looking_for_start_edge_negative = edge_difference > (average * 0.9)
                    #Logical and together the two to get something that eliminates both. 
                    looking_for_start_edge = np.logical_and(looking_for_start_edge_positive, looking_for_start_edge_negative)
                    #print looking_for_start_edge[:15]
                    #Grab all the locations that are true. 
                    check_if_consecutive = np.where(looking_for_start_edge)[0]
                    #print 'check if consecutive', check_if_consecutive
                    #print 'len of check if consecutive', len( check_if_consecutive)
                    #Create an array that should be the same if it is consecutive. 
                    consecutive_array = np.arange(check_if_consecutive[0], check_if_consecutive[-1] + 1)
                    #print 'consecutive array', consecutive_array
                    #Ther arrays may be different sizes and causing the check to throw and exception.
                    
                    
                    #Set compare to false ahead of time.
                    compare = False
                    for i in range(3):
                        #If they are different sizes then they can't be consecuitve.
                        if len( check_if_consecutive) == len( consecutive_array):
                            #Compare together the consecutive array and the check if consecutive. 
                            #If the arrays are not consecutive the check will fail. 
                            if np.all(np.equal(check_if_consecutive, consecutive_array)):
                                compare = True
                                #If the arrays are consecutive leave the for loop.
                                break
                        #Sometimes just one stray edge is the correct size.
                        #Try trimming the first edge and check for consecutive.
                        #Because of the for loop this is done up to 3 times. 
                        #If the array is not consecutive by then, it won't be. 
                        check_if_consecutive = check_if_consecutive[1:]
                        #Create an array that should be the same if it is consecutive. 
                        consecutive_array = np.arange(check_if_consecutive[0], check_if_consecutive[-1] + 1)
                        
                    if compare:
                        #Average together the preamble to get what the clock speed is. 
                        period = int(np.average(edge_difference[check_if_consecutive[0]: check_if_consecutive[-1] + 1]))
                        #debug
                        #print 'check_if_consecutive', check_if_consecutive[0]
                        #print 'edge locations', edge_locations[:10]
                        #print 'the preable was consecustive', edge_locations[check_if_consecutive[0]]
                        #This is where the leading edge of the preable is. 
                        #It is offset by one to properly align the manchester coding.
                        start = edge_locations[check_if_consecutive[0]]
                        #Trim edge locations
                        edge_locations = edge_locations[check_if_consecutive[0]:]
                        
                        
                        #Now create a sampling array that alignes with the data. 
                        ticks_positive = np.arange(start - self.edge_offset, (start - self.edge_offset) + (period * 88), period, dtype=np.int)
                        ticks_negative = np.arange(start + self.edge_offset, (start - self.edge_offset) + (period * 88), period, dtype=np.int)
                        
                        # To keep things from crashing
                        if ticks_negative[-1] < len(data_set):
                            #The data seems to have some gitter or drift. 
                            #Make an array of only desired edges.
                            optimised_edges = np.array([edge_locations[0]])
                            for g in range(1,len(edge_locations)):
                                if((edge_locations[g]-optimised_edges[-1])<(period*1.2))and((edge_locations[g]-optimised_edges[-1])>(period*0.8)):
                                    optimised_edges = np.append(optimised_edges,edge_locations[g])
                            #Now that we have the edges we can optimise the sampling locations.
                            for h in range(len(optimised_edges)):
                                if ticks_positive[h] >= optimised_edges[h]:
                                    adjustment = ticks_positive[h] - optimised_edges[h] + self.edge_offset
                                    ticks_negative[h:] -= adjustment
                                    ticks_positive[h:] -= adjustment
                                    
                                if ticks_negative[h] <= optimised_edges[h]:
                                    adjustment = optimised_edges[h] - ticks_negative[h] + self.edge_offset
                                    ticks_negative[h:] += adjustment
                                    ticks_positive[h:] += adjustment
                            
                            # Convert the data to high and low 
                            converted_data = data_set > 0.5
                            #Reshape the data 
                            positive_packet = converted_data[ticks_positive].reshape(88)
                            neagtive_packet = converted_data[ticks_negative].reshape(88)
                            
                            # if keep_track_flag == 0:
                                # file = open('C:\logs\data_set.txt','a')
                                # intermediate = data_set.astype(int)
                                # intermediate2 = ",\r".join(intermediate.astype(str))
                                # file.write(intermediate2)
                                # file.write(",\r space,\r")
                                # intermediate =  ",\r".join(ticks_positive.astype(str))
                                # file.write(intermediate)
                                # file.write(",\r space,\r")
                                # intermediate =  ",\r".join(ticks_negative.astype(str))
                                # file.write(intermediate)
                                # file.write(",\r space,\r")
                                # file.close()
                                # keep_track_flag = 1
                            
                            
                            
                            if np.all(np.logical_xor(positive_packet,neagtive_packet)):
                                #Without knowing what the information is supposed to look like
                                #it is a 50/50 chance as to using the positive packet or negative packet.
                                #The difference being that one gives you IEEE manchester coding
                                #and the other gives you Thomas coding. 
                                packet = positive_packet.reshape(11,8)
                                message = []
                                message2 = np.zeros((11,), dtype=int)
                                for j in range(11):
                                    decimal = sum([packet[j,7-i]*2**i for i in range(len(packet[j,]))])
                                    message2[j] = decimal
                                    message.append(str("{0:#0{1}x}".format(decimal,4)))
                                
                                
                                if old_message != message:
                                    old_message = message
                                    print(message[2:])
                                    message2[8] = message2[8] - 27
                                    if message2[8] < 0:
                                        message2[8] = 256 + message2[8]
                                        
                                    message2[7] += 1
                                    if message2[7] > 255:
                                        message2[7] = 0
                                        message2[6] += 1
                                        if message2[5] > 255:
                                            message2[5] = 0
                                            
                                    message2[10] = np.sum(message2[2:10])
                                    while message2[10] > 255:
                                        message2[10] -= 256
                                    message3 = []
                                    for j in range(11):
                                        message3.append(str("{0:#0{1}x}".format(message2[j],4)))
                                        
                                    print("The next message is")
                                    print(message3[2:])
                                    
                                    # concatinated_message = []
                                    # for j in range(11):
                                        # decimal = sum([packet[j,7-i]*2**i for i in range(len(packet[j,]))])
                                        # concatinated_message.append(str("{0:02x}".format(decimal,2)))
                                    
                                    
                                    # file = open('C:\logs\data_set.txt','a')
                                    # intermediate = "".join(concatinated_message)
                                    # file.write(intermediate)
                                    # file.write(" ")
                                    # file.close()
                                    
                            else:
                                print('The xor did not resolve.')
                        else:
                            print('index out during reshape', len( data_set), ticks_negative[-1])
                         
                    else:
                        print('the preable was not consecustive', check_if_consecutive, len( check_if_consecutive))
                else:
                    print('average failed')
            else:
                print('the data set was too short')
            #Reset all the variable for another go around
            state = 1
            size = 0
            start = 0
            stop = 0
            data_set = np.array([])
        
        
        return len(input_items[0])