#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Décodage COSPAS-SARSAT depuis rtl_sdr avec ré-échantillonnage
Usage: rtl_sdr -f 406.028M -s 250000 -g 40 - | ./decode_rtl_sdr.py 250000
"""

from gnuradio import gr, blocks, filter
from gnuradio.cospas import cospas_sarsat_decoder
from gnuradio.filter import firdes
import sys

class decode_rtl_sdr(gr.top_block):
    def __init__(self, input_rate=250000, output_rate=40000):
        gr.top_block.__init__(self, "Décodeur RTL-SDR COSPAS-SARSAT")

        print("="*70, file=sys.stderr)
        print("DÉCODAGE RTL-SDR → COSPAS-SARSAT", file=sys.stderr)
        print("="*70, file=sys.stderr)
        print(f"Sample rate entrée: {input_rate} Hz", file=sys.stderr)
        print(f"Sample rate sortie: {output_rate} Hz", file=sys.stderr)
        print(f"Ratio décimation: {input_rate/output_rate}", file=sys.stderr)
        print(f"Échantillons/bit (400 bps): {output_rate/400}", file=sys.stderr)
        print("="*70, file=sys.stderr)
        print(file=sys.stderr)

        # Source: stdin (rtl_sdr pipe)
        self.stdin_source = blocks.file_descriptor_source(
            gr.sizeof_gr_complex,
            0,  # stdin
            False
        )

        # Ré-échantillonnage si nécessaire
        if input_rate != output_rate:
            decimation = int(input_rate / output_rate)

            if decimation * output_rate != input_rate:
                # Ré-échantillonnage rationnel
                interpolation = output_rate
                decimation_frac = input_rate

                # Simplification
                from math import gcd
                g = gcd(interpolation, decimation_frac)
                interpolation //= g
                decimation_frac //= g

                print(f"⚙️  Ré-échantillonnage rationnel: {interpolation}/{decimation_frac}", file=sys.stderr)

                # Filtre de transition
                taps = firdes.low_pass(
                    interpolation,  # gain
                    interpolation * input_rate,  # sample rate
                    output_rate / 2 * 0.8,  # cutoff
                    output_rate / 2 * 0.2  # transition
                )

                self.resampler = filter.rational_resampler_ccc(
                    interpolation=interpolation,
                    decimation=decimation_frac,
                    taps=taps
                )

                self.connect(self.stdin_source, self.resampler)
                source_for_decoder = self.resampler
            else:
                # Décimation simple
                print(f"⚙️  Décimation simple: /{decimation}", file=sys.stderr)

                taps = firdes.low_pass(
                    1.0,  # gain
                    input_rate,  # sample rate
                    output_rate / 2 * 0.8,  # cutoff
                    output_rate / 2 * 0.2  # transition
                )

                self.decimator = filter.fir_filter_ccf(decimation, taps)

                self.connect(self.stdin_source, self.decimator)
                source_for_decoder = self.decimator
        else:
            source_for_decoder = self.stdin_source

        # Décodeur COSPAS-SARSAT
        self.decoder = cospas_sarsat_decoder(
            sample_rate=output_rate,
            debug_mode=True
        )

        # Sink pour récupérer les données
        self.vector_sink = blocks.vector_sink_b()

        # Connexions finales
        self.connect(source_for_decoder, self.decoder)
        self.connect(self.decoder, self.vector_sink)


def main():
    if len(sys.argv) < 2:
        print("Usage: rtl_sdr -f 406.028M -s 250000 -g 40 - | ./decode_rtl_sdr.py 250000", file=sys.stderr)
        print("       (ou remplacer 250000 par le sample rate utilisé)", file=sys.stderr)
        return 1

    input_rate = int(sys.argv[1])
    output_rate = 40000  # 100 samples/bit pour 400 bps

    print(f"⏳ Démarrage du décodeur...", file=sys.stderr)

    tb = decode_rtl_sdr(input_rate, output_rate)

    try:
        tb.run()

        # Récupération des données
        data = tb.vector_sink.data()

        if len(data) > 0:
            print(f"\n✅ Données décodées: {len(data)} octets", file=sys.stderr)
            print("\nDonnées (hex):", file=sys.stderr)
            hex_str = ''.join(f'{b:02X}' for b in data)
            print(f"  {hex_str}", file=sys.stderr)

            # Sortie pour scan406.pl
            print(hex_str)  # stdout pour parsing
        else:
            print("\n❌ Aucune donnée décodée", file=sys.stderr)

    except KeyboardInterrupt:
        print("\n⚠️  Interruption utilisateur", file=sys.stderr)
        tb.stop()
        tb.wait()
    except Exception as e:
        print(f"\n❌ Erreur: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc(file=sys.stderr)
        return 1

    return 0


if __name__ == '__main__':
    sys.exit(main())
