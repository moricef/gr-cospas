# examples/2g - Second Generation (2G) COSPAS-SARSAT Examples

**Status**: Non-Functional ✗ (No 2G demodulator available)

## Overview

Attempted IQ demodulation scripts for **2nd generation COSPAS-SARSAT beacons**.

### 2G Beacon Specifications
- **Modulation**: OQPSK with DSSS
- **Data Rate**: 300 bps
- **Chip Rate**: 38.4 kchips/s
- **Spreading**: 256 chips/bit
- **Frame Length**: 252 bits
- **Error Correction**: BCH(250,202)

## Available Scripts

### IQ Demodulation (NON-FUNCTIONAL)
- `decode_iq_file.py` - Attempt to decode IQ file
- `decode_iq_gui.py` - GUI version (non-functional)
- `decode_iq_40khz.py` - 40 kHz sample rate attempt
- `decode_matlab_iq.py` - MATLAB-style IQ decode
- `decode_iq_matlab_direct.py` - Direct IQ processing
- `decode_matlab_iq_gui.py` - GUI version
- `decode_cospas_iq.py` - COSPAS IQ decoder attempt

### Analysis
- `analyze_iq_matlab.py` - IQ signal analysis
- `test_resampling.py` - Sample rate conversion tests
- `parse_cospas_frame.py` - Frame parsing

## CRITICAL LIMITATION

### ⚠ These scripts DO NOT work!

The gr-cospas decoder (`/lib/cospas_sarsat_decoder_impl.cc`) only supports **1G beacons** (Biphase-L).

**Problem**: Scripts call the 1G decoder with 2G IQ files → No output

**Missing**:
- OQPSK demodulator block
- PN despreading (256 chips → 1 bit)
- Carrier/timing recovery
- BCH(250,202) error correction

## Workaround

For 2G signal generation, use: `/tools/2g/generate_oqpsk_iq.py`

For 2G frame decoding (from hex), use external decoder: `/home/fab2/.../dec406_v10.2/dec406_hex`

## Development Needed

To make these scripts functional, implement 2G demodulator in `/lib/`:
1. Create `cospas_sarsat_decoder_2g_impl.cc`
2. OQPSK demodulation
3. PN despreading
4. BCH correction
5. Frame parsing

**Estimated effort**: 1-2 weeks

---

**Last Updated**: 2025-10-17
**Status**: Awaiting 2G demodulator development
