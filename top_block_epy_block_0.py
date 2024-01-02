"""
Embedded Python Blocks:

Each time this file is saved, GRC will instantiate the first class it finds
to get ports and parameters of your block. The arguments to __init__  will
be the parameters. All of them are required to have default values!
"""
"""
import numpy as np
from gnuradio import gr


class blk(gr.sync_block):  # other base classes are basic_block, decim_block, interp_block
    #Embedded Python Block example - a simple multiply const

    def __init__(self, example_param=1.0):  # only default arguments here
        #arguments to this function show up as parameters in GRC
        gr.sync_block.__init__(
            self,
            name='Embedded Python Block',   # will show up in GRC
            in_sig=[np.complex64],
            out_sig=[np.complex64]
        )
        # if an attribute with the same name as a parameter is found,
        # a callback is registered (properties work, too).
        self.example_param = example_param

    def work(self, input_items, output_items):
        #example: multiply with constant
        output_items[0][:] = input_items[0] * self.example_param
        return len(output_items[0])
        """

from gnuradio import gr
import numpy as np

class MyBlock(gr.basic_block):
    def __init__(self):
        gr.basic_block.__init__(self,
            name="LoggerHelper",
            in_sig=[np.float32],
            out_sig=[])

    def general_work(self, input_items, output_items):
        # Przechwytywanie danych wejściowych (bajtów)
        #input_data = self.consume(0, input_items[0], len(input_items[0]))

        # Wypisanie danych na standardowym wyjściu
        print("Received data:", input_items)

        # Przekazywanie danych dalej
        #self.produce(0, input_data)

        # Zwracanie ilości przetworzonych elementów (w tym przypadku bajtów)
        return 1

