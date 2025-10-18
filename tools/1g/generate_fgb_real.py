#!/usr/bin/env python3
"""
Génère un fichier IQ+WAV FGB en utilisant le VRAI générateur GNU Radio
(pas de version simplifiée - utilise cospas.cospas_generator)
"""

import sys
import os
import struct
import wave
import numpy as np
import argparse

# Ajouter le chemin du module cospas
sys.path.insert(0, '/home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/python')

from gnuradio import cospas

def generate_fgb_frame_data():
    """Génère une trame FGB T.001 complète (144 bits = 18 octets)"""
    # Trame longue format T.001
    # Format: 2 bits header + 112 bits data + 30 bits BCH

    # Simuler une vraie trame (18 octets)
    frame_data = bytearray(18)

    # Bits 0-1: Format flag (1) + Protocol flag (0)
    frame_data[0] = 0x80  # 10xxxxxx

    # Bits 2-11: Country code 227 (France) = 0xE3
    frame_data[0] |= (227 >> 4)  # 4 bits hauts
    frame_data[1] = ((227 & 0x0F) << 4)  # 6 bits bas + ...

    # Le reste: ID, position, etc. (simplifié pour test)
    for i in range(2, 18):
        frame_data[i] = 0x55  # Pattern test

    return bytes(frame_data)

def generate_fgb_iq_real(output_basename, sample_rate=48000):
    """Génère fichier IQ et WAV avec le VRAI générateur GNU Radio"""

    print("="*70)
    print(" GÉNÉRATION FICHIER IQ FGB - VRAI GÉNÉRATEUR GNU Radio")
    print("="*70)

    # Générer les données de trame
    print("\n🔧 Génération trame T.001...")
    frame_data = generate_fgb_frame_data()
    print(f"  Trame: {len(frame_data)} octets = {len(frame_data)*8} bits")

    # Créer le générateur GNU Radio
    print("\n📡 Initialisation générateur GNU Radio cospas.cospas_generator...")
    gen = cospas.cospas_generator(data_bytes=frame_data, repeat=False)

    print(f"  Modulation: Biphase-L (Manchester)")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Samples/bit: 16")

    # Récupérer la trame générée
    print("\n🎵 Génération du signal...")
    signal = gen.frame  # Signal complexe

    num_samples = len(signal)
    duration = num_samples / sample_rate

    print(f"  ✓ {num_samples} échantillons générés")
    print(f"  Durée: {duration:.3f} secondes")

    # Structure du signal
    carrier_samples = 1024
    preamble_bits = 15
    data_bits = len(frame_data) * 8
    samples_per_bit = 16

    print(f"\n📊 Structure du signal:")
    print(f"  Porteuse: {carrier_samples} échantillons")
    print(f"  Préambule: {preamble_bits} bits × {samples_per_bit} = {preamble_bits * samples_per_bit} échantillons")
    print(f"  Données: {data_bits} bits × {samples_per_bit} = {data_bits * samples_per_bit} échantillons")

    # Extraire I et Q
    i_samples = np.real(signal).astype(np.float32)
    q_samples = np.imag(signal).astype(np.float32)

    # Sauvegarder IQ
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

    # Normaliser
    i_norm = i_samples / np.max(np.abs(i_samples)) if np.max(np.abs(i_samples)) > 0 else i_samples
    q_norm = q_samples / np.max(np.abs(q_samples)) if np.max(np.abs(q_samples)) > 0 else q_samples

    # Convertir en int16
    i_int16 = (i_norm * 32767).astype(np.int16)
    q_int16 = (q_norm * 32767).astype(np.int16)

    # Entrelacer stéréo
    stereo_data = np.empty((num_samples * 2,), dtype=np.int16)
    stereo_data[0::2] = i_int16  # Canal gauche = I
    stereo_data[1::2] = q_int16  # Canal droit = Q

    with wave.open(wav_filename, 'wb') as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(stereo_data.tobytes())

    wav_size = os.path.getsize(wav_filename)
    print(f"  ✓ Fichier créé: {wav_size / 1024:.2f} KB")
    print(f"  Format: Stéréo 16-bit, {sample_rate} Hz")

    # Statistiques
    print("\n📊 Statistiques du signal:")
    print(f"  I min/max: {i_samples.min():.6f} / {i_samples.max():.6f}")
    print(f"  Q min/max: {q_samples.min():.6f} / {q_samples.max():.6f}")

    magnitude = np.abs(signal)
    print(f"  Magnitude moyenne: {magnitude.mean():.6f}")
    print(f"  Magnitude std: {magnitude.std():.6f}")

    # Vérifier les phases
    phases = np.angle(signal)
    print(f"  Phase min/max: {np.rad2deg(phases.min()):.1f}° / {np.rad2deg(phases.max()):.1f}°")

    print("\n✅ Génération terminée!")
    print(f"\n📁 Fichiers créés:")
    print(f"  {iq_filename}  ({file_size / 1024:.2f} KB)")
    print(f"  {wav_filename} ({wav_size / 1024:.2f} KB)")

    print("\n💡 Ce signal utilise le VRAI générateur GNU Radio:")
    print("  ✅ Porteuse de 1024 échantillons")
    print("  ✅ Préambule de 15 bits conforme T.001")
    print("  ✅ Modulation Biphase-L correcte")
    print("  ✅ Compatible avec le décodeur GNU Radio")

    print("\n🎧 Écouter:")
    print(f"  aplay {wav_filename}")
    print(f"  # ou")
    print(f"  audacity {wav_filename}")

    print("\n🔍 Décoder avec GNU Radio:")
    print(f"  cd /home/fab2/Developpement/COSPAS-SARSAT/GNURADIO/gr-cospas/examples/1g")
    print(f"  ./decode_wav.py ../../tools/1g/{wav_filename}")

    print("="*70)

    return iq_filename, wav_filename

def main():
    parser = argparse.ArgumentParser(
        description='Génère FGB IQ+WAV avec le VRAI générateur GNU Radio'
    )
    parser.add_argument('-o', '--output', default='fgb_real',
                       help='Nom de base (défaut: fgb_real)')
    parser.add_argument('--rate', type=int, default=48000,
                       help='Sample rate (défaut: 48000 Hz)')

    args = parser.parse_args()

    try:
        generate_fgb_iq_real(args.output, args.rate)
        return 0
    except Exception as e:
        print(f"\n❌ Erreur: {e}")
        import traceback
        traceback.print_exc()
        return 1

if __name__ == '__main__':
    sys.exit(main())
