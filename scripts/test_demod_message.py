#!/usr/bin/env python3
"""Test démodulateur en mode message avec fichier IQ"""

import sys
import numpy as np
from gnuradio import gr, blocks
import pmt
from gnuradio import cospas

class test_demod_message(gr.top_block):
    def __init__(self, iq_file, sample_rate):
        gr.top_block.__init__(self)

        # Source fichier IQ
        self.file_source = blocks.file_source(gr.sizeof_gr_complex, iq_file, False)

        # Vector sink pour capturer les échantillons
        self.vector_sink = blocks.vector_sink_c()

        self.connect(self.file_source, self.vector_sink)

        # Démodulateur (mode message uniquement)
        self.demod = cospas.cospas_sarsat_demodulator(sample_rate, True)  # debug=True

def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <fichier.iq> <sample_rate>")
        sys.exit(1)

    iq_file = sys.argv[1]
    sample_rate = int(sys.argv[2])

    print(f"Lecture fichier: {iq_file}")
    print(f"Sample rate: {sample_rate} Hz")

    # Lire le fichier
    tb = test_demod_message(iq_file, sample_rate)
    tb.run()

    # Récupérer les échantillons
    samples = np.array(tb.vector_sink.data())
    print(f"Échantillons lus: {len(samples)}")

    # Créer un message PMT avec les échantillons
    samples_pmt = pmt.init_c32vector(len(samples), samples.tolist())
    msg = pmt.make_dict()
    msg = pmt.dict_add(msg, pmt.intern("samples"), samples_pmt)

    # Démarrer le flowgraph (juste le démodulateur)
    tb2 = gr.top_block()
    demod = cospas.cospas_sarsat_demodulator(sample_rate, True)

    print("Envoi au démodulateur...")
    tb2.start()

    import time
    time.sleep(0.01)

    # Envoyer via le port message
    demod_block = demod.to_basic_block()
    demod_block.post(pmt.intern("bursts"), msg)

    # Laisser le temps au message d'être traité
    time.sleep(0.5)

    tb2.stop()
    tb2.wait()

    print("Démodulation terminée")

if __name__ == '__main__':
    main()
