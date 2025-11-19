#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Capture et analyse plusieurs bursts PlutoSDR consécutifs
pour analyser la consistance de l'offset de fréquence
"""
import numpy as np
import sys
import os
from datetime import datetime

def extract_bursts(filename, threshold_factor=3.0, min_burst_samples=15000):
    """Extrait tous les bursts d'un fichier I/Q"""
    print(f"\n{'='*70}")
    print(f"Extraction des bursts de: {filename}")
    print(f"{'='*70}")

    # Lire le fichier
    iq = np.fromfile(filename, dtype=np.complex64)
    print(f"Échantillons totaux: {len(iq)} ({len(iq)/2500000:.2f} secondes à 2.5 MHz)")

    # Calculer la magnitude
    magnitude = np.abs(iq)

    # Détecter les bursts (amplitude > seuil)
    # Utiliser le percentile 90 comme seuil au lieu de moyenne + N*std
    threshold = np.percentile(magnitude, 90)
    print(f"Seuil de détection: {threshold:.3f} (percentile 90)")
    burst_mask = magnitude > threshold
    burst_samples = np.where(burst_mask)[0]

    if len(burst_samples) == 0:
        print("❌ Aucun burst détecté")
        return []

    # Trouver les régions continues (bursts séparés)
    bursts = []
    burst_start = burst_samples[0]
    last_sample = burst_samples[0]

    for sample in burst_samples[1:]:
        if sample - last_sample > 100000:  # Gap > 100000 échantillons (~40ms)
            burst_end = last_sample
            if burst_end - burst_start >= min_burst_samples:
                bursts.append((burst_start, burst_end))
                print(f"  Burst #{len(bursts)}: échantillons {burst_start}-{burst_end} "
                      f"({(burst_end - burst_start)/2500000*1000:.1f} ms)")
            burst_start = sample
        last_sample = sample

    # Dernier burst
    burst_end = last_sample
    if burst_end - burst_start >= min_burst_samples:
        bursts.append((burst_start, burst_end))
        print(f"  Burst #{len(bursts)}: échantillons {burst_start}-{burst_end} "
              f"({(burst_end - burst_start)/2500000*1000:.1f} ms)")

    print(f"\nBursts détectés: {len(bursts)}")
    return [(iq[start:end], start, end) for start, end in bursts]

def analyze_burst_carrier(burst_iq, burst_idx, start_sample):
    """Analyse la porteuse d'un burst"""
    print(f"\n{'='*70}")
    print(f"Analyse du burst #{burst_idx}")
    print(f"{'='*70}")

    # La porteuse est au début: 160ms = 400000 échantillons à 2.5 MHz
    carrier_len = min(400000, len(burst_iq) // 3)
    carrier_iq = burst_iq[:carrier_len]

    # Analyser la phase
    phase = np.angle(carrier_iq)
    magnitude = np.abs(carrier_iq)

    print(f"\nPorteuse (premiers {carrier_len} échantillons, {carrier_len/2500000*1000:.1f} ms):")
    print(f"  Amplitude moyenne: {magnitude.mean():.3f}")
    print(f"  Amplitude std:     {magnitude.std():.3f}")
    print(f"  Phase moyenne:     {phase.mean():.3f} rad ({np.degrees(phase.mean()):.1f}°)")
    print(f"  Phase std:         {phase.std():.3f} rad ({np.degrees(phase.std()):.1f}°)")

    # Calculer les différences de phase (dérivée)
    phase_diff = np.diff(phase)
    # Unwrap pour éviter les sauts -π/+π
    phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))

    print(f"  Phase diff moyenne: {phase_diff.mean():.6f} rad/échantillon")
    print(f"  Phase diff std:     {phase_diff.std():.6f} rad/échantillon")

    # Estimer l'offset de fréquence
    freq_offset = phase_diff.mean() / (2 * np.pi) * 2500000
    print(f"  Offset de fréquence estimé: {freq_offset:+.1f} Hz")

    # Analyser la dérive de phase sur 10 segments
    print(f"\n  Dérive de phase sur 10 segments:")
    segment_len = carrier_len // 10
    phase_means = []
    for i in range(10):
        segment_start = i * segment_len
        segment_end = segment_start + segment_len
        segment_phase = phase[segment_start:segment_end]
        segment_mean = segment_phase.mean()
        phase_means.append(segment_mean)
        print(f"    Segment {i+1}: phase_mean = {segment_mean:+.3f} rad")

    # Calculer la dérive totale
    phase_drift = phase_means[-1] - phase_means[0]
    print(f"  Dérive totale: {phase_drift:+.3f} rad ({np.degrees(phase_drift):+.1f}°)")

    # Vérifier la stabilité
    if phase.std() < 0.2:
        print(f"\n  ✅ Phase stable (std < 0.2 rad)")
    else:
        print(f"\n  ❌ Phase instable (std = {phase.std():.3f} rad > 0.2 rad)")
        print(f"     → Offset de fréquence: {freq_offset:+.1f} Hz doit être corrigé")

    return {
        'burst_idx': burst_idx,
        'start_sample': start_sample,
        'carrier_iq': carrier_iq,
        'freq_offset': freq_offset,
        'phase_std': phase.std(),
        'phase_mean': phase.mean(),
        'phase_means': phase_means,
        'phase_drift': phase_drift,
        'magnitude_mean': magnitude.mean()
    }

def compare_bursts(burst_results):
    """Compare les résultats de plusieurs bursts"""
    if len(burst_results) < 2:
        print("\n❌ Pas assez de bursts pour comparer")
        return

    print(f"\n{'='*70}")
    print(f"COMPARAISON DES {len(burst_results)} BURSTS")
    print(f"{'='*70}")

    print(f"\nOffset de fréquence:")
    offsets = [r['freq_offset'] for r in burst_results]
    for r in burst_results:
        print(f"  Burst #{r['burst_idx']}: {r['freq_offset']:+7.1f} Hz")
    print(f"  Moyenne:           {np.mean(offsets):+7.1f} Hz")
    print(f"  Std:               {np.std(offsets):7.1f} Hz")
    print(f"  Min-Max:           {min(offsets):+7.1f} - {max(offsets):+.1f} Hz")
    print(f"  Écart:             {max(offsets) - min(offsets):7.1f} Hz")

    if np.std(offsets) < 10.0:
        print(f"\n  ✅ Offset de fréquence CONSTANT (std < 10 Hz)")
        print(f"     → Une correction fixe de {np.mean(offsets):+.1f} Hz devrait suffire")
    else:
        print(f"\n  ⚠️  Offset de fréquence VARIABLE (std = {np.std(offsets):.1f} Hz)")
        print(f"     → Correction adaptative nécessaire")

    print(f"\nStabilité de phase (std):")
    for r in burst_results:
        print(f"  Burst #{r['burst_idx']}: {r['phase_std']:.3f} rad ({np.degrees(r['phase_std']):.1f}°)")

    print(f"\nDérive de phase pendant la porteuse:")
    for r in burst_results:
        print(f"  Burst #{r['burst_idx']}: {r['phase_drift']:+.3f} rad ({np.degrees(r['phase_drift']):+.1f}°)")

    drifts = [r['phase_drift'] for r in burst_results]
    if np.std(drifts) < 0.1:
        print(f"\n  ✅ Dérive de phase CONSTANTE (std < 0.1 rad)")
        print(f"     → Dérive moyenne: {np.mean(drifts):+.3f} rad")
    else:
        print(f"\n  ⚠️  Dérive de phase VARIABLE (std = {np.std(drifts):.3f} rad)")

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(f"Usage: {sys.argv[0]} <fichier_capture_2.5MHz.iq>")
        print(f"\nCapture avec GRC, puis analyse tous les bursts présents")
        sys.exit(1)

    capture_file = sys.argv[1]

    if not os.path.exists(capture_file):
        print(f"❌ Fichier non trouvé: {capture_file}")
        sys.exit(1)

    # Extraire tous les bursts
    bursts = extract_bursts(capture_file)

    if len(bursts) == 0:
        print("\n❌ Aucun burst détecté dans le fichier")
        sys.exit(1)

    # Analyser chaque burst
    burst_results = []
    for idx, (burst_iq, start, end) in enumerate(bursts, 1):
        result = analyze_burst_carrier(burst_iq, idx, start)
        burst_results.append(result)

    # Comparer les bursts
    compare_bursts(burst_results)

    print(f"\n{'='*70}")
