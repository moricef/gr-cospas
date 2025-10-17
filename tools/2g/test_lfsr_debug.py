#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test LFSR T.018 - Reproduction exacte du code dsPIC33CK
========================================================

Ce script reproduit EXACTEMENT le code C du dsPIC33CK pour comprendre
pourquoi la validation échoue.

Référence: system_comms.c:245-252 (dsPIC33CK validé)
"""

def test_lfsr_dspic_exact():
    """
    Reproduction EXACTE du code C dsPIC33CK (validé sur hardware).
    """
    print("=" * 70)
    print("Test LFSR - Reproduction exacte dsPIC33CK")
    print("=" * 70)

    # État initial T.018 Table 2.2 (Normal I)
    lfsr_i = 0x000001

    print(f"\nÉtat initial: 0x{lfsr_i:06X} (binaire: {lfsr_i:023b})")
    print(f"  bit 22 = {(lfsr_i >> 22) & 1}")
    print(f"  bit 17 = {(lfsr_i >> 17) & 1}")
    print(f"  bit 0  = {lfsr_i & 1}\n")

    # Générer les 64 premiers chips
    test_seq = []

    for i in range(64):
        # Table 2.3: 1→-1, 0→+1
        chip = -1 if (lfsr_i & 1) else 1
        test_seq.append(chip)

        # Afficher les 8 premiers états en détail
        if i < 8:
            output_bit = lfsr_i & 1
            bit_22 = (lfsr_i >> 22) & 1
            bit_17 = (lfsr_i >> 17) & 1

            print(f"Chip {i:2d}: État=0x{lfsr_i:06X} | "
                  f"bit[22]={bit_22} bit[17]={bit_17} bit[0]={output_bit} | "
                  f"Output={output_bit} → Signal={chip:+d}")

        # LFSR feedback: x^23 + x^18 + 1 (taps at bits 22 and 17)
        feedback = ((lfsr_i >> 22) ^ (lfsr_i >> 17)) & 1
        lfsr_i = (lfsr_i >> 1) | (feedback << 22)
        lfsr_i &= 0x7FFFFF  # Mask for 23 bits

        if i < 8:
            print(f"          feedback={feedback} → Nouvel état=0x{lfsr_i:06X}\n")

    # Convertir signal levels (-1,+1) en logic bits (1,0)
    logic_bits = [1 if chip == -1 else 0 for chip in test_seq]

    # Convertir en hex (4 groupes de 16 bits)
    hex_values = []
    for i in range(4):
        bits_16 = logic_bits[i*16:(i+1)*16]
        val = sum(b << (15-j) for j, b in enumerate(bits_16))
        hex_values.append(f"{val:04X}")

    print("\n" + "=" * 70)
    print("Résultat:")
    print("=" * 70)
    print(f"Séquence obtenue : {' '.join(hex_values)}")
    print(f"Séquence attendue: 8000 0108 4212 84A1 (T.018 Table 2.2)")

    # Vérification
    expected = ["8000", "0108", "4212", "84A1"]
    if hex_values == expected:
        print("\n✓ CONFORME T.018 Table 2.2")
        return True
    else:
        print("\n✗ NON CONFORME")
        # Afficher les différences
        for i, (got, exp) in enumerate(zip(hex_values, expected)):
            if got != exp:
                print(f"  Groupe {i}: attendu {exp}, obtenu {got}")
        return False

def test_lfsr_appendix_d():
    """
    Test en suivant EXACTEMENT l'Appendix D T.018.

    L'Appendix D montre les états successifs du registre.
    Essayons de reproduire la table.
    """
    print("\n" + "=" * 70)
    print("Test LFSR - Selon Appendix D T.018")
    print("=" * 70)

    # État initial (ligne 21 Appendix D)
    # Registre: bit22...bit0 = "0000 0000 0000 0000 0000 001"
    lfsr = 0x000001

    print("\nReproduction Table Appendix D:")
    print("État | bit[22..0] (hex) | bit[0] | Feedback | Next")
    print("-" * 70)

    for i in range(10):
        output = lfsr & 1
        bit_22 = (lfsr >> 22) & 1
        bit_17 = (lfsr >> 17) & 1
        feedback = bit_22 ^ bit_17

        print(f"{i:4d} | 0x{lfsr:06X}         | {output}      | {feedback}        |", end="")

        # Shift right + feedback MSB
        lfsr = (lfsr >> 1) | (feedback << 22)
        lfsr &= 0x7FFFFF

        print(f" 0x{lfsr:06X}")

    print("\nObservation: Avec état initial 0x000001:")
    print("  - bit[22]=0, bit[17]=0 → feedback=0")
    print("  - Après shift: 0x000000")
    print("  - LFSR meurt (reste bloqué à 0) !")

def test_alternative_feedback():
    """
    Tester des configurations alternatives de feedback.
    """
    print("\n" + "=" * 70)
    print("Test configurations alternatives")
    print("=" * 70)

    # Hypothèse 1: Feedback avec XOR de l'output
    print("\n1. Feedback = bit[22] ^ bit[17] ^ output")
    lfsr = 0x000001
    chips = []

    for i in range(8):
        output = lfsr & 1
        feedback = ((lfsr >> 22) ^ (lfsr >> 17) ^ output) & 1
        chips.append(1 if output else 0)

        print(f"  État {i}: 0x{lfsr:06X} | out={output} fb={feedback} →", end="")

        lfsr = (lfsr >> 1) | (feedback << 22)
        lfsr &= 0x7FFFFF

        print(f" 0x{lfsr:06X}")

    val = sum(b << (7-j) for j, b in enumerate(chips))
    print(f"  Premier octet: 0x{val:02X} (attendu: 0x80)")

    # Hypothèse 2: Shift LEFT au lieu de RIGHT
    print("\n2. Shift LEFT (Appendix D visuel)")
    lfsr = 0x000001
    chips = []

    for i in range(8):
        output = lfsr & 1
        feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
        chips.append(1 if output else 0)

        print(f"  État {i}: 0x{lfsr:06X} | out={output} fb={feedback} →", end="")

        # Shift LEFT + feedback LSB
        lfsr = ((lfsr << 1) & 0x7FFFFF) | feedback

        print(f" 0x{lfsr:06X}")

    val = sum(b << (7-j) for j, b in enumerate(chips))
    print(f"  Premier octet: 0x{val:02X} (attendu: 0x80)")

if __name__ == "__main__":
    # Test 1: Reproduction exacte dsPIC
    test_lfsr_dspic_exact()

    # Test 2: Appendix D
    test_lfsr_appendix_d()

    # Test 3: Alternatives
    test_alternative_feedback()

    print("\n" + "=" * 70)
    print("Conclusion")
    print("=" * 70)
    print("""
Le code dsPIC33CK utilise:
    feedback = (bit[22] ^ bit[17]) & 1
    lfsr = (lfsr >> 1) | (feedback << 22)

Avec état initial 0x000001, le LFSR devrait mourir (rester à 0).

MAIS le dsPIC est VALIDÉ sur hardware et fonctionne !

HYPOTHÈSES:
1. Le code C montré n'est pas celui qui s'exécute vraiment
2. Il y a une initialisation différente avant la génération
3. Le feedback est calculé différemment dans le code réel
4. L'Appendix D montre une configuration Galois différente

ACTION: Vérifier le code complet du dsPIC, notamment l'initialisation
dans generate_prn_sequence_i() ligne 187-211.
""")
