#!/usr/bin/env python3
"""
Test LFSR - SHIFT RIGHT (comme dsPIC mistral_bizarre.txt ligne 48-53)
"""

def hex_to_binary(hex_str):
    hex_clean = hex_str.replace(' ', '')
    val = int(hex_clean, 16)
    return format(val, '064b')

expected_hex = "8000 0108 4212 84A1"
expected_bin = hex_to_binary(expected_hex)

print("=" * 70)
print("Test LFSR - SHIFT RIGHT (dsPIC mistral_bizarre.txt)")
print("=" * 70)
print("\nConfiguration:")
print("  - Output: bit[0] (LSB)")
print("  - Feedback: (bit[22] XOR bit[17])")
print("  - Shift: RIGHT")
print("  - Feedback injecté au MSB (bit 22)\n")

lfsr = 0x000001
outputs = []

for i in range(64):
    # Output = LSB
    output_bit = lfsr & 1
    outputs.append(str(output_bit))

    if i < 8:
        bit_22 = (lfsr >> 22) & 1
        bit_17 = (lfsr >> 17) & 1
        print(f"État {i}: 0x{lfsr:06X} | bit[22]={bit_22} bit[17]={bit_17} bit[0]={output_bit}")

    # Feedback
    feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
    
    # Shift RIGHT + feedback → MSB
    lfsr = (lfsr >> 1) | (feedback << 22)
    lfsr &= 0x7FFFFF

    if i < 8:
        print(f"        feedback={feedback} → 0x{lfsr:06X}\n")

generated_bin = ''.join(outputs)

print("=" * 70)
print(f"Généré : {generated_bin}")
print(f"Attendu: {expected_bin}")

if generated_bin == expected_bin:
    print("\n✓✓✓ SUCCÈS TOTAL ! ✓✓✓")
    print("\nConfiguration CORRECTE:")
    print("  - État initial: 0x000001")
    print("  - Output depuis: bit[0] (LSB)")
    print("  - Direction: SHIFT RIGHT")
    print("  - Feedback: (bit[22] XOR bit[17]) → bit[22] (MSB)")
else:
    print("\n✗ Échec - différences détectées")
    diff_count = sum(1 for g, e in zip(generated_bin, expected_bin) if g != e)
    print(f"Total: {diff_count} bits différents sur 64")
