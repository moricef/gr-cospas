#!/usr/bin/env python3
"""
Génère un fichier IQ+WAV FGB simple (sans GNU Radio)
Modulation Biphase-L (Manchester) T.001
"""

import sys
import os
import struct
import wave
import numpy as np
import argparse

def manchester_encode(bits):
    """Encode en Biphase-L (Manchester): 0→01, 1→10"""
    encoded = []
    for bit in bits:
        if bit == 0:
            encoded.extend([0, 1])  # 0 → transition bas→haut
        else:
            encoded.extend([1, 0])  # 1 → transition haut→bas
    return encoded

def generate_fgb_frame():
    """Génère une trame FGB (1G) de 144 bits"""
    # Trame simplifiée pour test
    # Format T.001: Preamble + data + CRC

    # Preamble (24 bits): alternance 010101...
    preamble = [0, 1] * 12  # 24 bits

    # Data (112 bits) - exemple simplifié
    # Bits 0-14: Format flag + protocol flag + country code
    data = [1, 0]  # Format + Protocol
    data += [0, 1, 1, 1, 0, 0, 0, 1, 1, 1]  # Country code 227 (France)

    # Compléter avec des zéros pour 112 bits au total
    while len(data) < 112:
        data.append(0)

    # CRC (8 bits) - simplifié pour test
    crc = [1, 0, 1, 0, 1, 0, 1, 0]

    frame = preamble + data + crc
    return frame

def modulate_bpsk(manchester_bits, samples_per_bit=120):
    """Modulation BPSK: 0→-1, 1→+1"""
    signal = []
    for bit in manchester_bits:
        value = 1.0 if bit == 1 else -1.0
        signal.extend([value] * samples_per_bit)
    return np.array(signal, dtype=np.float32)

def generate_fgb_iq(output_basename, sample_rate=48000):
    """Génère fichier IQ et WAV pour FGB"""

    print("="*70)
    print(" GÉNÉRATION FICHIER IQ FGB (1ère génération - simplifié)")
    print("="*70)

    # Générer la trame
    print("\n🔧 Génération trame T.001...")
    frame_bits = generate_fgb_frame()
    print(f"  Trame: {len(frame_bits)} bits")

    # Encoder en Manchester (Biphase-L)
    print("\n🔄 Encodage Biphase-L (Manchester)...")
    manchester_bits = manchester_encode(frame_bits)
    print(f"  Manchester: {len(manchester_bits)} chips")

    # Moduler en BPSK
    bit_rate = 400  # 400 bps
    samples_per_bit = sample_rate // bit_rate  # 48000/400 = 120 samples/bit

    print(f"\n📡 Modulation BPSK:")
    print(f"  Sample rate: {sample_rate} Hz")
    print(f"  Bit rate: {bit_rate} bps")
    print(f"  Samples/bit: {samples_per_bit}")

    i_samples = modulate_bpsk(manchester_bits, samples_per_bit)
    q_samples = np.zeros_like(i_samples)  # BPSK → Q=0

    num_samples = len(i_samples)
    duration = num_samples / sample_rate

    print(f"  ✓ {num_samples} échantillons générés")
    print(f"  Durée: {duration:.3f} secondes")

    # Sauvegarder IQ
    iq_filename = f"{output_basename}.iq"
    print(f"\n💾 Sauvegarde fichier IQ: {iq_filename}")

    with open(iq_filename, 'wb') as f:
        for i in range(num_samples):
            f.write(struct.pack('f', i_samples[i]))
            f.write(struct.pack('f', q_samples[i]))

    file_size = os.path.getsize(iq_filename)
    print(f"  ✓ Fichier créé: {file_size / 1024:.2f} KB")

    # Convertir en WAV
    wav_filename = f"{output_basename}.wav"
    print(f"\n🎵 Conversion en WAV: {wav_filename}")

    # Convertir en int16
    i_int16 = (i_samples * 32767).astype(np.int16)
    q_int16 = (q_samples * 32767).astype(np.int16)

    # Entrelacer
    stereo_data = np.empty((num_samples * 2,), dtype=np.int16)
    stereo_data[0::2] = i_int16
    stereo_data[1::2] = q_int16

    with wave.open(wav_filename, 'wb') as wav_file:
        wav_file.setnchannels(2)
        wav_file.setsampwidth(2)
        wav_file.setframerate(sample_rate)
        wav_file.writeframes(stereo_data.tobytes())

    wav_size = os.path.getsize(wav_filename)
    print(f"  ✓ Fichier créé: {wav_size / 1024:.2f} KB")

    print("\n✅ Génération terminée!")
    print(f"\n📁 Fichiers créés:")
    print(f"  {iq_filename}  ({file_size / 1024:.2f} KB)")
    print(f"  {wav_filename} ({wav_size / 1024:.2f} KB)")

    print("\n💡 Le signal FGB (BPSK) est AUDIBLE car:")
    print("  • Bit rate: 400 Hz (dans la bande audio)")
    print("  • Manchester doubleé: 800 Hz effectif")
    print("  • Tu devrais entendre des bips courts!")

    print("\n🎧 Écouter:")
    print(f"  aplay {wav_filename}")
    print(f"  # ou")
    print(f"  audacity {wav_filename}")

    print("="*70)

    return iq_filename, wav_filename

def main():
    parser = argparse.ArgumentParser(description='Génère FGB IQ+WAV simple')
    parser.add_argument('-o', '--output', default='fgb_test',
                       help='Nom de base (défaut: fgb_test)')
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
