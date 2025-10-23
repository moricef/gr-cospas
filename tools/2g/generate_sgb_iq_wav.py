#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur IQ + WAV pour Balises COSPAS-SARSAT 2G (SGB - Second Generation Beacon)

Génère un fichier IQ complexe et un fichier WAV stéréo à partir d'une trame T.018.
Utilise le générateur OQPSK validé dsPIC33CK.

Usage:
    ./generate_sgb_iq_wav.py -o output_base
    ./generate_sgb_iq_wav.py -f trame.txt -o test_sgb

Sortie:
    - output_base.iq  : Signal IQ complexe (float32, 384 kHz) - FORMAT NATIF PLUTO
    - output_base.wav : Signal WAV I/Q stéréo (16-bit, 48 kHz) - BASEBAND DATA, PAS AUDIO
"""

import numpy as np
import argparse
import sys
import os
import struct
import wave

# Ajouter le répertoire courant au path pour importer generate_oqpsk_iq
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

def read_frame_file(filepath):
    """
    Lit un fichier de trame et extrait la trame hex (ignore commentaires #)

    Args:
        filepath: Chemin du fichier

    Returns:
        str: Trame hex (63 caractères)
    """
    with open(filepath, 'r') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#'):
                # Supprimer espaces et tirets
                return line.replace(' ', '').replace('-', '')
    raise ValueError(f"Aucune trame hex trouvée dans {filepath}")

def generate_default_frame():
    """
    Génère une trame de test par défaut (EPIRB France, position Marseille)

    Returns:
        str: Trame hex T.018 (63 caractères = 252 bits)
    """
    # Trame test validée BCH
    # EPIRB France, TAC 12345, Serial 13398, Position: 42.85°N, 4.95°E
    return "0C0E7456390956CCD02799A2468ACF135787FFF00C02832000037707609BC0F"

def iq_to_wav_stereo(iq_samples, sample_rate_iq, sample_rate_wav=48000):
    """
    Convertit signal IQ en WAV stéréo avec rééchantillonnage

    Args:
        iq_samples: Échantillons IQ complexes (numpy array)
        sample_rate_iq: Fréquence échantillonnage IQ (400000 Hz)
        sample_rate_wav: Fréquence échantillonnage WAV (48000 Hz)

    Returns:
        tuple: (i_resampled, q_resampled) à sample_rate_wav
    """
    from scipy import signal as scipy_signal

    # Séparer I et Q
    i_samples = np.real(iq_samples)
    q_samples = np.imag(iq_samples)

    # Ratio de rééchantillonnage
    decim = int(sample_rate_iq / sample_rate_wav)  # 400000 / 48000 ≈ 8.33

    # Utiliser resample_poly pour rééchantillonnage de haute qualité
    # 400000 / 48000 = 125/15
    i_resampled = scipy_signal.resample_poly(i_samples, 3, 25)
    q_resampled = scipy_signal.resample_poly(q_samples, 3, 25)

    return i_resampled, q_resampled

def write_wav_stereo(filename, i_samples, q_samples, sample_rate=48000):
    """
    Écrit fichier WAV stéréo (I sur gauche, Q sur droite)

    Args:
        filename: Nom fichier WAV
        i_samples: Canal I (numpy array float)
        q_samples: Canal Q (numpy array float)
        sample_rate: Fréquence échantillonnage (défaut: 48000 Hz)
    """
    # Normaliser à [-1, 1]
    i_norm = i_samples / (np.max(np.abs(i_samples)) + 1e-10)
    q_norm = q_samples / (np.max(np.abs(q_samples)) + 1e-10)

    # Convertir en int16 (-32768 à 32767)
    i_int16 = (i_norm * 32767).astype(np.int16)
    q_int16 = (q_norm * 32767).astype(np.int16)

    # Entrelacer I et Q (LRLRLR...)
    stereo = np.empty(len(i_int16) * 2, dtype=np.int16)
    stereo[0::2] = i_int16  # Canal gauche (I)
    stereo[1::2] = q_int16  # Canal droit (Q)

    # Écrire WAV
    with wave.open(filename, 'wb') as wav:
        wav.setnchannels(2)      # Stéréo
        wav.setsampwidth(2)      # 16-bit
        wav.setframerate(sample_rate)
        wav.writeframes(stereo.tobytes())

    file_size = os.path.getsize(filename)
    print(f"  ✓ Fichier créé: {file_size / 1024:.2f} KB")
    print(f"  Format: Stéréo 16-bit, {sample_rate} Hz")

def main():
    parser = argparse.ArgumentParser(
        description='Générateur IQ + WAV COSPAS-SARSAT 2G (T.018)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Exemples:
  # Générer avec trame par défaut
  ./generate_sgb_iq_wav.py -o test_sgb

  # Générer depuis fichier trame
  ./generate_sgb_iq_wav.py -f test_frame_2g.txt -o beacon_sgb

  # Générer depuis trame hex directe
  ./generate_sgb_iq_wav.py -t 0C0E7456390956CCD02799A2468ACF... -o custom

Sortie:
  - {output}.iq  : Signal IQ complexe (384 kHz, float32) - Pour PlutoSDR
  - {output}.wav : I/Q baseband stéréo (48 kHz, int16) - Pour GNU Radio/SDR++
                   ⚠️  PAS du son audio ! Contient données I/Q pour analyse SDR
        """
    )

    parser.add_argument('-o', '--output', required=True,
                        help='Nom de base fichiers sortie (sans extension)')
    parser.add_argument('-f', '--frame-file',
                        help='Fichier contenant trame hex T.018')
    parser.add_argument('-t', '--trame',
                        help='Trame hex directe (63 caractères)')
    parser.add_argument('-s', '--sample-rate', type=int, default=384000,
                        help='Sample rate IQ (défaut: 384000 Hz, compatible PlutoSDR)')
    parser.add_argument('-w', '--wav-rate', type=int, default=48000,
                        help='Sample rate WAV (défaut: 48000 Hz)')
    parser.add_argument('-q', '--quiet', action='store_true',
                        help='Mode silencieux')

    args = parser.parse_args()

    if not args.quiet:
        print("=" * 70)
        print(" GÉNÉRATION FICHIER IQ + WAV SGB - COSPAS-SARSAT 2G")
        print("=" * 70)
        print()

    # Déterminer la trame à utiliser
    if args.trame:
        frame_hex = args.trame.replace(' ', '').replace('-', '')
        if not args.quiet:
            print(f"🔧 Trame fournie: {frame_hex[:32]}...")
    elif args.frame_file:
        frame_hex = read_frame_file(args.frame_file)
        if not args.quiet:
            print(f"📂 Trame depuis fichier: {args.frame_file}")
            print(f"   {frame_hex[:32]}...")
    else:
        frame_hex = generate_default_frame()
        if not args.quiet:
            print("🔧 Utilisation trame par défaut (EPIRB France, Marseille)")
            print(f"   {frame_hex[:32]}...")

    if not args.quiet:
        print()

    # Générer IQ avec generate_oqpsk_iq.py
    iq_filename = f"{args.output}.iq"

    if not args.quiet:
        print("📡 Génération signal IQ OQPSK...")

    # Importer et utiliser le générateur existant
    import generate_oqpsk_iq as gen

    # Générer le signal
    iq_samples = gen.generate_2g_iq_signal(frame_hex, args.sample_rate, verbose=not args.quiet)

    # Sauvegarder IQ
    with open(iq_filename, 'wb') as f:
        iq_samples.tofile(f)

    if not args.quiet:
        file_size = os.path.getsize(iq_filename)
        print(f"  ✓ Fichier créé: {file_size / 1024:.2f} KB")
        print(f"  Format: Complex float32 interleaved I/Q")
        print(f"  Échantillons: {len(iq_samples):,}")
        print(f"  Sample rate: {args.sample_rate} Hz")
        print(f"  Durée: {len(iq_samples) / args.sample_rate:.3f} s")
        print()

    # Convertir en WAV
    wav_filename = f"{args.output}.wav"

    if not args.quiet:
        print(f"🎵 Conversion en WAV stéréo ({args.wav_rate} Hz)...")

    i_wav, q_wav = iq_to_wav_stereo(iq_samples, args.sample_rate, args.wav_rate)
    write_wav_stereo(wav_filename, i_wav, q_wav, args.wav_rate)

    if not args.quiet:
        print()
        print("✅ Génération terminée!")
        print()
        print("📁 Fichiers créés:")
        iq_size = os.path.getsize(iq_filename)
        wav_size = os.path.getsize(wav_filename)
        print(f"  {iq_filename}  ({iq_size / 1024:.2f} KB)")
        print(f"  {wav_filename} ({wav_size / 1024:.2f} KB)")
        print()
        print("💡 Utilisation:")
        print()
        print("  ⚠️  IMPORTANT: Le fichier .wav contient des données I/Q baseband,")
        print("      PAS du son audio ! Si vous le jouez avec aplay/VLC,")
        print("      vous entendrez du bruit - c'est NORMAL.")
        print()
        print(f"  # Transmettre avec PlutoSDR (RECOMMANDÉ - utiliser .iq)")
        print(f"  iio_attr -C -d cf-ad9361-dds0 frequency 406037500")
        print(f"  cat {iq_filename} > /dev/iio:device2")
        print()
        print(f"  # Analyser avec GNU Radio Companion")
        print(f"  gnuradio-companion")
        print(f"  - Fichier IQ: File Source → Type: Complex, Rate: {args.sample_rate}")
        print(f"  - Fichier WAV: WAV File Source → Rate: {args.wav_rate} (I=Left, Q=Right)")
        print()
        print(f"  # Visualiser le spectre")
        print(f"  python3 visualize_iq.py {iq_filename}")
        print("=" * 70)

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\n⚠️  Interrompu par utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur: {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)
