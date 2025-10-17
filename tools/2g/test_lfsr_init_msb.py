#!/usr/bin/env python3
"""
Test LFSR - État initial avec bit[22]=1 au lieu de bit[0]=1
"""

def hex_to_binary(hex_str):
    hex_clean = hex_str.replace(' ', '')
    val = int(hex_clean, 16)
    return format(val, '064b')

expected_hex = "8000 0108 4212 84A1"
expected_bin = hex_to_binary(expected_hex)

print("=" * 70)
print("Test LFSR - État initial 0x400000 (bit[22]=1)")
print("=" * 70)

configs = [
    ("SHIFT LEFT, output bit[22]", lambda s: (s >> 22) & 1, lambda s, fb: ((s << 1) & 0x7FFFFF) | fb, 0x400000),
    ("SHIFT LEFT, output bit[0]", lambda s: s & 1, lambda s, fb: ((s << 1) & 0x7FFFFF) | fb, 0x400000),
    ("SHIFT RIGHT, output bit[22]", lambda s: (s >> 22) & 1, lambda s, fb: (s >> 1) | (fb << 22), 0x400000),
    ("SHIFT RIGHT, output bit[0]", lambda s: s & 1, lambda s, fb: (s >> 1) | (fb << 22), 0x400000),
]

for name, get_output, shift_op, init_val in configs:
    print(f"\n{name}:")
    print(f"  Init: 0x{init_val:06X}")
    
    lfsr = init_val
    outputs = []

    for i in range(64):
        output_bit = get_output(lfsr)
        outputs.append(str(output_bit))

        feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
        lfsr = shift_op(lfsr, feedback) & 0x7FFFFF

    generated_bin = ''.join(outputs)
    
    if generated_bin == expected_bin:
        print(f"  ✓✓✓ MATCH PARFAIT !")
        print(f"  Séquence: {generated_bin[:32]}...")
    else:
        diff_count = sum(1 for g, e in zip(generated_bin, expected_bin) if g != e)
        print(f"  ✗ {diff_count} bits différents")
        print(f"  Obtenu : {generated_bin[:32]}...")
        print(f"  Attendu: {expected_bin[:32]}...")
