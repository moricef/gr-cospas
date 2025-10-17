#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Générateur de Séquences PN pour COSPAS-SARSAT 2G
=================================================

Génère les séquences PN I et Q selon la spécification C/S T.018.
Implémentation identique au code dsPIC33CK validé.

Polynôme générateur : x^23 + x^18 + 1
États initiaux (Table 2.2 T.018) :
    - Normal I : 0x000001
    - Normal Q : 0x1AC3FC (d'après Table 2.2, pas 0x000041)

Références:
    - C/S T.018 Rev.12 Oct 2024, Section 2.2.3, Table 2.2, Figure 2-2
    - Code dsPIC33CK validé (system_comms.c)
"""

import numpy as np


def generate_prn_sequence_i(length=38400):
    """
    Génère la séquence PRN I selon T.018 Table 2.2.

    Implémentation identique au code dsPIC33CK qui fonctionne.
    LFSR x^23 + x^18 + 1, taps aux bits 22 et 17.

    Args:
        length: Nombre de chips à générer (38400 par défaut)

    Returns:
        np.array de {0, 1} représentant les chips
    """
    # État initial I d'après T.018 Table 2.2
    lfsr = 0x000001

    sequence = np.zeros(length, dtype=np.uint8)

    for i in range(length):
        # Sortie = LSB
        sequence[i] = lfsr & 1

        # Feedback = bit[22] XOR bit[17]
        # (taps du polynôme x^23 + x^18 + 1 pour registre 23 bits)
        feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1

        # Shift right et insérer feedback au MSB
        lfsr = (lfsr >> 1) | (feedback << 22)

        # Masquer pour garder 23 bits
        lfsr &= 0x7FFFFF

    return sequence


def generate_prn_sequence_q(length=38400):
    """
    Génère la séquence PRN Q selon T.018 Table 2.2.

    Args:
        length: Nombre de chips à générer (38400 par défaut)

    Returns:
        np.array de {0, 1} représentant les chips
    """
    # État initial Q d'après T.018 Table 2.2
    # Bits (MSB→LSB): 0 0 1 1 0 1 0 1 1 0 0 0 0 0 1 1 1 1 1 1 1 0 0
    # En hex: 0x1AC3FC
    lfsr = 0x1AC3FC

    sequence = np.zeros(length, dtype=np.uint8)

    for i in range(length):
        sequence[i] = lfsr & 1
        feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
        lfsr = (lfsr >> 1) | (feedback << 22)
        lfsr &= 0x7FFFFF

    return sequence


def bits_to_hex(bits, bits_per_group=16):
    """
    Convertit un array de bits en chaîne hexadécimale.

    Args:
        bits: np.array de bits (0 ou 1)
        bits_per_group: Nombre de bits par groupe hex (défaut 16 = 4 chars hex)

    Returns:
        Liste de chaînes hexadécimales
    """
    hex_values = []
    for i in range(0, len(bits), bits_per_group):
        chunk = bits[i:i+bits_per_group]
        if len(chunk) < bits_per_group:
            chunk = np.pad(chunk, (0, bits_per_group - len(chunk)), constant_values=0)

        # Convertir en entier (MSB first)
        value = 0
        for bit in chunk:
            value = (value << 1) | bit

        hex_values.append(f"{value:04X}")

    return hex_values


def validate_sequences():
    """
    Valide les séquences générées contre T.018 Table 2.2.

    Valeurs de référence (64 premiers chips) :
        PRN_I : 8000 0108 4212 84A1
        PRN_Q : 3F83 58BA D030 F231

    Returns:
        True si validation réussie, False sinon
    """
    print("=" * 70)
    print("  Validation des Séquences PN COSPAS-SARSAT 2G")
    print("  Référence : T.018 Rev.12 Oct 2024, Table 2.2")
    print("=" * 70)
    print()

    # Générer les 64 premiers chips
    pn_i = generate_prn_sequence_i(64)
    pn_q = generate_prn_sequence_q(64)

    # Convertir en hex
    hex_i = bits_to_hex(pn_i, 16)
    hex_q = bits_to_hex(pn_q, 16)

    # Valeurs de référence T.018 Table 2.2
    expected_i = ['8000', '0108', '4212', '84A1']
    expected_q = ['3F83', '58BA', 'D030', 'F231']

    print("PRN_I (64 premiers chips) :")
    print(f"  Généré  : {' '.join(hex_i)}")
    print(f"  Attendu : {' '.join(expected_i)}")

    match_i = (hex_i == expected_i)
    print(f"  Status  : {'✓ VALIDÉ' if match_i else '✗ ERREUR'}")
    print()

    print("PRN_Q (64 premiers chips) :")
    print(f"  Généré  : {' '.join(hex_q)}")
    print(f"  Attendu : {' '.join(expected_q)}")

    match_q = (hex_q == expected_q)
    print(f"  Status  : {'✓ VALIDÉ' if match_q else '✗ ERREUR'}")
    print()

    if match_i and match_q:
        print("=" * 70)
        print("  ✓ SÉQUENCES PN VALIDÉES AVEC SUCCÈS !")
        print("  Conformité T.018 Table 2.2 : 100%")
        print("=" * 70)
        return True
    else:
        print("=" * 70)
        print("  ✗ ERREUR : Séquences PN ne correspondent pas aux références")
        print("=" * 70)
        return False


def main():
    """Test et validation des séquences PN."""

    # Valider les séquences
    if not validate_sequences():
        return 1

    print()
    print("Génération de séquences complètes pour trame 2G...")
    print("  - Durée trame : 1 seconde")
    print("  - Bits total : 300 (150 I + 150 Q)")
    print("  - Chips/bit : 256")
    print("  - Chips total/canal : 38400")
    print()

    # Générer les séquences complètes (38400 chips par canal)
    pn_i = generate_prn_sequence_i(38400)
    pn_q = generate_prn_sequence_q(38400)

    print(f"✓ Séquence PRN_I : {len(pn_i)} chips générés")
    print(f"✓ Séquence PRN_Q : {len(pn_q)} chips générés")
    print()

    # Sauvegarder les séquences
    output_file_i = "pn_sequence_i.npy"
    output_file_q = "pn_sequence_q.npy"

    np.save(output_file_i, pn_i)
    np.save(output_file_q, pn_q)

    print(f"✓ Séquences sauvegardées :")
    print(f"  - {output_file_i}")
    print(f"  - {output_file_q}")
    print()
    print("Les séquences peuvent maintenant être utilisées par generate_oqpsk_iq.py")

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
