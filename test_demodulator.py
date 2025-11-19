#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Test du démodulateur BPSK COSPAS-SARSAT avec connexion à dec406
"""

import numpy as np
from gnuradio import gr, blocks
from gnuradio import cospas
import sys
import subprocess
import tempfile
import os

class test_demodulator(gr.top_block):
    def __init__(self, input_file, sample_rate=40000, debug=True):
        gr.top_block.__init__(self, "Test BPSK Demodulator")

        # Source: fichier I/Q complexe 32-bit float
        self.file_source = blocks.file_source(
            gr.sizeof_gr_complex,
            input_file,
            False  # No repeat
        )

        # Démodulateur BPSK COSPAS-SARSAT
        self.demodulator = cospas.cospas_sarsat_demodulator(
            sample_rate=sample_rate,
            debug_mode=debug
        )

        # Forcer le traitement d'un burst complet à la fois
        self.set_max_noutput_items(20800)  # 6400 + 14400 = burst complet

        # Sink: fichier de bits bruts (uint8: 0 ou 1)
        fd, self.bits_file_name = tempfile.mkstemp(suffix='.bits')
        os.close(fd)  # Fermer le file descriptor, GNU Radio va rouvrir le fichier

        self.file_sink = blocks.file_sink(
            gr.sizeof_char,  # uint8_t
            self.bits_file_name,
            False  # No append
        )

        # Connexions
        self.connect(self.file_source, self.demodulator)
        self.connect(self.demodulator, self.file_sink)

        print(f"[TEST] Fichier d'entrée: {input_file}")
        print(f"[TEST] Fichier de bits: {self.bits_file_name}")
        print(f"[TEST] Sample rate: {sample_rate} Hz")

    def get_bits_file(self):
        return self.bits_file_name


def bits_to_dec406_format(bits_file, output_file):
    """
    Convertit le fichier de bits bruts (0/1) en format texte pour dec406
    Sépare les trames (144 bits long / 112 bits court) et affiche chacune individuellement
    """
    # Lire tous les bits
    bits = np.fromfile(bits_file, dtype=np.uint8)

    print(f"\n[CONVERT] Bits lus: {len(bits)}")

    # Tailles de trames possibles
    LONG_FRAME = 144  # Trame longue
    SHORT_FRAME = 112  # Trame courte

    # Essayer de séparer les trames (long ou court)
    frame_num = 1
    pos = 0

    while pos < len(bits):
        remaining = len(bits) - pos

        # Détecter le type de trame (long ou court)
        if remaining >= LONG_FRAME:
            # Vérifier si c'est une trame longue complète
            frame_size = LONG_FRAME
            frame_type = "LONGUE"
            hex_width = 36
        elif remaining >= SHORT_FRAME:
            # Vérifier si c'est une trame courte complète
            frame_size = SHORT_FRAME
            frame_type = "COURTE"
            hex_width = 28
        else:
            # Trame incomplète
            frame_bits = bits[pos:]
            frame_str = ''.join(str(b) for b in frame_bits)
            print(f"\n[TRAME INCOMPLETE] {len(frame_bits)} bits:")
            print(f"  Bits: {frame_str}")
            break

        # Extraire la trame
        frame_bits = bits[pos:pos+frame_size]
        frame_str = ''.join(str(b) for b in frame_bits)

        # Convertir en hex pour affichage compact
        frame_hex = hex(int(frame_str, 2))[2:].upper().zfill(hex_width)

        print(f"\n[TRAME {frame_num}] {frame_type} - {frame_size} bits:")
        print(f"  Bits 1-15  (Preamble):  {frame_str[:15]}")
        print(f"  Bits 16-24 (Frame sync): {frame_str[15:24]}")

        if frame_size == LONG_FRAME:
            print(f"  Bits 25-144 (Message):   {frame_str[24:]}")
        else:  # SHORT_FRAME
            print(f"  Bits 25-112 (Message):   {frame_str[24:]}")

        print(f"  Hex: {frame_hex}")

        pos += frame_size
        frame_num += 1

    # Statistiques
    num_long = (len(bits) // LONG_FRAME) if len(bits) >= LONG_FRAME else 0
    num_short = ((len(bits) - num_long * LONG_FRAME) // SHORT_FRAME) if len(bits) > num_long * LONG_FRAME else 0

    print(f"\n[CONVERT] Trames longues (144 bits): {num_long}")
    print(f"[CONVERT] Trames courtes (112 bits): {num_short}")

    # Écrire en format texte (un caractère '0' ou '1' par bit)
    with open(output_file, 'w') as f:
        for bit in bits:
            f.write('1' if bit else '0')

    print(f"[CONVERT] Fichier texte créé: {output_file} ({len(bits)} bits)")
    return len(bits)


def call_dec406(bits_text_file):
    """
    Appelle dec406 avec le fichier de bits en entrée
    """
    dec406_path = "/home/fab2/Developpement/COSPAS-SARSAT/balise_406MHz/dec406_V10.2/build/dec406"

    if not os.path.exists(dec406_path):
        print(f"[ERROR] dec406 introuvable: {dec406_path}")
        return None

    print(f"\n[DEC406] Appel de dec406...")
    try:
        result = subprocess.run(
            [dec406_path, bits_text_file],
            capture_output=True,
            text=True,
            timeout=10
        )

        print("[DEC406] stdout:")
        print(result.stdout)

        if result.stderr:
            print("[DEC406] stderr:")
            print(result.stderr)

        return result.returncode

    except subprocess.TimeoutExpired:
        print("[ERROR] dec406 timeout")
        return -1
    except Exception as e:
        print(f"[ERROR] Erreur lors de l'appel dec406: {e}")
        return -1


def main():
    if len(sys.argv) < 2:
        print("Usage: ./test_demodulator.py <fichier_iq.raw> [sample_rate]")
        print("\nFichiers I/Q: format complexe 32-bit float (I+jQ)")
        print("Sample rate par défaut: 40000 Hz")
        sys.exit(1)

    input_file = sys.argv[1]
    sample_rate = int(sys.argv[2]) if len(sys.argv) > 2 else 40000

    if not os.path.exists(input_file):
        print(f"[ERROR] Fichier introuvable: {input_file}")
        sys.exit(1)

    # Créer et exécuter le flowgraph
    tb = test_demodulator(input_file, sample_rate, debug=True)

    print("\n[TEST] Démarrage du démodulateur...")
    tb.start()
    tb.wait()
    print("[TEST] Démodulation terminée")

    bits_file = tb.get_bits_file()

    # Convertir les bits en format texte
    bits_text_file = bits_file + ".txt"
    num_bits = bits_to_dec406_format(bits_file, bits_text_file)

    if num_bits > 0:
        # Appeler dec406 pour décoder
        call_dec406(bits_text_file)
    else:
        print("[WARNING] Aucun bit démodulé!")

    # Nettoyer
    print(f"\n[TEST] Fichiers temporaires:")
    print(f"  Bits bruts: {bits_file}")
    print(f"  Bits texte: {bits_text_file}")


if __name__ == '__main__':
    main()
