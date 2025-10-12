#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Décodage d'un fichier I/Q COSPAS-SARSAT
Démodulateur BPSK Biphase-L en bande de base
"""

from gnuradio import gr, blocks, filter
from gnuradio.cospas import cospas_sarsat_decoder
import sys

class decode_iq_file(gr.top_block):
    def __init__(self, iq_file, sample_rate=None):
        gr.top_block.__init__(self, "Décodeur I/Q COSPAS-SARSAT")

        # Paramètres
        self.target_rate = 6400  # Fréquence cible pour le décodeur COSPAS

        # Si le sample rate n'est pas spécifié, on va essayer plusieurs valeurs
        if sample_rate is None:
            # Les taux courants: 250 kHz, 1 MHz, 2.4 MHz, etc.
            sample_rate = 250000  # Par défaut

        self.input_rate = sample_rate

        print("="*70)
        print("DÉCODAGE FICHIER I/Q COSPAS-SARSAT")
        print("="*70)
        print(f"Fichier: {iq_file.split('/')[-1]}")
        print(f"Fréquence source: {self.input_rate} Hz")
        print(f"Fréquence cible: {self.target_rate} Hz")
        print(f"Facteur de décimation: {self.input_rate / self.target_rate:.1f}")
        print("="*70)
        print()

        ##################################################
        # Blocs
        ##################################################

        # Source: fichier I/Q (complex float32)
        self.file_source = blocks.file_source(
            gr.sizeof_gr_complex,
            iq_file,
            False  # repeat
        )

        # Filtre anti-repliement avant décimation
        # Filtre passe-bas à fc = target_rate/2 = 3200 Hz
        lpf_taps = filter.firdes.low_pass(
            1.0,                    # gain
            self.input_rate,        # sample rate
            self.target_rate / 2,   # cutoff (3200 Hz)
            500                     # transition width
        )
        self.low_pass_filter = filter.fir_filter_ccf(1, lpf_taps)

        # Ré-échantillonnage à 6400 Hz
        self.rational_resampler = filter.rational_resampler_ccc(
            interpolation=self.target_rate,
            decimation=self.input_rate,
            taps=[],
            fractional_bw=0
        )

        # Normalisation (facultatif)
        self.multiply_const = blocks.multiply_const_cc(1.0)

        # Décodeur COSPAS-SARSAT
        self.decoder = cospas_sarsat_decoder(debug_mode=True)

        # Sink pour les données décodées
        self.vector_sink = blocks.vector_sink_b()

        ##################################################
        # Connexions
        ##################################################
        self.connect((self.file_source, 0), (self.low_pass_filter, 0))
        self.connect((self.low_pass_filter, 0), (self.rational_resampler, 0))
        self.connect((self.rational_resampler, 0), (self.multiply_const, 0))
        self.connect((self.multiply_const, 0), (self.decoder, 0))
        self.connect((self.decoder, 0), (self.vector_sink, 0))


def main():
    if len(sys.argv) < 2:
        iq_file = "/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq"
        print(f"Usage: {sys.argv[0]} <fichier.iq> [sample_rate]")
        print(f"Utilisation du fichier par défaut: {iq_file}")
        print()
    else:
        iq_file = sys.argv[1]

    # Sample rate optionnel
    sample_rate = None
    if len(sys.argv) >= 3:
        sample_rate = int(sys.argv[2])
        print(f"Sample rate spécifié: {sample_rate} Hz\n")
    else:
        # Essayer de deviner le sample rate depuis la taille du fichier
        import os
        file_size = os.path.getsize(iq_file)
        num_samples = file_size // 8  # 8 bytes per complex float32

        # Fichiers générés par Matlab sont souvent à des taux standards
        possible_rates = [6400, 12800, 25600, 48000, 96000, 250000, 1000000, 2400000]

        print(f"Taille fichier: {file_size} octets = {num_samples} échantillons complexes")
        print(f"Durée à différents taux d'échantillonnage:")
        for rate in possible_rates:
            duration = num_samples / rate
            print(f"  {rate:8d} Hz → {duration:.3f} s")

        # Choisir un taux qui donne une durée raisonnable (0.5 - 5 secondes)
        for rate in possible_rates:
            duration = num_samples / rate
            if 0.5 <= duration <= 5.0:
                sample_rate = rate
                print(f"\nSample rate estimé: {sample_rate} Hz (durée {duration:.3f}s)")
                break

        if sample_rate is None:
            sample_rate = 250000  # Par défaut
            print(f"\nSample rate par défaut: {sample_rate} Hz")
        print()

    tb = decode_iq_file(iq_file, sample_rate)

    try:
        print("Démarrage du décodage I/Q...")
        print()
        tb.run()
        print()
        print("="*70)

        # Récupérer les données décodées
        data = list(tb.vector_sink.data())

        if len(data) > 0:
            print(f"\n✅ Données décodées: {len(data)} octets")
            print("\nDonnées complètes (hex):")
            print("  ", end="")
            for i, byte in enumerate(data):
                print(f"{byte:02X} ", end="")
                if (i + 1) % 18 == 0:
                    print("\n  ", end="")
            print()

            # Comparer avec la trame réelle connue si c'est une trame longue
            if len(data) >= 15:
                expected = bytes.fromhex("8E3E0425A52B002E364FF709674EB7")
                matches = sum(1 for i in range(min(len(expected), len(data)))
                            if data[i] == expected[i])
                print(f"\nComparaison avec trame connue:")
                print(f"  Octets correspondants: {matches}/{len(expected)}")
                if matches >= len(expected) * 0.8:
                    print("  ✅ Décodage réussi!")
        else:
            print("\n❌ Aucune donnée décodée")
            print("\nSuggestions:")
            print("  - Vérifier le sample rate du fichier")
            print("  - Essayer avec un autre sample rate:")
            print(f"    {sys.argv[0]} {iq_file} <sample_rate>")

        print("="*70)

    except KeyboardInterrupt:
        print("\nInterrompu par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()

if __name__ == '__main__':
    main()
