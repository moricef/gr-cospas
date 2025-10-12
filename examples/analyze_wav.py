#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse spectrale d'un fichier WAV COSPAS-SARSAT
Visualise le contenu fréquentiel pour comprendre la structure du signal
"""

import numpy as np
import matplotlib.pyplot as plt
from scipy.io import wavfile
from scipy import signal

# Fichier WAV à analyser
wav_file = "/home/fab2/Developpement/COSPAS-SARSAT/Audio/enregistrement_balise_exercice_zonesud/gqrx_20250918_091106_406028000.wav"

print("="*70)
print("ANALYSE SPECTRALE FICHIER WAV COSPAS-SARSAT")
print("="*70)

# Lire le fichier WAV
sample_rate, audio_data = wavfile.read(wav_file)

# Convertir en float et normaliser
if audio_data.dtype == np.int16:
    audio_data = audio_data.astype(np.float32) / 32768.0
elif audio_data.dtype == np.int32:
    audio_data = audio_data.astype(np.float32) / 2147483648.0

print(f"\nFichier: {wav_file}")
print(f"Fréquence d'échantillonnage: {sample_rate} Hz")
print(f"Durée: {len(audio_data)/sample_rate:.2f} secondes")
print(f"Nombre d'échantillons: {len(audio_data)}")
print(f"Amplitude min/max: {audio_data.min():.3f} / {audio_data.max():.3f}")

# Calculer le spectrogramme
f, t, Sxx = signal.spectrogram(audio_data, sample_rate,
                                nperseg=2048, noverlap=1024)

# Calculer la FFT sur une fenêtre représentative
fft_window = audio_data[len(audio_data)//4:len(audio_data)//4 + 48000]  # 1 seconde
fft_result = np.fft.fft(fft_window)
fft_freq = np.fft.fftfreq(len(fft_window), 1/sample_rate)
fft_magnitude = np.abs(fft_result)

# Trouver les pics principaux (fréquences dominantes)
half = len(fft_freq)//2
peaks, _ = signal.find_peaks(fft_magnitude[:half], height=np.max(fft_magnitude[:half])*0.1)
peak_freqs = fft_freq[peaks]
peak_mags = fft_magnitude[peaks]

# Trier par magnitude
sorted_idx = np.argsort(peak_mags)[::-1]
top_peaks = sorted_idx[:5]  # Top 5 fréquences

print("\n" + "="*70)
print("FRÉQUENCES DOMINANTES:")
print("="*70)
for i, idx in enumerate(top_peaks, 1):
    freq = peak_freqs[idx]
    mag = peak_mags[idx]
    print(f"{i}. {freq:8.1f} Hz  (magnitude: {mag:.0f})")

# Créer les graphiques
fig, axes = plt.subplots(3, 1, figsize=(12, 10))

# 1. Signal temporel
axes[0].plot(np.arange(len(audio_data[:48000]))/sample_rate, audio_data[:48000])
axes[0].set_xlabel('Temps (s)')
axes[0].set_ylabel('Amplitude')
axes[0].set_title('Signal audio (première seconde)')
axes[0].grid(True)

# 2. Spectrogramme
im = axes[1].pcolormesh(t, f, 10 * np.log10(Sxx + 1e-10), shading='gouraud', cmap='viridis')
axes[1].set_ylabel('Fréquence (Hz)')
axes[1].set_xlabel('Temps (s)')
axes[1].set_title('Spectrogramme')
axes[1].set_ylim([0, 5000])  # Limiter à 5 kHz
plt.colorbar(im, ax=axes[1], label='Puissance (dB)')

# 3. Spectre FFT
axes[2].plot(fft_freq[:half], 20*np.log10(fft_magnitude[:half] + 1e-10))
axes[2].set_xlabel('Fréquence (Hz)')
axes[2].set_ylabel('Magnitude (dB)')
axes[2].set_title('Spectre FFT (fenêtre 1s)')
axes[2].set_xlim([0, 5000])
axes[2].grid(True)

# Marquer les pics
for idx in top_peaks:
    freq = peak_freqs[idx]
    if 0 < freq < 5000:
        axes[2].axvline(freq, color='r', linestyle='--', alpha=0.5)
        axes[2].text(freq, axes[2].get_ylim()[1]*0.9, f'{freq:.0f} Hz',
                    rotation=90, va='top', fontsize=8)

plt.tight_layout()
print("\n" + "="*70)
print("Fermer la fenêtre graphique pour continuer...")
print("="*70)
plt.show()

print("\nAnalyse terminée.")
