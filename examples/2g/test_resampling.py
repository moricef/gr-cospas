#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test l'effet du ré-échantillonnage sur le signal IQ Matlab
Compare le signal original vs ré-échantillonné
"""

import numpy as np
from gnuradio import filter

def main():
    filename = "/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/sarsat-main/beacon_signal_406mhz_long_msg_144bit.iq"

    print("="*70)
    print("TEST DU RÉ-ÉCHANTILLONNAGE")
    print("="*70)

    # Lire le signal original
    data = np.fromfile(filename, dtype=np.float32)
    I = data[0::2]
    Q = data[1::2]
    signal_40khz = I + 1j * Q

    print(f"\nSignal original à 40 kHz:")
    print(f"  Échantillons: {len(signal_40khz)}")
    print(f"  Échantillons/bit: 100")

    # Créer un ré-échantillonneur GNU Radio
    input_rate = 40000
    target_rate = 6400

    # Simuler le ré-échantillonnage avec scipy
    from scipy import signal as scipy_signal

    # Décimation: 40000 / 6400 = 6.25 = 25/4
    decim_factor = 25
    interp_factor = 4

    # Ré-échantillonner
    signal_resampled = scipy_signal.resample_poly(signal_40khz, interp_factor, decim_factor)

    print(f"\nSignal ré-échantillonné à 6.4 kHz:")
    print(f"  Échantillons: {len(signal_resampled)}")
    print(f"  Échantillons/bit: {len(signal_resampled) / (len(signal_40khz) / 100):.1f}")
    print(f"  Ratio: {len(signal_resampled) / len(signal_40khz):.4f}")

    # Analyser les phases
    carrier_duration = 0.160  # 160 ms
    carrier_samples_40k = int(carrier_duration * input_rate)
    carrier_samples_6k4 = int(carrier_duration * target_rate)

    # Signal de données (après porteuse)
    data_40k = signal_40khz[carrier_samples_40k:carrier_samples_40k + 5000]
    data_6k4 = signal_resampled[carrier_samples_6k4:carrier_samples_6k4 + 800]

    phase_40k = np.angle(data_40k)
    phase_6k4 = np.angle(data_6k4)

    # Calculer les différences de phase
    phase_diff_40k = np.diff(phase_40k)
    phase_diff_6k4 = np.diff(phase_6k4)

    # Unwrap
    phase_diff_40k = np.where(phase_diff_40k > np.pi, phase_diff_40k - 2*np.pi, phase_diff_40k)
    phase_diff_40k = np.where(phase_diff_40k < -np.pi, phase_diff_40k + 2*np.pi, phase_diff_40k)
    phase_diff_6k4 = np.where(phase_diff_6k4 > np.pi, phase_diff_6k4 - 2*np.pi, phase_diff_6k4)
    phase_diff_6k4 = np.where(phase_diff_6k4 < -np.pi, phase_diff_6k4 + 2*np.pi, phase_diff_6k4)

    print(f"\nAnalyse des phases (premiers 5000/800 échantillons après porteuse):")
    print(f"\nSignal 40 kHz:")
    print(f"  Phase: min={phase_40k.min():.3f}, max={phase_40k.max():.3f}")
    print(f"  Diff phase: min={phase_diff_40k.min():.3f}, max={phase_diff_40k.max():.3f}")
    print(f"  Transitions > 0.5 rad: {np.sum(np.abs(phase_diff_40k) > 0.5)}")

    print(f"\nSignal 6.4 kHz (ré-échantillonné):")
    print(f"  Phase: min={phase_6k4.min():.3f}, max={phase_6k4.max():.3f}")
    print(f"  Diff phase: min={phase_diff_6k4.min():.3f}, max={phase_diff_6k4.max():.3f}")
    print(f"  Transitions > 0.5 rad: {np.sum(np.abs(phase_diff_6k4) > 0.5)}")

    # Examiner les premiers bits
    print(f"\nPremiers 3 bits (échantillons de données):")
    print(f"\nSignal 40 kHz (100 échantillons/bit):")
    for bit_num in range(3):
        start = bit_num * 100
        end = start + 100
        bit_phase = phase_40k[start:end]
        half = 50
        phase_first = np.mean(bit_phase[:half])
        phase_second = np.mean(bit_phase[half:])
        transition = phase_second - phase_first
        if transition > np.pi:
            transition -= 2 * np.pi
        elif transition < -np.pi:
            transition += 2 * np.pi
        print(f"  Bit {bit_num}: phase 1={phase_first:6.3f}, phase 2={phase_second:6.3f}, transition={transition:6.3f}")

    print(f"\nSignal 6.4 kHz (16 échantillons/bit):")
    for bit_num in range(3):
        start = bit_num * 16
        end = start + 16
        if end <= len(phase_6k4):
            bit_phase = phase_6k4[start:end]
            half = 8
            phase_first = np.mean(bit_phase[:half])
            phase_second = np.mean(bit_phase[half:])
            transition = phase_second - phase_first
            if transition > np.pi:
                transition -= 2 * np.pi
            elif transition < -np.pi:
                transition += 2 * np.pi
            print(f"  Bit {bit_num}: phase 1={phase_first:6.3f}, phase 2={phase_second:6.3f}, transition={transition:6.3f}")

    print("\n" + "="*70)
    print("CONCLUSION:")
    print("="*70)
    print("Les transitions de phase sont-elles préservées par le ré-échantillonnage?")
    print("Si les transitions du signal ré-échantillonné sont < 0.5 rad,")
    print("alors le décodeur ne pourra pas les détecter correctement.")
    print("="*70)

if __name__ == '__main__':
    main()
