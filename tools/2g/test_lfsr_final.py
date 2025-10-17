#!/usr/bin/env python3
"""
Test LFSR - Analyse complète en comparant avec Appendix D ligne par ligne
"""

def test_lfsr_exact_appendix():
    print("=" * 70)
    print("Comparaison EXACTE avec Appendix D Figure D-1")
    print("=" * 70)
    
    # États de référence depuis Appendix D (lignes 783-818)
    # Format: [bit22, bit21, ..., bit1, bit0]
    appendix_states = [
        0b00000000000000000000001,  # État 0
        0b10000000000000000000000,  # État 1
        0b01000000000000000000000,  # État 2
        0b00100000000000000000000,  # État 3
        0b00010000000000000000000,  # État 4
        0b00001000000000000000000,  # État 5
        0b10000100000000000000000,  # État 6 (feedback activé!)
    ]
    
    appendix_outputs = [1, 0, 0, 0, 0, 0, 0]  # 7 premiers outputs selon Appendix D

    lfsr = 0x000001
    all_outputs = []

    print("\nComparaison premiers états:")
    print(f"{'État':<6} {'LFSR (hex)':<10} {'LFSR (bin)':<24} {'Out':<4} {'Attendu':<8}")
    print("-" * 70)

    for i in range(min(7, len(appendix_states))):
        output_bit = lfsr & 1
        all_outputs.append(output_bit)
        
        expected = appendix_outputs[i] if i < len(appendix_outputs) else '?'
        match = "✓" if output_bit == expected else "✗"
        
        print(f"{i:<6} 0x{lfsr:06X}   {lfsr:023b}  {output_bit:<4} {expected} {match}")

        # Shift et feedback
        feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
        lfsr = ((lfsr << 1) & 0x7FFFFF) | feedback

    # Générer les 64 chips complets
    lfsr = 0x000001
    chips = []
    for i in range(64):
        chips.append(lfsr & 1)
        feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
        lfsr = ((lfsr << 1) & 0x7FFFFF) | feedback

    # Convertir en hex
    hex_values = []
    for i in range(4):
        bits_16 = chips[i*16:(i+1)*16]
        val = sum(b << (15-j) for j, b in enumerate(bits_16))
        hex_values.append(f"{val:04X}")

    print("\n" + "=" * 70)
    print(f"Séquence complète: {' '.join(hex_values)}")
    print(f"Attendue (T.018) : 8000 0108 4212 84A1")
    
    if hex_values == ["8000", "0108", "4212", "84A1"]:
        print("\n✓✓✓ VALIDATION RÉUSSIE ✓✓✓")
        return True
    else:
        print("\n✗ Pas encore la bonne configuration")
        # Testons l'inverse du bit de sortie
        print("\nTest avec mapping inversé (bit output)...")
        chips_inv = [1-b for b in chips]
        hex_inv = []
        for i in range(4):
            bits_16 = chips_inv[i*16:(i+1)*16]
            val = sum(b << (15-j) for j, b in enumerate(bits_16))
            hex_inv.append(f"{val:04X}")
        print(f"Séquence inversée: {' '.join(hex_inv)}")
        
        return False

if __name__ == "__main__":
    test_lfsr_exact_appendix()
