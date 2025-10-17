#!/usr/bin/env python3
"""
Test LFSR avec OUTPUT depuis le MSB (bit 22) - Version LSFR_code.txt
"""

def test_lfsr_msb_output():
    print("=" * 70)
    print("Test LFSR - OUTPUT depuis MSB (bit 22) + SHIFT LEFT")
    print("=" * 70)
    print("\nBasé sur LSFR_code.txt lignes 42-46:")
    print("  output = (lfsr >> 22) & 1  # MSB!")
    print("  feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1")
    print("  lfsr = ((lfsr << 1) | feedback) & 0x7FFFFF\n")

    lfsr = 0x000001
    chips = []

    for i in range(64):
        # OUTPUT DEPUIS LE BIT 22 (MSB) !
        output_bit = (lfsr >> 22) & 1
        chips.append(output_bit)

        if i < 8:
            bit_22 = (lfsr >> 22) & 1
            bit_17 = (lfsr >> 17) & 1
            print(f"Chip {i}: État=0x{lfsr:06X} | bit[22]={bit_22} bit[17]={bit_17} | Output={output_bit}")

        # Feedback et shift LEFT
        feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
        lfsr = ((lfsr << 1) | feedback) & 0x7FFFFF

        if i < 8:
            print(f"          feedback={feedback} → Nouvel état=0x{lfsr:06X}\n")

    # Convertir en hex (4 groupes de 16 bits)
    hex_values = []
    for i in range(4):
        bits_16 = chips[i*16:(i+1)*16]
        val = sum(b << (15-j) for j, b in enumerate(bits_16))
        hex_values.append(f"{val:04X}")

    print("\n" + "=" * 70)
    print(f"Séquence obtenue : {' '.join(hex_values)}")
    print(f"Séquence attendue: 8000 0108 4212 84A1")

    if hex_values == ["8000", "0108", "4212", "84A1"]:
        print("\n✓✓✓ PARFAIT ! C'est LA solution !")
        return True
    else:
        print("\n✗ Pas encore...")
        return False

if __name__ == "__main__":
    test_lfsr_msb_output()
