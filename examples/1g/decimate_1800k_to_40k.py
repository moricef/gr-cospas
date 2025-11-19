#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Décimation 1.8 MHz → 40 kHz pour le décodeur COSPAS-SARSAT
"""

from gnuradio import gr, blocks, filter
from gnuradio.filter import firdes
import sys

class decimate_1800k_to_40k(gr.top_block):
    def __init__(self, input_file, output_file):
        gr.top_block.__init__(self, "Décimation 1.8M → 40k")

        print("="*70)
        print("DÉCIMATION 1.8 MHz → 40 kHz")
        print("="*70)
        print(f"Input:  {input_file}")
        print(f"Output: {output_file}")
        print(f"Facteur: 45 (1800k/40k)")
        print("="*70)

        # Source
        self.file_source = blocks.file_source(
            gr.sizeof_gr_complex,
            input_file,
            False
        )

        # Décimation par 45 = 9 × 5
        # Étape 1: décimer par 9 (1.8M → 200k)
        self.decimator_1 = filter.fir_filter_ccf(
            9,
            firdes.low_pass(1, 1800000, 80000, 20000)
        )

        # Étape 2: décimer par 5 (200k → 40k)
        self.decimator_2 = filter.fir_filter_ccf(
            5,
            firdes.low_pass(1, 200000, 18000, 4000)
        )

        # Sink
        self.file_sink = blocks.file_sink(
            gr.sizeof_gr_complex,
            output_file,
            False
        )
        self.file_sink.set_unbuffered(False)

        # Connexions
        self.connect((self.file_source, 0), (self.decimator_1, 0))
        self.connect((self.decimator_1, 0), (self.decimator_2, 0))
        self.connect((self.decimator_2, 0), (self.file_sink, 0))


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input_1800k.raw> <output_40k.iq>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    tb = decimate_1800k_to_40k(input_file, output_file)

    try:
        print("\nDémarrage de la décimation...")
        tb.run()
        print("\n✅ Décimation terminée!")
        print(f"Fichier créé: {output_file}")
    except KeyboardInterrupt:
        print("\n\nInterrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
