#!/usr/bin/env python3
"""
Test LFSR avec mapping INVERSÉ (comme le dsPIC33CK fait réellement)
"""

def test_lfsr_inverse_mapping():
    print("=" * 70)
    print("Test LFSR - Mapping INVERSÉ (dsPIC33CK réel)")
    print("=" * 70)
    print("\ndsPIC33CK ligne 200: sequence[i] = (lfsr & 1) ? 1 : -1")
    print("   → LSB=1 → Signal +1 (PAS -1 !)")
    print("   → LSB=0 → Signal -1")
    print("\nC'est l'INVERSE de la Table 2.3 T.018 !\n")

    lfsr = 0x000001
    chips = []

    for i in range(64):
        output_bit = lfsr & 1
        # Mapping dsPIC33CK RÉEL (inversé Table 2.3)
        chip = +1 if output_bit else -1
        chips.append(chip)

        if i < 8:
            print(f"Chip {i}: État=0x{lfsr:06X} | bit[0]={output_bit} → Signal={chip:+d}")

        feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
        lfsr = (lfsr >> 1) | (feedback << 22)
        lfsr &= 0x7FFFFF

    # Convertir signal → logic (avec mapping inversé)
    # Signal +1 → Logic 1, Signal -1 → Logic 0
    logic_bits = [1 if chip == +1 else 0 for chip in chips]

    hex_values = []
    for i in range(4):
        bits_16 = logic_bits[i*16:(i+1)*16]
        val = sum(b << (15-j) for j, b in enumerate(bits_16))
        hex_values.append(f"{val:04X}")

    print("\n" + "=" * 70)
    print(f"Séquence obtenue : {' '.join(hex_values)}")
    print(f"Séquence attendue: 8000 0108 4212 84A1")

    if hex_values == ["8000", "0108", "4212", "84A1"]:
        print("\n✓ MATCH ! Le dsPIC utilise un mapping INVERSÉ")
        return True
    else:
        print("\n✗ Toujours pas bon...")
        return False

if __name__ == "__main__":
    test_lfsr_inverse_mapping()
