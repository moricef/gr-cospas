#!/usr/bin/env python3
"""
Test EXACT de la configuration LSFR_code.txt lignes 40-55
"""

def hex_to_binary(hex_str):
    hex_clean = hex_str.replace(' ', '')
    val = int(hex_clean, 16)
    return format(val, '064b')

expected_hex = "8000 0108 4212 84A1"
expected_bin = hex_to_binary(expected_hex)

print("=" * 70)
print("Test configuration EXACTE LSFR_code.txt")
print("=" * 70)
print("\nCode C (lignes 42-46):")
print("  uint8_t output = (lfsr_i_state >> 22) & 1;  // MSB")
print("  uint32_t feedback = ((lfsr_i_state >> 22) ^ (lfsr_i_state >> 17)) & 1;")
print("  lfsr_i_state = ((lfsr_i_state << 1) | feedback) & LFSR_MASK;\n")

lfsr = 0x000001
outputs = []

print("Premiers états:")
for i in range(10):
    # Output depuis MSB (bit 22)
    output_bit = (lfsr >> 22) & 1
    outputs.append(str(output_bit))
    
    bit_22 = (lfsr >> 22) & 1
    bit_17 = (lfsr >> 17) & 1
    print(f"État {i}: 0x{lfsr:06X} | bit[22]={bit_22} bit[17]={bit_17} | output={output_bit}")
    
    # Feedback
    feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
    
    # Shift LEFT + feedback au LSB
    lfsr = ((lfsr << 1) | feedback) & 0x7FFFFF

# Compléter jusqu'à 64
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
    print("\n✓✓✓ SUCCÈS PARFAIT ! ✓✓✓")
    print("\nConfiguration validée LSFR_code.txt:")
    print("  - État initial: 0x000001")
    print("  - Output: bit[22] (MSB)")
    print("  - Shift: LEFT")
    print("  - Feedback: (bit[22] XOR bit[17]) → bit[0] (LSB)")
else:
    diff_count = sum(1 for g, e in zip(generated_bin, expected_bin) if g != e)
    print(f"\n✗ {diff_count} bits différents sur 64")
    
    # Afficher les premières différences
    for i, (g, e) in enumerate(zip(generated_bin, expected_bin)):
        if g != e:
            print(f"  Bit {i}: généré={g}, attendu={e}")
            if i >= 10:
                print("  ...")
                break
