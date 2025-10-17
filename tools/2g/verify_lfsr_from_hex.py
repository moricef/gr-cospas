#!/usr/bin/env python3
"""
Vérifier LFSR en reconstruisant depuis le hex attendu
"""

def hex_to_binary_string(hex_str):
    """Convertit hex en chaîne binaire"""
    hex_clean = hex_str.replace(' ', '')
    val = int(hex_clean, 16)
    return format(val, '064b')

# Séquence attendue T.018 Table 2.2
expected_hex = "8000 0108 4212 84A1"
expected_bin = hex_to_binary_string(expected_hex)

print("=" * 70)
print("Reconstruction séquence depuis T.018 Table 2.2")
print("=" * 70)
print(f"\nHex attendu: {expected_hex}")
print(f"Binaire: {expected_bin}")
print(f"Bits (liste): [{', '.join(expected_bin)}]")

# Afficher par groupes de 16
print("\nPar groupes de 16 bits:")
for i in range(4):
    bits = expected_bin[i*16:(i+1)*16]
    val = int(bits, 2)
    print(f"  Bits {i*16:2d}-{i*16+15:2d}: {bits} = 0x{val:04X}")

# Maintenant testons si notre LFSR peut générer cette séquence
print("\n" + "=" * 70)
print("Test génération LFSR")
print("=" * 70)

lfsr = 0x000001
outputs = []

for i in range(64):
    output_bit = lfsr & 1
    outputs.append(str(output_bit))
    
    feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
    lfsr = ((lfsr << 1) & 0x7FFFFF) | feedback

generated_bin = ''.join(outputs)
print(f"\nGénéré : {generated_bin}")
print(f"Attendu: {expected_bin}")

if generated_bin == expected_bin:
    print("\n✓✓✓ PARFAIT ! Le LFSR génère la séquence correcte !")
    print("\nConfiguration validée:")
    print("  - État initial: 0x000001")
    print("  - Output: bit[0] (LSB)")
    print("  - Shift: LEFT")
    print("  - Feedback: (bit[22] XOR bit[17]) → LSB")
else:
    print("\n✗ La séquence ne correspond pas")
    # Comparer bit par bit
    diff_count = 0
    for i, (gen, exp) in enumerate(zip(generated_bin, expected_bin)):
        if gen != exp:
            diff_count += 1
            if diff_count <= 10:  # Afficher les 10 premières différences
                print(f"  Bit {i}: généré={gen}, attendu={exp}")
    print(f"\nTotal: {diff_count} bits différents sur 64")
