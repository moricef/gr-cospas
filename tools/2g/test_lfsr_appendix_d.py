#!/usr/bin/env python3
"""
Test LFSR - Configuration EXACTE de l'Appendix D T.018
"""

def test_lfsr_appendix_d():
    print("=" * 70)
    print("Test LFSR - Configuration Appendix D T.018 (Figure D-1)")
    print("=" * 70)
    print("\nConfiguration:")
    print("  - Output depuis LSB (bit 0)")
    print("  - Shift LEFT")
    print("  - Feedback = bit[22] XOR bit[17]")
    print("  - Feedback injecté au LSB\n")

    lfsr = 0x000001
    chips_binary = []

    for i in range(64):
        # OUTPUT DEPUIS LE BIT 0 (LSB)
        output_bit = lfsr & 1
        chips_binary.append(output_bit)

        if i < 8:
            bit_22 = (lfsr >> 22) & 1
            bit_17 = (lfsr >> 17) & 1
            print(f"Chip {i}: État=0x{lfsr:06X} ({lfsr:023b}) | bit[0]={output_bit}")

        # Feedback
        feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
        
        # Shift LEFT + feedback injecté au LSB
        lfsr = ((lfsr << 1) & 0x7FFFFF) | feedback

        if i < 8:
            print(f"          feedback={feedback} → 0x{lfsr:06X}\n")

    # Convertir en hex (4 groupes de 16 bits)
    hex_values = []
    for i in range(4):
        bits_16 = chips_binary[i*16:(i+1)*16]
        val = sum(b << (15-j) for j, b in enumerate(bits_16))
        hex_values.append(f"{val:04X}")

    print("\n" + "=" * 70)
    print(f"Séquence obtenue : {' '.join(hex_values)}")
    print(f"Séquence attendue: 8000 0108 4212 84A1 (T.018 Table 2.2)")

    if hex_values == ["8000", "0108", "4212", "84A1"]:
        print("\n✓✓✓ PARFAIT ! Configuration validée ✓✓✓")
        print("\nRÉSOLUTION:")
        print("  - Output: bit[0] (LSB)")
        print("  - Direction: SHIFT LEFT")
        print("  - Feedback: (bit[22] XOR bit[17]) injecté au LSB")
        return True
    else:
        print("\n✗ Échec...")
        return False

if __name__ == "__main__":
    result = test_lfsr_appendix_d()
    exit(0 if result else 1)
