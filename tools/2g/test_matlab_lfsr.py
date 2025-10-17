#!/usr/bin/env python3
"""
Test LFSR with Matlab comm.PNSequence configuration
"""

def lfsr_matlab_style(initial_state_vector, num_chips=64):
    """
    Simulate Matlab comm.PNSequence behavior
    Polynomial: X23+X18+1

    Args:
        initial_state_vector: List of 23 bits [bit22, bit21, ..., bit1, bit0]
        num_chips: Number of chips to generate

    Returns:
        List of output bits
    """
    # Convert vector to integer (MSB first interpretation)
    state = 0
    for i, bit in enumerate(initial_state_vector):
        state |= (bit << (22 - i))

    print(f"Initial state from vector: 0x{state:06X}")
    print(f"Binary: {state:023b}")

    output = []

    for i in range(num_chips):
        # Output from bit[0] (LSB)
        output_bit = state & 1
        output.append(output_bit)

        # Feedback from bit[22] XOR bit[17] for polynomial X23+X18+1
        # bit[22] is tap for X23, bit[17] is tap for X18
        bit_22 = (state >> 22) & 1
        bit_17 = (state >> 17) & 1
        feedback = bit_22 ^ bit_17

        # Shift right and insert feedback at bit[22]
        state = (state >> 1) | (feedback << 22)

        if i < 10:
            print(f"Step {i}: output={output_bit}, state=0x{state:06X}, feedback={feedback}")

    return output


def lfsr_matlab_style_shift_left(initial_state_vector, num_chips=64):
    """
    Try shift LEFT with output from MSB
    """
    state = 0
    for i, bit in enumerate(initial_state_vector):
        state |= (bit << (22 - i))

    print(f"\nShift LEFT test:")
    print(f"Initial state: 0x{state:06X}")

    output = []

    for i in range(num_chips):
        # Output from bit[22] (MSB)
        output_bit = (state >> 22) & 1
        output.append(output_bit)

        # Feedback
        bit_22 = (state >> 22) & 1
        bit_17 = (state >> 17) & 1
        feedback = bit_22 ^ bit_17

        # Shift left and insert feedback at bit[0]
        state = ((state << 1) | feedback) & 0x7FFFFF  # Mask to 23 bits

        if i < 10:
            print(f"Step {i}: output={output_bit}, state=0x{state:06X}")

    return output


# Matlab configuration from PDF page 4
normalI = [0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 1]
normalQ = [0, 0, 1, 1, 0, 1, 0, 1, 1, 0, 0, 0, 0, 0, 1, 1, 1, 1, 1, 1, 1, 0, 0]

print("="*60)
print("MATLAB LFSR TEST - NORMAL I")
print("="*60)
print(f"Initial vector: {normalI}")

# Test shift RIGHT
prn_i_right = lfsr_matlab_style(normalI, 64)

# Convert to hex
hex_output_right = []
for i in range(0, 64, 16):
    chunk = prn_i_right[i:i+16]
    value = 0
    for j, bit in enumerate(chunk):
        value |= (bit << (15 - j))
    hex_output_right.append(f"{value:04X}")

print(f"\nShift RIGHT output (first 64 bits): {' '.join(hex_output_right)}")
print(f"Expected from Matlab:                 8000 0108 4212 84A1")

# Test shift LEFT
prn_i_left = lfsr_matlab_style_shift_left(normalI, 64)

hex_output_left = []
for i in range(0, 64, 16):
    chunk = prn_i_left[i:i+16]
    value = 0
    for j, bit in enumerate(chunk):
        value |= (bit << (15 - j))
    hex_output_left.append(f"{value:04X}")

print(f"\nShift LEFT output (first 64 bits):  {' '.join(hex_output_left)}")
