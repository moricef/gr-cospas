#!/usr/bin/env python3
"""
Test LFSR Fibonacci standard - Polynôme x^23 + x^18 + 1
"""

def hex_to_binary(hex_str):
    hex_clean = hex_str.replace(' ', '')
    val = int(hex_clean, 16)
    return format(val, '064b')

expected_hex = "8000 0108 4212 84A1"
expected_bin = hex_to_binary(expected_hex)

print("=" * 70)
print("Test LFSR Fibonacci - x^23 + x^18 + 1")
print("=" * 70)

# Fibonacci LFSR : feedback calculé depuis taps, injecté en bit[0]
# Taps aux positions 23 et 18 → indices 22 et 17
print("\nFibonacci LFSR:")
print("  - Taps: bit[22] et bit[17]")
print("  - Output: bit[22] (MSB)")
print("  - Feedback: bit[22] XOR bit[17] → injecté en bit[0]")
print("  - Shift: LEFT (vers MSB)")

lfsr = 0x000001
outputs = []

print("\n10 premiers états:")
for i in range(10):
    # Output = MSB
    output_bit = (lfsr >> 22) & 1
    outputs.append(str(output_bit))
    
    # Feedback = XOR des taps
    tap_22 = (lfsr >> 22) & 1
    tap_17 = (lfsr >> 17) & 1
    feedback = tap_22 ^ tap_17
    
    print(f"{i}: 0x{lfsr:06X} ({lfsr:023b}) | taps=[{tap_22},{tap_17}] fb={feedback} out={output_bit}")
    
    # Shift left, inject feedback at LSB
    lfsr = ((lfsr << 1) | feedback) & 0x7FFFFF

# Génération complète
lfsr = 0x000001
outputs = []
for i in range(64):
    output_bit = (lfsr >> 22) & 1
    outputs.append(str(output_bit))
    feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
    lfsr = ((lfsr << 1) | feedback) & 0x7FFFFF

generated_bin = ''.join(outputs)

print("\n" + "=" * 70)
print(f"Généré : {generated_bin}")
print(f"Attendu: {expected_bin}")

if generated_bin == expected_bin:
    print("\n✓✓✓ SOLUTION TROUVÉE !")
else:
    diff = sum(1 for g, e in zip(generated_bin, expected_bin) if g != e)
    print(f"\n✗ {diff} bits différents")
    
    # Test inversion complète
    inverted = ''.join('1' if b == '0' else '0' for b in generated_bin)
    if inverted == expected_bin:
        print("\n⚠️  La séquence INVERSÉE correspond !")
