#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse la porteuse au début des fichiers I/Q COSPAS-SARSAT
"""
import numpy as np
import matplotlib.pyplot as plt
import sys

def analyze_carrier(filename, start_sample=0, carrier_len=6400):
    """Analyse la porteuse dans un fichier I/Q"""
    print(f"\n{'='*70}")
    print(f"Analyse de: {filename.split('/')[-1]}")
    print(f"{'='*70}")

    # Lire le fichier
    iq = np.fromfile(filename, dtype=np.complex64)
    print(f"Échantillons totaux: {len(iq)} ({len(iq)/40000:.2f} secondes)")

    # Extraire la porteuse
    carrier_iq = iq[start_sample:start_sample+carrier_len]
    print(f"\nAnalyse de la porteuse: échantillons {start_sample}-{start_sample+carrier_len}")

    # Magnitude et phase
    magnitude = np.abs(carrier_iq)
    phase = np.angle(carrier_iq)

    print(f"\nAmplitude:")
    print(f"  Moyenne: {magnitude.mean():.4f}")
    print(f"  Std:     {magnitude.std():.4f}")
    print(f"  Min:     {magnitude.min():.4f}")
    print(f"  Max:     {magnitude.max():.4f}")

    # Analyser la phase
    print(f"\nPhase:")
    print(f"  Moyenne: {phase.mean():.4f} rad ({np.degrees(phase.mean()):.1f}°)")
    print(f"  Std:     {phase.std():.4f} rad ({np.degrees(phase.std()):.1f}°)")

    # Calculer les différences de phase (dérivée)
    phase_diff = np.diff(phase)
    # Unwrap pour éviter les sauts -π/+π
    phase_diff = np.arctan2(np.sin(phase_diff), np.cos(phase_diff))

    print(f"\nDifférence de phase (dérivée):")
    print(f"  Moyenne: {phase_diff.mean():.6f} rad/échantillon")
    print(f"  Std:     {phase_diff.std():.6f} rad/échantillon")

    # Estimer l'offset de fréquence
    freq_offset = phase_diff.mean() / (2 * np.pi) * 40000
    print(f"\nOffset de fréquence estimé: {freq_offset:.1f} Hz")

    # Vérifier la stabilité
    if phase.std() < 0.2:
        print(f"✅ Phase stable (std < 0.2 rad)")
    else:
        print(f"❌ Phase instable (std = {phase.std():.3f} rad > 0.2 rad)")
        print(f"   → Offset de fréquence: {freq_offset:.1f} Hz doit être corrigé")

    # Analyser l'IQ dans le plan complexe
    print(f"\nPlan I/Q:")
    print(f"  I (réel) - Moyenne: {carrier_iq.real.mean():.4f}, Std: {carrier_iq.real.std():.4f}")
    print(f"  Q (imag) - Moyenne: {carrier_iq.imag.mean():.4f}, Std: {carrier_iq.imag.std():.4f}")

    return {
        'iq': iq,
        'carrier_iq': carrier_iq,
        'magnitude': magnitude,
        'phase': phase,
        'phase_diff': phase_diff,
        'freq_offset': freq_offset,
        'phase_std': phase.std()
    }

def plot_comparison(ref_data, test_data):
    """Trace les graphiques de comparaison"""
    fig, axes = plt.subplots(3, 2, figsize=(14, 10))

    # Magnitude
    axes[0, 0].plot(ref_data['magnitude'][:1000], label='Référence', alpha=0.7)
    axes[0, 0].set_title('Magnitude - Référence')
    axes[0, 0].set_xlabel('Échantillon')
    axes[0, 0].set_ylabel('Amplitude')
    axes[0, 0].grid(True, alpha=0.3)

    axes[0, 1].plot(test_data['magnitude'][:1000], label='Test', color='orange', alpha=0.7)
    axes[0, 1].set_title('Magnitude - Test')
    axes[0, 1].set_xlabel('Échantillon')
    axes[0, 1].set_ylabel('Amplitude')
    axes[0, 1].grid(True, alpha=0.3)

    # Phase
    axes[1, 0].plot(ref_data['phase'][:1000], label='Référence', alpha=0.7)
    axes[1, 0].set_title(f'Phase - Référence (std={ref_data["phase_std"]:.3f} rad)')
    axes[1, 0].set_xlabel('Échantillon')
    axes[1, 0].set_ylabel('Phase (rad)')
    axes[1, 0].axhline(y=0, color='r', linestyle='--', alpha=0.3)
    axes[1, 0].grid(True, alpha=0.3)

    axes[1, 1].plot(test_data['phase'][:1000], label='Test', color='orange', alpha=0.7)
    axes[1, 1].set_title(f'Phase - Test (std={test_data["phase_std"]:.3f} rad)')
    axes[1, 1].set_xlabel('Échantillon')
    axes[1, 1].set_ylabel('Phase (rad)')
    axes[1, 1].axhline(y=0, color='r', linestyle='--', alpha=0.3)
    axes[1, 1].grid(True, alpha=0.3)

    # Plan I/Q (constellation)
    axes[2, 0].scatter(ref_data['carrier_iq'][:1000].real, ref_data['carrier_iq'][:1000].imag,
                      s=1, alpha=0.5, label='Référence')
    axes[2, 0].set_title('Constellation - Référence')
    axes[2, 0].set_xlabel('I (réel)')
    axes[2, 0].set_ylabel('Q (imag)')
    axes[2, 0].axhline(y=0, color='r', linestyle='--', alpha=0.3)
    axes[2, 0].axvline(x=0, color='r', linestyle='--', alpha=0.3)
    axes[2, 0].grid(True, alpha=0.3)
    axes[2, 0].axis('equal')

    axes[2, 1].scatter(test_data['carrier_iq'][:1000].real, test_data['carrier_iq'][:1000].imag,
                      s=1, alpha=0.5, color='orange', label='Test')
    axes[2, 1].set_title('Constellation - Test')
    axes[2, 1].set_xlabel('I (réel)')
    axes[2, 1].set_ylabel('Q (imag)')
    axes[2, 1].axhline(y=0, color='r', linestyle='--', alpha=0.3)
    axes[2, 1].axvline(x=0, color='r', linestyle='--', alpha=0.3)
    axes[2, 1].grid(True, alpha=0.3)
    axes[2, 1].axis('equal')

    plt.tight_layout()
    plt.savefig('comparison_carrier.png', dpi=150)
    print(f"\n📊 Graphique sauvegardé: comparison_carrier.png")

if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(f"Usage: {sys.argv[0]} <fichier_reference.iq> <fichier_test.iq>")
        sys.exit(1)

    ref_file = sys.argv[1]
    test_file = sys.argv[2]

    # Analyser les deux fichiers
    ref_data = analyze_carrier(ref_file, start_sample=0, carrier_len=6400)
    test_data = analyze_carrier(test_file, start_sample=0, carrier_len=6400)

    # Comparer
    print(f"\n{'='*70}")
    print("COMPARAISON")
    print(f"{'='*70}")
    print(f"\nOffset de fréquence:")
    print(f"  Référence: {ref_data['freq_offset']:+.1f} Hz")
    print(f"  Test:      {test_data['freq_offset']:+.1f} Hz")
    print(f"  Différence: {abs(ref_data['freq_offset'] - test_data['freq_offset']):.1f} Hz")

    print(f"\nStabilité de phase:")
    print(f"  Référence: {ref_data['phase_std']:.4f} rad")
    print(f"  Test:      {test_data['phase_std']:.4f} rad")

    if test_data['phase_std'] > ref_data['phase_std'] * 2:
        print(f"\n⚠️  La phase du signal test est {test_data['phase_std']/ref_data['phase_std']:.1f}x plus instable")

    print(f"\n{'='*70}")

    # Tracer les graphiques
    try:
        plot_comparison(ref_data, test_data)
    except Exception as e:
        print(f"Erreur lors du tracé: {e}")
