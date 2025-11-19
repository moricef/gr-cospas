#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Décodage COSPAS-SARSAT depuis stdin (pour rtl_sdr en direct)
Usage: rtl_sdr -f 406.028M -s 40000 -g 40 - | ./decode_iq_stdin.py
"""

from gnuradio import gr, blocks
from gnuradio.cospas import cospas_sarsat_decoder
import sys

class decode_iq_stdin(gr.top_block):
    def __init__(self, sample_rate=40000):
        gr.top_block.__init__(self, "Décodeur I/Q COSPAS-SARSAT depuis stdin")

        print("="*70)
        print("DÉCODAGE I/Q DEPUIS STDIN")
        print("="*70)
        print(f"Sample rate: {sample_rate} Hz")
        print(f"Échantillons/bit (400 bps): {sample_rate/400}")
        print("="*70)
        print()

        # Source: stdin (file descriptor 0)
        self.stdin_source = blocks.file_descriptor_source(
            gr.sizeof_gr_complex,
            0,  # stdin = fd 0
            False  # Ne pas répéter
        )

        # Décodeur COSPAS-SARSAT
        self.decoder = cospas_sarsat_decoder(
            sample_rate=sample_rate,
            debug_mode=True
        )

        # Sink pour récupérer les données
        self.vector_sink = blocks.vector_sink_b()

        # Connexions
        self.connect((self.stdin_source, 0), (self.decoder, 0))
        self.connect((self.decoder, 0), (self.vector_sink, 0))


def main():
    sample_rate = 40000

    if len(sys.argv) > 1:
        sample_rate = int(sys.argv[1])

    print(f"⚙️  Configuration: {sample_rate} Hz", file=sys.stderr)
    print(f"⏳ En attente de données I/Q sur stdin...", file=sys.stderr)

    tb = decode_iq_stdin(sample_rate)

    try:
        tb.run()

        # Récupération des données
        data = tb.vector_sink.data()

        if len(data) > 0:
            print(f"\n✅ Données décodées: {len(data)} octets")
            print("\nDonnées (hex):")
            hex_str = ''.join(f'{b:02X}' for b in data)
            print(f"  {hex_str}")
        else:
            print("\n❌ Aucune donnée décodée")

    except KeyboardInterrupt:
        print("\n⚠️  Interruption utilisateur", file=sys.stderr)
    except Exception as e:
        print(f"\n❌ Erreur: {e}", file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
