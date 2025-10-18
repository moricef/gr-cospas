#!/usr/bin/env python3
"""
Génère un fichier IQ FGB (1G) et le convertit en WAV

Usage:
    ./generate_fgb_iq_wav.py -o output

Génère:
    - output.iq  (fichier IQ brut)
    - output.wav (fichier WAV stéréo I/Q)
"""

import sys
import os
import struct
import wave
import argparse
import numpy as np

# Ajouter le chemin du module cospas
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../python'))

from cospas.cospas_generator import CospasSarsatGenerator

def generate_fgb_iq(output_basename, sample_rate=48000):
    """Génère un fichier IQ FGB (1G BPSK)"""

    print("="*70)
    print(" GÉNÉRATION FICHIER IQ FGB (1ère génération)")
    print("="*70)

    # Créer le générateur
    print("\n📡 Configuration:")
    print(f"  Modulation: Biphase-L (Manchester BPSK)")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Data rate: 400 bps")

    generator = CospasSarsatGenerator(sample_rate=sample_rate)

    # Générer le signal (trame longue 144 bits par défaut)
    print("\n🔧 Génération du signal...")
    samples = generator.generate()

    num_samples = len(samples)
    duration = num_samples / sample_rate

    print(f"  ✓ {num_samples} échantillons générés")
    print(f"  Durée: {duration:.3f} secondes")

    # Les samples sont en float complexe (I + jQ)
    # Pour FGB/1G, c'est du BPSK donc Q=0
    i_samples = np.real(samples).astype(np.float32)
    q_samples = np.imag(samples).astype(np.float32)

    # Sauvegarder en fichier IQ (format interleaved float32)
    iq_filename = f"{output_basename}.iq"
    print(f"\n💾 Sauvegarde fichier IQ: {iq_filename}")

    with open(iq_filename, 'wb') as f:
        for i in range(num_samples):
            f.write(struct.pack('f', i_samples[i]))
            f.write(struct.pack('f', q_samples[i]))

    file_size = os.path.getsize(iq_filename)
    print(f"  ✓ Fichier créé: {file_size / 1024:.2f} KB")
    print(f"  Format: Complex float32 interleaved I/Q")

    # Convertir en WAV
    wav_filename = f"{output_basename}.wav"
    print(f"\n🎵 Conversion en WAV: {wav_filename}")

    # Normaliser à ±1.0
    i_norm = i_samples / np.max(np.abs(i_samples)) if np.max(np.abs(i_samples)) > 0 else i_samples
    q_norm = q_samples / np.max(np.abs(q_samples)) if np.max(np.abs(q_samples)) > 0 else q_samples

    # Convertir en int16
    i_int16 = (i_norm * 32767).astype(np.int16)
    q_int16 = (q_norm * 32767).astype(np.int16)

    # Entrelacer pour stéréo
    stereo_data = np.empty((num_samples * 2,), dtype=np.int16)
    stereo_data[0::2] = i_int16  # Canal gauche = I
    stereo_data[1::2] = q_int16  # Canal droit = Q

    # Écrire WAV
    with wave.open(wav_filename, 'wb') as wav_file:
        wav_file.setnchannels(2)  # Stéréo
        wav_file.setsampwidth(2)  # 16 bits
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(stereo_data.tobytes())

    wav_size = os.path.getsize(wav_filename)
    print(f"  ✓ Fichier créé: {wav_size / 1024:.2f} KB")
    print(f"  Format: Stéréo 16-bit, {sample_rate} Hz")

    # Statistiques
    print("\n📊 Statistiques du signal:")
    print(f"  I min/max: {i_samples.min():.6f} / {i_samples.max():.6f}")
    print(f"  Q min/max: {q_samples.min():.6f} / {q_samples.max():.6f}")

    magnitude = np.sqrt(i_samples**2 + q_samples**2)
    print(f"  Magnitude moyenne: {magnitude.mean():.6f}")
    print(f"  Magnitude std: {magnitude.std():.6f}")

    print("\n✅ Génération terminée!")
    print(f"\n📁 Fichiers créés:")
    print(f"  {iq_filename}  ({file_size / 1024:.2f} KB)")
    print(f"  {wav_filename} ({wav_size / 1024:.2f} KB)")

    print("\n💡 Utilisation:")
    print(f"  # Écouter (après downsampling si nécessaire)")
    print(f"  sox {wav_filename} -r 48000 audio.wav")
    print(f"")
    print(f"  # Analyser avec Audacity")
    print(f"  audacity {wav_filename}")
    print(f"")
    print(f"  # Analyser avec script Python")
    print(f"  python3 ../examples/1g/analyze_wav.py {wav_filename}")

    print("="*70)

    return iq_filename, wav_filename

def main():
    parser = argparse.ArgumentParser(
        description='Génère un fichier IQ FGB (1G) et le convertit en WAV',
        formatter_class=argparse.RawDescriptionHelpFormatter
    )

    parser.add_argument('-o', '--output', default='fgb_signal',
                       help='Nom de base pour les fichiers de sortie (sans extension)')
    parser.add_argument('--rate', type=int, default=48000,
                       help='Sample rate (défaut: 48000 Hz)')

    args = parser.parse_args()

    try:
        generate_fgb_iq(args.output, args.rate)
        return 0
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
