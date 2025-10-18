#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Décodage direct d'un fichier I/Q Matlab (40 kHz, 100 samples/bit)
Sans ré-échantillonnage - traite le signal tel quel
"""

import numpy as np
import sys

def decode_biphase_l(signal, samples_per_bit=100):
    """
    Décode un signal Biphase-L

    Biphase-L:
    - Bit '1': première moitié à +1.1 rad, deuxième moitié à -1.1 rad
    - Bit '0': première moitié à -1.1 rad, deuxième moitié à +1.1 rad
    """

    phase = np.angle(signal)
    num_bits = len(signal) // samples_per_bit
    bits = []

    half_bit = samples_per_bit // 2

    for i in range(num_bits):
        start = i * samples_per_bit
        mid = start + half_bit
        end = start + samples_per_bit

        # Prendre les phases au centre de chaque moitié (plus robuste)
        center_first = start + half_bit // 2
        center_second = mid + half_bit // 2

        phase_first_half = phase[center_first]
        phase_second_half = phase[center_second]

        # Transition au milieu du bit
        transition = phase_second_half - phase_first_half

        # Unwrap
        if transition > np.pi:
            transition -= 2 * np.pi
        elif transition < -np.pi:
            transition += 2 * np.pi

        # Décision (selon générateur Matlab)
        # Bit '1': +1.1 → -1.1 (transition descendante)
        # Bit '0': -1.1 → +1.1 (transition montante)
        if transition < -0.5:  # Transition descendante
            bits.append(1)
        elif transition > 0.5:  # Transition montante
            bits.append(0)
        else:
            bits.append(-1)  # Indéterminé

    return bits

def main():
    if len(sys.argv) < 2:
        filename = "/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq"
    else:
        filename = sys.argv[1]

    print("="*70)
    print("DÉCODAGE DIRECT FICHIER I/Q MATLAB")
    print("="*70)

    # Lire le fichier
    data = np.fromfile(filename, dtype=np.float32)
    I = data[0::2]
    Q = data[1::2]
    signal = I + 1j * Q

    fs = 40000
    samples_per_bit = 100
    carrier_duration = 0.160  # 160 ms
    carrier_samples = int(carrier_duration * fs)

    print(f"\nFichier: {filename.split('/')[-1]}")
    print(f"Échantillons: {len(signal)}")
    print(f"Fréquence: {fs} Hz")
    print(f"Échantillons/bit: {samples_per_bit}")
    print()

    # Ignorer la porteuse (160 ms)
    data_start = carrier_samples
    data_signal = signal[data_start:]

    print(f"Porteuse: {carrier_samples} échantillons ignorés ({carrier_duration*1000} ms)")
    print(f"Signal de données: {len(data_signal)} échantillons")
    print()

    # Décoder les bits
    bits = decode_biphase_l(data_signal, samples_per_bit)

    print(f"Bits décodés: {len(bits)}")
    print()

    # Afficher les premiers bits
    print("Premiers 50 bits:")
    for i in range(min(50, len(bits))):
        if i > 0 and i % 10 == 0:
            print()
        if bits[i] == -1:
            print("?", end="")
        else:
            print(bits[i], end="")
    print("\n")

    # Convertir les premiers octets pour debug
    print("Premiers 5 octets décodés:")
    for byte_num in range(5):
        bit_start = byte_num * 8
        bit_end = bit_start + 8
        if bit_end <= len(bits):
            byte_bits = bits[bit_start:bit_end]
            byte_str = ''.join(str(b) for b in byte_bits)
            byte_val = sum(b << (7-i) for i, b in enumerate(byte_bits) if b != -1)
            print(f"  Octet {byte_num}: {byte_str} = 0x{byte_val:02X}")
    print()

    # Chercher le préambule (15 bits à '1')
    preamble_found = False
    preamble_pos = -1

    for i in range(len(bits) - 15):
        if all(b == 1 for b in bits[i:i+15]):
            preamble_found = True
            preamble_pos = i
            break

    if preamble_found:
        print(f"✅ Préambule trouvé à la position {preamble_pos}")

        # Frame sync (9 bits après préambule)
        frame_sync_start = preamble_pos + 15
        frame_sync = bits[frame_sync_start:frame_sync_start+9]
        frame_sync_str = ''.join(str(b) for b in frame_sync)

        expected_normal = "000101111"
        expected_test = "011010000"

        print(f"Frame sync: {frame_sync_str}")
        if frame_sync_str == expected_normal:
            print("  Mode: Normal")
        elif frame_sync_str == expected_test:
            print("  Mode: Self-Test")
        else:
            print("  ⚠️  Frame sync invalide")

        # Format flag (bit 25)
        format_flag_pos = frame_sync_start + 9
        if format_flag_pos < len(bits):
            format_flag = bits[format_flag_pos]
            frame_type = "LONGUE (144 bits)" if format_flag == 1 else "COURTE (112 bits)"
            print(f"Format flag: {format_flag} → Trame {frame_type}")

            # Extraire les données
            data_start = format_flag_pos
            data_length = 144 if format_flag == 1 else 112

            if data_start + data_length <= len(bits):
                data_bits = bits[data_start:data_start + data_length]

                # Convertir en octets
                data_bytes = []
                for i in range(0, len(data_bits), 8):
                    if i + 8 <= len(data_bits):
                        byte_bits = data_bits[i:i+8]
                        if all(b != -1 for b in byte_bits):
                            byte_val = sum(b << (7-j) for j, b in enumerate(byte_bits))
                            data_bytes.append(byte_val)

                print(f"\nDonnées décodées: {len(data_bytes)} octets")
                print("Hex: " + "".join(f"{b:02X}" for b in data_bytes))

                # Comparer avec trame connue
                expected_hex = "8E3E0425A52B002E364FF709674EB7"
                expected_bytes = bytes.fromhex(expected_hex)

                if len(data_bytes) >= len(expected_bytes):
                    matches = sum(1 for i in range(len(expected_bytes))
                                if data_bytes[i] == expected_bytes[i])
                    print(f"\nComparaison: {matches}/{len(expected_bytes)} octets corrects")
                    if matches == len(expected_bytes):
                        print("✅ Décodage parfait!")
            else:
                print(f"⚠️  Pas assez de bits pour une trame complète")
    else:
        print("❌ Préambule non trouvé")
        print("\nRecherche de séquences de '1':")
        max_ones = 0
        max_pos = -1
        current_ones = 0

        for i, b in enumerate(bits):
            if b == 1:
                current_ones += 1
                if current_ones > max_ones:
                    max_ones = current_ones
                    max_pos = i - current_ones + 1
            else:
                current_ones = 0

        print(f"Plus longue séquence: {max_ones} bits '1' à la position {max_pos}")

    print("="*70)

if __name__ == '__main__':
    main()
