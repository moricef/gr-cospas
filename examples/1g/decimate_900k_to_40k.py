#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Décimation 900 kHz → 40 kHz pour le décodeur COSPAS-SARSAT
"""

from gnuradio import gr, blocks, filter
from gnuradio.filter import firdes
from gnuradio import eng_notation
import sys

class decimate_900k_to_40k(gr.top_block):
    def __init__(self, input_file, output_file):
        gr.top_block.__init__(self, "Décimation 900k → 40k")

        print("="*70)
        print("DÉCIMATION 900 kHz → 40 kHz")
        print("="*70)
        print(f"Input:  {input_file}")
        print(f"Output: {output_file}")
        print(f"Facteur: 22.5 (900k/40k)")
        print("="*70)

        # Source
        self.file_source = blocks.file_source(
            gr.sizeof_gr_complex,
            input_file,
            False
        )

        # Décimation par 22.5 = décimer par 45/2
        # Étape 1: décimer par 9 (900k → 100k)
        self.decimator_1 = filter.fir_filter_ccf(
            9,
            firdes.low_pass(1, 900000, 40000, 10000)
        )

        # Étape 2: décimer par 2.5 = interpoler par 2, décimer par 5 (100k → 40k)
        self.rational_resampler = filter.rational_resampler_ccc(
            interpolation=2,
            decimation=5,
            taps=firdes.low_pass(1, 200000, 18000, 4000),
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
        self.connect((self.decimator_1, 0), (self.rational_resampler, 0))
        self.connect((self.rational_resampler, 0), (self.file_sink, 0))


def main():
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <input_900k.iq> <output_40k.iq>")
        sys.exit(1)

    input_file = sys.argv[1]
    output_file = sys.argv[2]

    tb = decimate_900k_to_40k(input_file, output_file)

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
