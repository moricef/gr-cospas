#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Analyse spectrale d'un fichier WAV COSPAS-SARSAT (sans GUI)
"""

import numpy as np
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

print(f"\nFichier: {wav_file.split('/')[-1]}")
print(f"Fréquence d'échantillonnage: {sample_rate} Hz")
print(f"Durée: {len(audio_data)/sample_rate:.2f} secondes")
print(f"Nombre d'échantillons: {len(audio_data)}")
print(f"Amplitude min/max: {audio_data.min():.3f} / {audio_data.max():.3f}")

# Calculer la FFT sur plusieurs fenêtres pour moyenner
n_windows = 10
window_size = 48000  # 1 seconde
fft_avg = np.zeros(window_size // 2)

for i in range(n_windows):
    start = i * len(audio_data) // n_windows
    end = start + window_size
    if end > len(audio_data):
        break

    window = audio_data[start:end]
    fft_result = np.fft.fft(window)
    fft_magnitude = np.abs(fft_result[:window_size//2])
    fft_avg += fft_magnitude

fft_avg /= n_windows
fft_freq = np.fft.fftfreq(window_size, 1/sample_rate)[:window_size//2]

# Trouver les pics principaux
peaks, properties = signal.find_peaks(fft_avg, height=np.max(fft_avg)*0.1, distance=50)
peak_freqs = fft_freq[peaks]
peak_mags = fft_avg[peaks]

# Trier par magnitude
sorted_idx = np.argsort(peak_mags)[::-1]
top_peaks = sorted_idx[:10]  # Top 10 fréquences

print("\n" + "="*70)
print("TOP 10 FRÉQUENCES DOMINANTES:")
print("="*70)
print(f"{'Rang':<6} {'Fréquence':<12} {'Magnitude':<12} {'Note'}")
print("-"*70)

for i, idx in enumerate(top_peaks, 1):
    freq = peak_freqs[idx]
    mag = peak_mags[idx]

    # Identifier les fréquences intéressantes
    note = ""
    if 900 < freq < 1100:
        note = "← PORTEUSE 1kHz attendue"
    elif 1900 < freq < 2100:
        note = "← Harmonique 2"
    elif freq < 100:
        note = "← Basse fréquence / DC"

    print(f"{i:<6} {freq:8.1f} Hz   {mag:10.0f}    {note}")

# Calculer l'énergie dans différentes bandes
bands = [
    (0, 100, "DC / Basse fréquence"),
    (100, 500, "0.1 - 0.5 kHz"),
    (500, 1500, "0.5 - 1.5 kHz (zone attendue)"),
    (1500, 3000, "1.5 - 3 kHz"),
    (3000, 5000, "3 - 5 kHz"),
    (5000, 24000, "5 - 24 kHz")
]

print("\n" + "="*70)
print("ÉNERGIE PAR BANDE DE FRÉQUENCE:")
print("="*70)

for low, high, label in bands:
    mask = (fft_freq >= low) & (fft_freq < high)
    energy = np.sum(fft_avg[mask]**2)
    energy_db = 10 * np.log10(energy + 1e-10)
    print(f"{label:<30} : {energy_db:6.1f} dB")

# Détecter la présence d'un signal autour de 1 kHz
center_freq = 1000
bandwidth = 200
mask = (fft_freq >= center_freq - bandwidth) & (fft_freq <= center_freq + bandwidth)
signal_1khz = np.max(fft_avg[mask])
noise_floor = np.median(fft_avg[(fft_freq > 5000) & (fft_freq < 10000)])
snr = 20 * np.log10(signal_1khz / (noise_floor + 1e-10))

print("\n" + "="*70)
print("DÉTECTION SIGNAL COSPAS-SARSAT:")
print("="*70)
print(f"Signal autour de 1 kHz: {signal_1khz:.0f}")
print(f"Plancher de bruit: {noise_floor:.0f}")
print(f"SNR estimé: {snr:.1f} dB")

if snr > 10:
    print("\n✅ Signal détecté autour de 1 kHz (probable signal COSPAS-SARSAT)")
else:
    print("\n⚠️  Signal faible ou absent autour de 1 kHz")

print("\n" + "="*70)
