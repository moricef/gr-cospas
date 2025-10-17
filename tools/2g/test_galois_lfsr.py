#\!/usr/bin/env python3
"""
Test LFSR Galois - Configuration alternative
"""

def hex_to_binary(hex_str):
    hex_clean = hex_str.replace(' ', '')
    val = int(hex_clean, 16)
    return format(val, '064b')

expected_hex = "8000 0108 4212 84A1"
expected_bin = hex_to_binary(expected_hex)

print("=" * 70)
print("Test LFSR Galois - x^23 + x^18 + 1")
print("=" * 70)

# Galois LFSR : les XOR sont appliqués à des positions spécifiques lors du shift
# Si on shift right et que le LSB est 1, on XOR les taps

lfsr = 0x000001
outputs = []

print("\nGalois LFSR (Shift RIGHT avec XOR conditionnel):")
print("10 premiers états:")

for i in range(10):
    # Output = LSB
    output_bit = lfsr & 1
    outputs.append(str(output_bit))
    
    print(f"{i}: 0x{lfsr:06X} ({lfsr:023b}) | LSB={output_bit}")
    
    # Galois: si LSB=1, XOR aux positions des taps
    if output_bit:
        # XOR aux positions 23 et 18 (indices 22 et 17)
        lfsr = (lfsr >> 1) ^ (1 << 22) ^ (1 << 17)
    else:
        lfsr = lfsr >> 1
    
    lfsr &= 0x7FFFFF

# Génération complète
lfsr = 0x000001
outputs = []
for i in range(64):
    output_bit = lfsr & 1
    outputs.append(str(output_bit))
    
    if output_bit:
        lfsr = (lfsr >> 1) ^ (1 << 22) ^ (1 << 17)
    else:
        lfsr = lfsr >> 1
    
    lfsr &= 0x7FFFFF

generated_bin = ''.join(outputs)

print("\n" + "=" * 70)
print(f"Généré : {generated_bin}")
print(f"Attendu: {expected_bin}")

if generated_bin == expected_bin:
    print("\n*** GALOIS LFSR - SOLUTION TROUVEE ***")
    print("\nConfiguration correcte:")
    print("  - Type: Galois LFSR")
    print("  - Polynome: x^23 + x^18 + 1")
    print("  - Etat initial: 0x000001")
    print("  - Output: LSB")
    print("  - Si LSB=1: shift right + XOR aux bits 22 et 17")
    print("  - Sinon: shift right seulement")
else:
    diff = sum(1 for g, e in zip(generated_bin, expected_bin) if g \!= e)
    print(f"\n✗ {diff} bits differents")
