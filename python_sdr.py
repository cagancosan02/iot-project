#!/usr/bin/env python

from gnuradio import gr
from gnuradio import blocks
from gnuradio import analog
from gnuradio import osmosdr

import numpy as np
from symbol import comparison

# todo global array to remember signals
# todo naming signals


"""
struktura
    [
        {
            "numer_of_signal": 1,
            "signal": <x>,
            "number of occurence": <int>,
            <maybe additional data>
        },
        {
        
        },
        {
        
        },
    ]
"""
GLOBAL_SIGNALS_ARRAY = []


def global_signal_array_iterator(signal):
    """
    Argument: signal and global array of remembered signals
    Return:
        Position if exists
        None if does not exist
    """
    for one in GLOBAL_SIGNALS_ARRAY:
        if np.array_equal(signal, one["signal"]):
            return GLOBAL_SIGNALS_ARRAY.index(one)
    return None

def check_if_bitstream_exists(signal):
    # Sprawdź, czy sygnały mają tę samą długość


    # Porównaj sygnały
    # a może jaka entropia? trzeba zobaczyć jak wyjdzie w praniu. 
    # No ale przy CRC albo zmiennych sygnałach no to kurcze będzie trzeba o to zadbać

    # zweryfikować co powinno zostać zwrazane oraz przenieś print z returna do ciała
    is_in_array = global_signal_array_iterator(signal)
    # adding new signal
    if is_in_array == None:
        new = {
            "number_of_signal": len(GLOBAL_SIGNALS_ARRAY) + 1,
            "signal": signal,
            "number_of_occurence": 1
        }
        GLOBAL_SIGNALS_ARRAY.append(new)
        return "Dodano nowy sygnał"
    
    # aktualizacja obecnego
    GLOBAL_SIGNALS_ARRAY[is_in_array]["number_of_occurence"] += 1


    return "Zaaktualizowano obecny sygnał"

class SignalCaptureWithBits(gr.top_block):
    def __init__(self, center_freq, sample_rate, output_file_prefix):
        gr.top_block.__init__(self)

        # Ustawienia odbiornika SDR
        self.source = osmosdr.source(0)  # Numer urządzenia SDR
        self.source.set_sample_rate(sample_rate) # Próbkowanie
        self.source.set_center_freq(center_freq) # Częstotliowść centralna odbiornika
        self.source.set_freq_corr(0, 0) # Korekcja częstotliwości
        self.source.set_gain(20) # Wzmocnienie odbiornika

        # Demodulacja amplitudy
        self.amplitude_demod = analog.am_demod_cf()

        # Demodulatory
        self.demodulators = [digital.dbpsk_demod(), digital.qpsk_demod(), digital.constellation_decoder_cb()]
        self.current_demodulator = 0
        self.demod = self.demodulators[self.current_demodulator]

        # Kwadratura
        self.quadrature_demod = analog.quadrature_demod_cf()

        # Próbkowanie
        self.sampler = blocks.keep_one_in_n(gr.sizeof_float, int(sample_rate / 100e3))

        # Kwantyzacja
        self.quantizer = blocks.float_to_char()

        # Zapis do pliku RAW
        self.file_sink = blocks.file_sink(gr.sizeof_gr_complex, output_file_prefix + ".raw", False)
        self.file_sink.set_unbuffered(True)

        # odbiór do tablicy numpy
        self.array_sink = blocks.vector_sink_char()

        # Połączenie bloków
        self.connect((self.source, 0), (self.amplitude_demod, 0))
        self.connect((self.amplitude_demod, 0), (self.quadrature_demod, 0))
        self.connect((self.quadrature_demod, 0), (self.sampler, 0))
        self.connect((self.sampler, 0), (self.quantizer, 0))
        self.connect((self.quantizer, 0), (self.file_sink, 0))

        # Wątek do nasłuchiwania i wyświetlania
        self.message_queue = gr.msg_queue(1024)

        # Rozpoznawanie modulacji
        self.modulation_detector = digital.modulation_analysis_ss(256)
        self.msg_connect((self.modulation_detector, 'constellation'), self.detect_modulation)
    
    def detect_modulation(self, msg):
        modulation_type = msg.to_string()
        print(f"Detected modulation: {modulation_type}")

        # Wybierz demodulator w zależności od rozpoznanej modulacji
        if modulation_type == 'QPSK':
            self.current_demodulator = 1
        elif modulation_type == 'BPSK':
            self.current_demodulator = 0
        else:
            self.current_demodulator = 2

        # Zmień aktualny demodulator
        self.demod = self.demodulators[self.current_demodulator]
        self.disconnect_all()
        self.connect((self.source, 0), (self.demod, 0))
        self.connect((self.demod, 0), (self.audio_sink, 0))
        self.connect((self.demod, 0), (self.message_sink, 0))

if __name__ == '__main__':
    center_freq = 433e6  # Częstotliwość odbiornika 433 MHz
    sample_rate = 2e6   # Próbkowanie 2 MHz
    output_file_prefix = "captured_signal"

    try:
        while True:
            tb = SignalCaptureWithBits(center_freq, sample_rate, output_file_prefix)
            tb.start()
            tb.wait()

            captured_signal_array = np.array(tb.array_sink.data())
            print("Dane w postaci numpy")
            print(captured_signal_array)

            comparison_signal_array = check_if_bitstream_exists(captured_signal_array)
            print(comparison_signal_array)

    except KeyboardInterrupt:
        print("Przechwycono sygnał, zaraz program zostanie zamknięty")
    finally:
        print("Zamykanie programu")
