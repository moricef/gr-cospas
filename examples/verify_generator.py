#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Vérification du générateur COSPAS-SARSAT
Analyse les échantillons générés pour voir s'ils correspondent à la spec
"""

import numpy as np
import sys
sys.path.insert(0, '/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/python')

from gnuradio import cospas

def main():
    print("=" * 70)
    print("VÉRIFICATION DU GÉNÉRATEUR COSPAS-SARSAT")
    print("=" * 70)
    print()

    # Créer le générateur avec des données simples
    test_data = bytes([0xFF])  # 1 octet = 8 bits à '1'
    gen = cospas.cospas_generator(data_bytes=test_data, repeat=False)

    print("Analyse des échantillons générés:")
    print()

    # Paramètres attendus
    CARRIER_SAMPLES = 1024
    PREAMBLE_BITS = 15
    DATA_BITS = 8
    SAMPLES_PER_BIT = 16

    total_expected = CARRIER_SAMPLES + (PREAMBLE_BITS + DATA_BITS) * SAMPLES_PER_BIT

    print(f"Échantillons attendus:")
    print(f"  - Porteuse: {CARRIER_SAMPLES}")
    print(f"  - Préambule: {PREAMBLE_BITS} bits × {SAMPLES_PER_BIT} = {PREAMBLE_BITS * SAMPLES_PER_BIT}")
    print(f"  - Données: {DATA_BITS} bits × {SAMPLES_PER_BIT} = {DATA_BITS * SAMPLES_PER_BIT}")
    print(f"  - TOTAL: {total_expected}")
    print(f"  - Durée: {total_expected / 6400.0:.3f} secondes")
    print()

    # Accéder à la trame générée
    frame = gen.frame
    print(f"Trame générée: {len(frame)} échantillons")
    print()

    # Analyser la porteuse (1024 premiers échantillons)
    print("=" * 70)
    print("ANALYSE DE LA PORTEUSE (échantillons 0-1023)")
    print("=" * 70)
    carrier = frame[0:CARRIER_SAMPLES]
    phases_carrier = np.angle(carrier)
    print(f"Phase min: {np.min(phases_carrier):.6f} rad")
    print(f"Phase max: {np.max(phases_carrier):.6f} rad")
    print(f"Phase moyenne: {np.mean(phases_carrier):.6f} rad")
    print(f"Phase std dev: {np.std(phases_carrier):.6f} rad")
    print(f"Magnitude moyenne: {np.mean(np.abs(carrier)):.6f}")
    print()

    # Analyser le premier bit du préambule (échantillons 1024-1039)
    print("=" * 70)
    print("ANALYSE DU PREMIER BIT DU PRÉAMBULE (échantillons 1024-1039)")
    print("=" * 70)
    print("Un bit '1' en biphase-L doit avoir :")
    print("  - Première moitié (8 échantillons): phase +1.1 rad")
    print("  - Deuxième moitié (8 échantillons): phase -1.1 rad")
    print()

    first_bit_start = CARRIER_SAMPLES
    first_bit = frame[first_bit_start:first_bit_start + SAMPLES_PER_BIT]
    first_half = first_bit[0:8]
    second_half = first_bit[8:16]

    phase_first_half = np.angle(first_half)
    phase_second_half = np.angle(second_half)

    print(f"Première moitié (échantillons 1024-1031):")
    for i, p in enumerate(phase_first_half):
        print(f"  Échantillon {i}: phase = {p:.6f} rad, magnitude = {np.abs(first_half[i]):.6f}")
    print(f"  Phase moyenne: {np.mean(phase_first_half):.6f} rad (attendu: +1.1)")
    print()

    print(f"Deuxième moitié (échantillons 1032-1039):")
    for i, p in enumerate(phase_second_half):
        print(f"  Échantillon {i+8}: phase = {p:.6f} rad, magnitude = {np.abs(second_half[i]):.6f}")
    print(f"  Phase moyenne: {np.mean(phase_second_half):.6f} rad (attendu: -1.1)")
    print()

    # Calcul de la différence comme le fait le décodeur
    first_half_sum = np.sum(first_half)
    second_half_sum = np.sum(second_half)
    phase_first_avg = np.angle(first_half_sum)
    phase_second_avg = np.angle(second_half_sum)
    phase_diff = phase_second_avg - phase_first_avg

    # Normaliser dans [-π, π]
    while phase_diff > np.pi:
        phase_diff -= 2 * np.pi
    while phase_diff < -np.pi:
        phase_diff += 2 * np.pi

    print(f"Décodage comme le fait le décodeur:")
    print(f"  Somme première moitié: {first_half_sum}")
    print(f"  Phase de la somme: {phase_first_avg:.6f} rad")
    print(f"  Somme deuxième moitié: {second_half_sum}")
    print(f"  Phase de la somme: {phase_second_avg:.6f} rad")
    print(f"  Différence de phase: {phase_diff:.6f} rad (attendu: ~-2.2)")
    print()

    if phase_diff < -1.0:
        print("✓ Bit décodé: '1' (correct!)")
    elif phase_diff > 1.0:
        print("✗ Bit décodé: '0' (ERREUR - attendu '1')")
    else:
        print(f"✗ Bit ambigu: diff = {phase_diff:.6f} (ERREUR)")
    print()

if __name__ == '__main__':
    main()
