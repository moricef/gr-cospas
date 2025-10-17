#!/usr/bin/env python3
"""
Test LFSR avec la correction selon T.018 Appendix D
Feedback = X0 ⊕ X18 (et non X22 ⊕ X17)
"""

def lfsr_t018_corrected(initial_state=0x000001, num_chips=64):
    """
    LFSR conforme T.018 Appendix D Figure D-1

    Algorithme:
    1. Output = X0 (LSB du registre)
    2. Feedback = X0 ⊕ X18
    3. Shift RIGHT: Xn → Xn-1
    4. Feedback → X22
    """
    state = initial_state
    output = []

    print(f"État initial: 0x{state:06X} = {state:023b}")
    print(f"\nRegistres: 22 21 20 19 18 17 16 15 14 13 12 11 10  9  8  7  6  5  4  3  2  1  0  Out")
    print("=" * 90)

    for i in range(num_chips):
        # Output = X0 (bit[0])
        output_bit = state & 1
        output.append(output_bit)

        # Feedback = X0 ⊕ X18 (bit[0] XOR bit[18])
        x0 = state & 1
        x18 = (state >> 18) & 1
        feedback = x0 ^ x18

        # Afficher les 10 premières itérations
        if i < 10:
            state_bits = f"{state:023b}"
            formatted = " ".join([state_bits[j] if j < 23 else " " for j in range(23)])
            print(f"{formatted}  {output_bit}")

        # Shift RIGHT et insérer feedback dans X22
        state = (state >> 1) | (feedback << 22)

        # Masque 23 bits
        state &= 0x7FFFFF

    return output


# Test avec l'état initial Normal I
print("="*90)
print("TEST LFSR CORRIGÉ - T.018 Appendix D Algorithm")
print("="*90)
print("Polynomial: G(x) = X²³ + X¹⁸ + 1")
print("Initial state: 0x000001 (Normal I)")
print("Feedback: X0 ⊕ X18\n")

prn_bits = lfsr_t018_corrected(0x000001, 64)

print("\n" + "="*90)
print("RÉSULTAT:")
print("="*90)

# Convertir en groupes hex de 16 bits
hex_groups = []
for i in range(0, 64, 16):
    chunk = prn_bits[i:i+16]
    value = 0
    for j, bit in enumerate(chunk):
        value |= (bit << (15 - j))  # MSB first
    hex_groups.append(f"{value:04X}")

result = " ".join(hex_groups)
expected = "8000 0108 4212 84A1"

print(f"Produit:  {result}")
print(f"Attendu:  {expected}")
print(f"\n{'✓ SUCCÈS' if result == expected else '✗ ÉCHEC'}")

# Vérification bit par bit des premiers chips
print("\n" + "="*90)
print("VÉRIFICATION DÉTAILLÉE (premiers 32 bits):")
print("="*90)

# Référence T.018 Table 2.2
reference_hex = [0x8000, 0x0108, 0x4212, 0x84A1]
reference_bits = []
for hex_val in reference_hex:
    for j in range(15, -1, -1):
        reference_bits.append((hex_val >> j) & 1)

errors = []
for i in range(min(32, len(prn_bits))):
    match = "✓" if prn_bits[i] == reference_bits[i] else "✗"
    if prn_bits[i] != reference_bits[i]:
        errors.append(i)
    if i < 32:
        print(f"Bit {i:2d}: Produit={prn_bits[i]}  Attendu={reference_bits[i]}  {match}")

if errors:
    print(f"\n✗ {len(errors)} erreur(s) aux positions: {errors}")
else:
    print(f"\n✓ Tous les {min(32, len(prn_bits))} premiers bits correspondent!")
