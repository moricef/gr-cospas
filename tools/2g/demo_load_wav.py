#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Démonstration: Comment charger et utiliser les fichiers WAV I/Q

Les fichiers .wav générés par generate_sgb_iq_wav.py contiennent des données
I/Q baseband (pas du son audio). Ce script montre comment les charger correctement.

Usage:
    ./demo_load_wav.py <fichier.wav>
    ./demo_load_wav.py beacon_sgb.wav
"""

import sys
import wave
import numpy as np
import matplotlib
matplotlib.use('Agg')  # Backend non-interactif
import matplotlib.pyplot as plt

def load_iq_from_wav(filename):
    """
    Charge fichier WAV stéréo et reconstruit échantillons I/Q complexes

    Args:
        filename: Chemin du fichier WAV (I=Left, Q=Right)

    Returns:
        tuple: (complex_samples, sample_rate)
    """
    with wave.open(filename, 'rb') as wav:
        # Vérifier format
        n_channels = wav.getnchannels()
        sampwidth = wav.getsampwidth()
        framerate = wav.getframerate()
        n_frames = wav.getnframes()

        if n_channels != 2:
            raise ValueError(f"Fichier doit être stéréo (2 canaux), trouvé: {n_channels}")

        if sampwidth != 2:
            raise ValueError(f"Fichier doit être 16-bit (2 bytes), trouvé: {sampwidth}")

        # Lire toutes les trames
        frames = wav.readframes(n_frames)

    # Convertir en tableau numpy int16
    audio_data = np.frombuffer(frames, dtype=np.int16)

    # Séparer canaux gauche (I) et droit (Q)
    i_channel = audio_data[0::2].astype(float) / 32768.0  # Normaliser à [-1, 1]
    q_channel = audio_data[1::2].astype(float) / 32768.0

    # Construire échantillons complexes
    complex_samples = i_channel + 1j * q_channel

    return complex_samples, framerate

def analyze_signal(samples, sample_rate):
    """
    Analyse basique du signal I/Q

    Args:
        samples: Échantillons complexes
        sample_rate: Fréquence échantillonnage (Hz)
    """
    print("=" * 70)
    print("  ANALYSE SIGNAL I/Q DEPUIS FICHIER WAV")
    print("=" * 70)
    print()

    # Statistiques de base
    i_samples = np.real(samples)
    q_samples = np.imag(samples)

    print(f"📊 Statistiques:")
    print(f"  Échantillons: {len(samples):,}")
    print(f"  Sample rate: {sample_rate:,} Hz")
    print(f"  Durée: {len(samples) / sample_rate:.3f} s")
    print()

    print(f"Canal I:")
    print(f"  Range: [{i_samples.min():.3f}, {i_samples.max():.3f}]")
    print(f"  Mean: {i_samples.mean():.6f}")
    print(f"  RMS: {np.sqrt(np.mean(i_samples**2)):.3f}")
    print()

    print(f"Canal Q:")
    print(f"  Range: [{q_samples.min():.3f}, {q_samples.max():.3f}]")
    print(f"  Mean: {q_samples.mean():.6f}")
    print(f"  RMS: {np.sqrt(np.mean(q_samples**2)):.3f}")
    print()

    # Analyse spectrale
    fft_size = min(2048, len(samples))
    fft = np.fft.fftshift(np.fft.fft(samples[:fft_size]))
    freq = np.fft.fftshift(np.fft.fftfreq(fft_size, 1/sample_rate))
    power_db = 20 * np.log10(np.abs(fft) + 1e-10)

    peak_idx = np.argmax(power_db)
    peak_freq = freq[peak_idx]
    peak_power = power_db[peak_idx]

    # Largeur de bande (-20 dB)
    threshold = peak_power - 20
    signal_mask = power_db > threshold
    signal_freqs = freq[signal_mask]

    if len(signal_freqs) > 0:
        bandwidth = signal_freqs[-1] - signal_freqs[0]
    else:
        bandwidth = 0

    print(f"🔬 Analyse spectrale:")
    print(f"  Puissance pic: {peak_power:.1f} dB")
    print(f"  Fréquence centrale: {peak_freq:.1f} Hz (baseband)")
    print(f"  Largeur bande (-20dB): {bandwidth/1000:.1f} kHz")
    print()

    # Graphiques
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))

    # 1. Constellation
    ax = axes[0, 0]
    ax.scatter(i_samples[::10], q_samples[::10], alpha=0.3, s=1)
    ax.set_xlabel('I (In-phase)')
    ax.set_ylabel('Q (Quadrature)')
    ax.set_title('Constellation Diagram')
    ax.grid(True, alpha=0.3)
    ax.axis('equal')

    # 2. Time series I/Q
    ax = axes[0, 1]
    n_plot = min(500, len(samples))
    t = np.arange(n_plot) / sample_rate * 1000  # ms
    ax.plot(t, i_samples[:n_plot], label='I', alpha=0.7)
    ax.plot(t, q_samples[:n_plot], label='Q', alpha=0.7)
    ax.set_xlabel('Temps (ms)')
    ax.set_ylabel('Amplitude')
    ax.set_title('Signal temporel I/Q')
    ax.legend()
    ax.grid(True, alpha=0.3)

    # 3. Spectre
    ax = axes[1, 0]
    ax.plot(freq/1000, power_db)
    ax.set_xlabel('Fréquence (kHz)')
    ax.set_ylabel('Puissance (dB)')
    ax.set_title('Spectre FFT')
    ax.grid(True, alpha=0.3)
    ax.axhline(y=threshold, color='r', linestyle='--', alpha=0.5, label='-20dB')
    ax.legend()

    # 4. Magnitude
    ax = axes[1, 1]
    magnitude = np.abs(samples)
    ax.hist(magnitude, bins=100, alpha=0.7, edgecolor='black')
    ax.set_xlabel('Magnitude')
    ax.set_ylabel('Count')
    ax.set_title('Distribution de magnitude')
    ax.grid(True, alpha=0.3)

    plt.tight_layout()
    output_file = 'wav_analysis.png'
    plt.savefig(output_file, dpi=150, bbox_inches='tight')
    print(f"📈 Graphiques sauvegardés: {output_file}")
    print()

    print("=" * 70)
    print("✅ Le fichier WAV contient bien des données I/Q valides")
    print()
    print("💡 Utilisation dans GNU Radio:")
    print("   WAV File Source → Complex to Float → (votre flowgraph)")
    print("     - Sample rate: 48000")
    print("     - Channels: 2 (Left=I, Right=Q)")
    print("=" * 70)

def main():
    if len(sys.argv) != 2:
        print(__doc__)
        sys.exit(1)

    filename = sys.argv[1]

    try:
        # Charger fichier WAV
        samples, sample_rate = load_iq_from_wav(filename)

        # Analyser
        analyze_signal(samples, sample_rate)

    except FileNotFoundError:
        print(f"❌ Erreur: Fichier '{filename}' introuvable")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == '__main__':
    main()
