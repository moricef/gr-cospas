# GR-COSPAS Directory Structure Analysis
## 1G vs 2G Beacon Implementation Status

**Date**: 2025-10-17  
**Project**: COSPAS-SARSAT GNU Radio Decoder (gr-cospas)  
**Throughness Level**: Very Thorough Analysis

---

## EXECUTIVE SUMMARY

### Current State
- **1G Beacons (Biphase-L)**: ✅ **FULLY IMPLEMENTED & 100% FUNCTIONAL**
  - Modulation: Biphase-L (Manchester)
  - Data rate: 400 bps
  - Frame sizes: 112 bits (short) / 144 bits (long)
  - Status: Production-ready, 100% deterministic decoding achieved
  
- **2G Beacons (OQPSK/DSSS)**: ⏳ **PARTIALLY IMPLEMENTED - Framework Only**
  - Modulation: OQPSK + DSSS (Direct Sequence Spread Spectrum)
  - Data rate: 300 bps
  - Chip rate: 38,400 chips/s
  - Frame size: 250 bits (202 info + 48 BCH)
  - Status: Generator framework exists, demodulator NOT YET IMPLEMENTED

### Key Finding: MIXED IMPLEMENTATION
The codebase contains **extensive 2G infrastructure** (LFSR tests, PN generators, OQPSK generator) but **the actual gr-cospas decoder module is 100% focused on 1G**. The demodulator will need significant work for 2G support.

---

## DETAILED BREAKDOWN BY DIRECTORY

### 1. `/lib/` - C++ Core Decoder Implementation

#### Files Present
- `cospas_sarsat_decoder_impl.h` (140 lines)
- `cospas_sarsat_decoder_impl.cc` (552 lines)
- Backup files: `.back_101120252247`, `_cor`

#### 1G Implementation: ✅ COMPLETE

**Module Type**: Biphase-L Demodulator

**Key Constants**:
```cpp
BIT_RATE = 400.0f                    // 1G standard: 400 bps
PREAMBLE_BITS = 15                   // 15 consecutive '1' bits
FRAME_SYNC_BITS = 9                  // Frame sync pattern
SHORT_FRAME_TOTAL_BITS = 112         // 15 + 9 + 88
LONG_FRAME_TOTAL_BITS = 144          // 15 + 9 + 120
FRAME_SYNC_NORMAL = 0b000101111      // Normal mode
FRAME_SYNC_TEST = 0b011010000        // Self-test mode
MOD_PHASE = 1.1f                     // ±1.1 radians phase shift
```

**State Machine** (5 states):
1. `STATE_CARRIER_SEARCH` - Detect 160ms unmodulated carrier
2. `STATE_INITIAL_JUMP` - Detect phase jump at modulation start
3. `STATE_PREAMBLE_SYNC` - Synchronize on 15 '1' bits
4. `STATE_FRAME_SYNC` - Detect 9-bit sync pattern
5. `STATE_DATA_DECODE` - Decode message bits

**Architecture**:
- **Buffer Accumulation**: Accumulates 21,000 samples before processing (solves GNU Radio scheduler fragmentation)
- **Phase Detection**: Measures phase at bit center to detect transitions
- **Bit Decoding**: 
  - '1' bit: +1.1 → -1.1 (descending transition)
  - '0' bit: -1.1 → +1.1 (ascending transition)

**Key Methods**:
- `detect_carrier()` - Checks if phase near 0 (carrier present)
- `detect_initial_jump()` - Detects start of modulation
- `decode_bit()` - Demodulates single bit from samples
- `process_accumulated_buffer()` - Main state machine execution

**Performance**:
- ✅ 100% deterministic (30/30 test passes)
- ✅ Handles both short (112-bit) and long (144-bit) frames
- ✅ Detects normal and self-test modes

#### 2G Implementation: ❌ MISSING

**Expected Features NOT PRESENT**:
- OQPSK demodulation (I/Q offset handling)
- PN sequence despreading (LFSR-based)
- Carrier recovery (Costas loop or similar)
- Timing recovery (Gardner or M&M algorithm)
- BCH(250,202) error correction
- Chip-level processing (38.4 kchips/s)
- 8 chips/bit despreading

**Hardware Present But Not Used**:
- Complex sample support (gr_complex input/output exists)
- Phase computation infrastructure (could be adapted)
- State machine framework (extensible)

---

### 2. `/python/cospas/` - Python Blocks & Generators

#### Files Present

**Main Generator**: `cospas_generator.py` (150+ lines)

**Function**: Generate synthetic 1G beacon signals

**Type**: ✅ **1G ONLY**

**Parameters** (hardcoded for 1G):
```python
SAMPLE_RATE = 6400.0         # 1G: 6.4 kHz
BIT_RATE = 400.0             # 1G: 400 bps
SAMPLES_PER_BIT = 16         # 6400/400
CARRIER_DURATION = 0.160     # 160 ms unmodulated carrier
PREAMBLE_BITS = 15           # Fifteen '1' bits
FRAME_SYNC_BITS = 9
MOD_PHASE = 1.1              # ±1.1 radians
```

**Frame Structure Generated**:
1. Carrier: 1024 samples @ phase 0 (160 ms)
2. Preamble: 15 bits of '1'
3. Frame Sync: 9-bit pattern (normal or test mode)
4. Message: Up to 18 octets (144 bits maximum)

**Modulation** (Biphase-L):
```python
def generate_bit(self, bit):
    if bit == '1':
        # Transition: +1.1 → -1.1 (mid-bit)
        first_half = exp(1j * 1.1)
        second_half = exp(-1j * 1.1)
    else:
        # Transition: -1.1 → +1.1 (mid-bit)
        first_half = exp(-1j * 1.1)
        second_half = exp(1j * 1.1)
```

**No 2G Support**: Zero code for OQPSK, DSSS, or PN sequences.

---

### 3. `/examples/` - Test Scripts & Flowgraphs

#### 1G Test Scripts: ✅ COMPREHENSIVE

**Main Examples**:

| File | Purpose | Type | Status |
|------|---------|------|--------|
| `test_generator_decoder.py` | Generator→Decoder loopback | 1G | ✅ Working |
| `decode_iq_40khz.py` | Decode IQ file (40 kHz) | 1G | ✅ Working |
| `decode_wav.py` | Decode WAV file | 1G | ✅ Working |
| `parse_cospas_frame.py` | Parse decoded message bits | 1G | ✅ Working |
| `test_real_frame.py` | Test known beacon data | 1G | ✅ Working |
| `verify_decoding.py` | Validation script | 1G | ✅ Working |

**Test Coverage**:
- Generator correctness verification
- Decoder determinism tests (30x repetitions)
- Real frame decoding
- Frame format parsing

#### 2G Test Scripts: ❌ NONE

**Found 2G-related files**:
- Multiple test scripts reference "2G" in names
- But all are about GENERATING or TESTING LFSR, not decoding

**Example**: `decode_iq_gui.py` has comments mentioning BPHASE support but no 2G demodulator

---

### 4. `/tools/` - Utilities & Research

#### EXTENSIVE 2G Infrastructure Present

**LFSR Tests (15+ files)**:

These test LFSR implementations for PN sequence generation (used in 2G DSSS):

| File | Purpose | Status |
|------|---------|--------|
| `test_lfsr_final.py` | Final LFSR implementation | ✅ Validated |
| `test_lfsr_appendix_d.py` | T.018 Appendix D compliance | ✅ Passing |
| `test_fibonacci_lfsr.py` | Fibonacci LFSR variant | ⏳ Testing |
| `test_galois_lfsr.py` | Galois LFSR variant | ⏳ Testing |
| `verify_lfsr_from_hex.py` | LFSR hex validation | ⏳ Testing |
| `test_lfsr_corrected.py` | Corrected LFSR | ✅ Working |
| And 9 more LFSR-related test files | | |

**Key Finding**: These test **PN sequence generation for 2G spreading**, not 1G demodulation

**PN Sequence Generator**: `generate_pn_sequences.py` (210 lines)

**Purpose**: Generate I and Q channel PN sequences per T.018 Table 2.2

**Implementation** (CORRECT):
```python
def generate_prn_sequence_i(length=38400):
    """Generate 38400 chips for complete 2G frame"""
    lfsr = 0x000001  # T.018 initial state I-channel
    
    for i in range(length):
        sequence[i] = lfsr & 1  # Output LSB
        
        # Feedback: bit[22] XOR bit[17]
        feedback = ((lfsr >> 22) ^ (lfsr >> 17)) & 1
        
        # Shift right (Fibonacci configuration)
        lfsr = (lfsr >> 1) | (feedback << 22)
        lfsr &= 0x7FFFFF  # Keep 23 bits
```

**Validation**: Generates matching T.018 Table 2.2 reference values

#### OQPSK Generator: `generate_oqpsk_iq.py` (470+ lines)

**Status**: ✅ **COMPLETE & T.018 COMPLIANT**

**Features**:
- Converts 250-bit 2G frame (hex) to IQ samples
- LFSR_T018 class with T.018 Table 2.2 compliance
- DSSS spreading (256 chips/bit per T.018)
- OQPSK modulation with Q offset (Tc/2)
- Output: gr_complex format (400 kHz sample rate)

**Key Constants** (2G specifications):
```python
DATA_RATE = 300              # 300 bps
CHIP_RATE = 38400            # 38.4 kchips/s
CHIPS_PER_BIT = 256          # 256 chips/bit
PREAMBLE_BITS = 50           # 50 preamble bits
INFO_BITS = 202              # Message bits
BCH_BITS = 48                # BCH(250,202) parity
TOTAL_MESSAGE_BITS = 250     # Total bits per frame
SAMPLE_RATE = 400000         # 400 kHz (10.42 samples/chip)
```

**PN LFSR Parameters** (T.018 Table 2.2):
```python
INIT_NORMAL_I = 0x000001   # I-channel normal mode
INIT_NORMAL_Q = 0x000041   # Q-channel (offset 64 chips)
INIT_TEST_I = 0x69E780     # I-channel self-test
INIT_TEST_Q = 0x3CB948     # Q-channel self-test
```

**Implementation Details**:

1. **LFSR Class** (`LFSR_T018`):
   - Polynomial: x^23 + x^18 + 1 (T.018 Appendix D)
   - Feedback: X0 ⊕ X18 (output bit XOR'd with bit 18)
   - Shift: RIGHT (X_n → X_{n-1}, feedback → X22)
   - Output: ±1 signal (Logic 1 → -1, Logic 0 → +1)

2. **DSSS Spreading** (`dsss_spread_oqpsk`):
   - Odd bits (1,3,5,...) → I-channel (256 chips each)
   - Even bits (0,2,4,...) → Q-channel (256 chips each)
   - Bit value 0: PRN normal
   - Bit value 1: PRN inverted

3. **OQPSK Modulation** (`oqpsk_modulate`):
   - I-channel: odd bits, no offset
   - Q-channel: even bits, delayed by Tc/2 (half chip period)
   - Output: Complex signal (I + jQ)

**Testing**: ✅ PN generation validates against T.018 reference sequences

---

## MODULATION COMPARISON TABLE

| Feature | 1G (Biphase-L) | 2G (OQPSK+DSSS) |
|---------|----------------|-----------------|
| **Implemented in gr-cospas** | ✅ Yes | ❌ No |
| **Data Rate** | 400 bps | 300 bps |
| **Modulation** | Biphase-L (Manchester) | OQPSK with offset |
| **Phase Shift** | ±1.1 radians | ±π/4 (QPSK) |
| **Chip Rate** | N/A (non-spread) | 38.4 kchips/s |
| **Spreading** | None | DSSS 256 chips/bit |
| **PN LFSR** | None | Yes (x^23+x^18+1) |
| **Frame Size** | 112 or 144 bits | 250 bits (fixed) |
| **FEC** | None (CRC only) | BCH(250,202) |
| **Generator Available** | ✅ Yes | ✅ Yes |
| **Demodulator** | ✅ Complete | ❌ Missing |
| **Test IQ Files** | ✅ Many | ⏳ Theoretical support |
| **Example Scripts** | ✅ 8+ scripts | ❌ 0 working examples |

---

## KEYWORD ANALYSIS

### 1G Keywords: ✅ THOROUGHLY PRESENT

**In `lib/cospas_sarsat_decoder_impl.cc`**:
- "biphase" (implied by Manchester terminology)
- "manchester" (not explicit, called "mod_phase")
- "400" (references to BIT_RATE = 400.0f)
- "112" / "144" (FRAME_TOTAL_BITS constants)
- "preamble_ones" (synchronization)
- "frame_sync" (pattern matching)

**In `python/cospas/cospas_generator.py`**:
- "Biphase-L" (docstring)
- "400.0" (BIT_RATE)
- "1.1" (MOD_PHASE)
- "Manchester" (docstring)

### 2G Keywords: ⏳ PRESENT IN TOOLS, MISSING IN DECODER

**In `/tools/`**:
- "oqpsk" / "OQPSK" (5+ files)
- "dsss" / "DSSS" (multiple generators)
- "lfsr" / "LFSR" (15+ test files)
- "prn" / "PRN" (PN sequence generators)
- "chip" / "CHIP" (chip rate: 38400)
- "256" (chips/bit)
- "38400" (chip rate)
- "250" (frame bits)
- "BCH" (error correction)

**IN `/lib/` Decoder**: ❌ **COMPLETELY ABSENT**

---

## WHAT IS ACTUALLY SUPPORTED vs WHAT'S MIXED UP

### ✅ FULLY SUPPORTED (PRODUCTION READY)

**gr-cospas Decoder**:
- **1G Biphase-L beacons** (400 bps, ±1.1 rad phase shift)
- Short frames: 112 bits (15 preamble + 9 sync + 88 message)
- Long frames: 144 bits (15 preamble + 9 sync + 120 message)
- Normal and self-test modes
- **100% deterministic decoding** (buffer accumulation architecture)
- **Frame structure**:
  - 160 ms unmodulated carrier detection
  - 15-bit preamble synchronization
  - 9-bit frame sync (000101111 or 011010000)
  - Variable message length decoding

**Synthetic 1G Signal Generation**:
- `cospas_generator.py` creates perfect 1G test signals
- Configurable payloads (up to 18 octets)
- Compatible with 40 kHz or 6.4 kHz sample rates

### ⏳ FRAMEWORK ONLY (NOT INTEGRATED INTO DECODER)

**2G OQPSK IQ Generator** (Complete standalone tool):
- `generate_oqpsk_iq.py` creates T.018-compliant 2G signals
- Takes 250-bit frame (hex) → outputs gr_complex IQ file
- Implements complete DSSS spreading (LFSR-based)
- OQPSK modulation with Q-channel offset
- Can generate 2G test files for future demodulator

**PN Sequence Generators** (Research/validation tools):
- `generate_pn_sequences.py`: Generates I/Q channel PN sequences
- `generate_oqpsk_iq.py`: LFSR_T018 class with validated sequences
- Multiple LFSR implementations for comparison

### ❌ NOT IMPLEMENTED

**2G Demodulator Block** (Required for production 2G support):
- ❌ OQPSK demodulation (I/Q recovery with offset)
- ❌ Carrier recovery (Costas loop or similar)
- ❌ Timing recovery (Gardner or M&M algorithm)
- ❌ PN despreading (256 chips → 1 bit)
- ❌ BCH(250,202) error correction integration
- ❌ Auto-detection of 1G vs 2G beacons
- ❌ Frame parsing for 2G (different from 1G)

**In Decoder**: The `cospas_sarsat_decoder_impl` module is **100% hardcoded for 1G**:
- Fixed 400 bps assumption
- Biphase-L demodulation logic only
- No 2G frame structure support
- No spreading/despreading capability

---

## FILE CATEGORIZATION

### **1G EXCLUSIVE** (Never Touch for 2G)
- `/lib/cospas_sarsat_decoder_impl.h`
- `/lib/cospas_sarsat_decoder_impl.cc`
- `/python/cospas/cospas_generator.py`
- All example test scripts

### **2G ONLY** (Not Used by 1G)
- `/tools/generate_oqpsk_iq.py`
- `/tools/generate_pn_sequences.py`
- `/tools/test_lfsr_*.py` (15+ files)
- `/tools/*_appendix_*.py`
- `/docs/ETAT_GENERATEUR_2G.md`
- `/docs/OQPSK_vs_BPSK.md`

### **SUPPORTING INFRASTRUCTURE** (Can be used by both)
- `/docs/ROADMAP_PROJET.md`
- `/docs/ARCHITECTURE_CIBLE.md`
- Documentation and specs

---

## MISSING PIECES FOR 2G PRODUCTION

To add **2G OQPSK support** to gr-cospas, you need to implement:

1. **Auto-detection** (can signal be 1G or 2G?)
2. **OQPSK Demodulator** (I/Q recovery with offset)
3. **Carrier Recovery** (PLL or Costas loop)
4. **Timing Recovery** (Clock synchronization)
5. **PN Despreading** (Use LFSR_T018 from generator)
6. **BCH Decoder** (Error correction)
7. **Frame Parser** (2G-specific message structure)

**Current state**: You have **60% of infrastructure** (generators, LFSR validation) but **0% of demodulator**.

---

## RECOMMENDATIONS

### Immediate Actions
1. **Keep 1G unchanged**: It's working and production-ready
2. **Create separate 2G block** (not in main decoder yet)
3. **Use existing tools**: Reuse LFSR_T018 class from generator
4. **Implement modular**: Demod → Despread → BCH pipeline

### Integration Strategy
```
gr-cospas/
├── lib/
│   ├── cospas_sarsat_decoder_impl.cc (KEEP: 1G only)
│   └── cospas_sarsat_decoder_2g_impl.cc (NEW: 2G OQPSK)
├── python/
│   ├── cospas_generator.py (KEEP: 1G only)
│   ├── cospas_generator_2g.py (NEW: 2G generator)
│   └── pn_sequences.py (NEW: LFSR utilities)
└── tools/
    └── (Keep all tools for validation)
```

### Estimated Effort
- **Phase 1** (1-2 days): OQPSK demodulator basic
- **Phase 2** (2-3 days): PN despreading
- **Phase 3** (3-4 days): BCH integration + auto-detect
- **Phase 4** (1-2 days): Testing & validation

**Total**: ~1-2 weeks for production-ready 2G support

---

## CONCLUSION

**What gr-cospas actually supports right now**:
- ✅ **1G beacons only** - Fully functional, production-ready
- ❌ 2G decoders not present in main module
- ⏳ 2G infrastructure (generators, tools) exists but not integrated

**What's mixed up**:
- Extensive 2G research/tools exist in `/tools/` but live in wrong place
- OQPSK generator is standalone, not integrated as GNU Radio block
- Documentation mentions "auto-detect 1G/2G" but code only supports 1G

**The bottom line**:
If you want to receive real 1G beacons today: **Ready to go** ✅  
If you want to receive real 2G beacons: **Requires 1-2 weeks development** ⏳
