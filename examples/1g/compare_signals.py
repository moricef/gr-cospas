#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Compare deux fichiers I/Q COSPAS-SARSAT pour identifier les différences
"""
import numpy as np
import matplotlib.pyplot as plt
import sys

def analyze_iq_file(filename, max_samples=100000):
    """Analyse un fichier I/Q et retourne des statistiques"""
    print(f"\n{'='*70}")
    print(f"Analyse de: {filename.split('/')[-1]}")
    print(f"{'='*70}")

    # Lire le fichier
    iq = np.fromfile(filename, dtype=np.complex64, count=max_samples)
    print(f"Échantillons: {len(iq)}")

    # Calculer la magnitude et la phase
    magnitude = np.abs(iq)
    phase = np.angle(iq)

    # Détecter les bursts (amplitude > seuil)
    threshold = magnitude.mean() + 3 * magnitude.std()
    burst_mask = magnitude > threshold
    burst_samples = np.where(burst_mask)[0]

    if len(burst_samples) > 0:
        # Trouver les régions continues
        burst_starts = [burst_samples[0]]
        burst_ends = []
        for i in range(1, len(burst_samples)):
            if burst_samples[i] - burst_samples[i-1] > 100:  # Gap > 100 échantillons
                burst_ends.append(burst_samples[i-1])
                burst_starts.append(burst_samples[i])
        burst_ends.append(burst_samples[-1])

        print(f"\nBursts détectés: {len(burst_starts)}")
        for i, (start, end) in enumerate(zip(burst_starts[:3], burst_ends[:3])):
            duration_ms = (end - start) / 40000 * 1000  # Assuming 40 kHz
            print(f"  Burst #{i+1}: échantillons {start}-{end} ({duration_ms:.1f} ms)")

            # Analyser le premier burst en détail
            if i == 0:
                burst_iq = iq[start:end]
                burst_mag = magnitude[start:end]
                burst_phase = phase[start:end]

                # Chercher la porteuse (160ms = 6400 échantillons à 40 kHz)
                carrier_len = min(6400, len(burst_iq) // 3)
                carrier_iq = burst_iq[:carrier_len]
                carrier_phase = burst_phase[:carrier_len]

                # Analyser la stabilité de phase de la porteuse
                phase_diff = np.diff(carrier_phase)
                # Unwrap pour éviter les sauts -π/+π
                phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))

                print(f"\n  Porteuse (premiers {carrier_len} échantillons):")
                print(f"    Amplitude moyenne: {burst_mag[:carrier_len].mean():.3f}")
                print(f"    Amplitude std:     {burst_mag[:carrier_len].std():.3f}")
                print(f"    Phase moyenne:     {carrier_phase.mean():.3f} rad")
                print(f"    Phase std:         {carrier_phase.std():.3f} rad")
                print(f"    Phase diff moyenne:{phase_diff.mean():.6f} rad/échantillon")
                print(f"    Phase diff std:    {phase_diff.std():.6f} rad/échantillon")

                # Estimer l'offset de fréquence
                freq_offset = phase_diff.mean() / (2 * np.pi) * 40000
                print(f"    Offset de fréquence estimé: {freq_offset:.1f} Hz")

                # Analyser la partie BPSK (après la porteuse)
                if len(burst_iq) > carrier_len + 1000:
                    bpsk_iq = burst_iq[carrier_len:carrier_len+1000]
                    bpsk_phase = burst_phase[carrier_len:carrier_len+1000]

                    # Détecter les sauts de phase (BPSK)
                    phase_jumps = np.abs(np.diff(bpsk_phase))
                    phase_jumps = np.arctan2(np.sin(phase_jumps), np.cos(phase_jumps))
                    large_jumps = phase_jumps[np.abs(phase_jumps) > 0.5]

                    print(f"\n  Données BPSK (échantillons {carrier_len}-{carrier_len+1000}):")
                    print(f"    Sauts de phase > 0.5 rad: {len(large_jumps)}")
                    if len(large_jumps) > 0:
                        print(f"    Saut moyen: {large_jumps.mean():.3f} rad")
                        print(f"    Saut std:   {large_jumps.std():.3f} rad")

                return {
                    'iq': iq,
                    'burst_iq': burst_iq,
                    'burst_start': start,
                    'burst_end': end,
                    'carrier_iq': carrier_iq,
                    'freq_offset': freq_offset,
                    'phase_std': carrier_phase.std()
                }
    else:
        print("\n❌ Aucun burst détecté")

    # Statistiques globales
    print(f"\nStatistiques globales:")
    print(f"  Amplitude moyenne: {magnitude.mean():.3f}")
    print(f"  Amplitude std:     {magnitude.std():.3f}")
    print(f"  Amplitude max:     {magnitude.max():.3f}")

    return {'iq': iq}

def compare_bursts(ref_data, test_data):
    """Compare les bursts de deux fichiers"""
    if 'burst_iq' not in ref_data or 'burst_iq' not in test_data:
        print("\n❌ Impossible de comparer: bursts non détectés")
        return

    print(f"\n{'='*70}")
    print("COMPARAISON DES BURSTS")
    print(f"{'='*70}")

    ref_burst = ref_data['burst_iq']
    test_burst = test_data['burst_iq']

    print(f"\nLongueur des bursts:")
    print(f"  Référence: {len(ref_burst)} échantillons ({len(ref_burst)/40000*1000:.1f} ms)")
    print(f"  Test:      {len(test_burst)} échantillons ({len(test_burst)/40000*1000:.1f} ms)")

    print(f"\nOffset de fréquence:")
    print(f"  Référence: {ref_data['freq_offset']:.1f} Hz")
    print(f"  Test:      {test_data['freq_offset']:.1f} Hz")
    print(f"  Différence: {abs(ref_data['freq_offset'] - test_data['freq_offset']):.1f} Hz")

    print(f"\nStabilité de phase (porteuse):")
    print(f"  Référence: {ref_data['phase_std']:.3f} rad")
    print(f"  Test:      {test_data['phase_std']:.3f} rad")
    if test_data['phase_std'] > 0.2:
        print(f"  ⚠️  La phase du signal test est trop instable (> 0.2 rad)")
        print(f"      → L'offset de fréquence doit être corrigé")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <fichier_reference.iq> <fichier_test.iq>")
        sys.exit(1)

    ref_file = sys.argv[1]
    test_file = sys.argv[2]

    # Analyser les deux fichiers
    ref_data = analyze_iq_file(ref_file)
    test_data = analyze_iq_file(test_file)

    # Comparer
    compare_bursts(ref_data, test_data)

    print(f"\n{'='*70}")
