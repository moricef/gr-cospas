# tools/2g - Second Generation (2G) COSPAS-SARSAT Tools

**Status**: IQ Generator Ready ✓ | Demodulator Missing ✗

## Overview

Tools for **2nd generation COSPAS-SARSAT beacons** (T.018 Rev.12 compliant).

### 2G Beacon Specifications
- **Modulation**: OQPSK with DSSS
- **Data Rate**: 300 bps
- **Chip Rate**: 38.4 kchips/s
- **Spreading**: 256 chips/bit per channel (I/Q)
- **Frame Length**: 252 bits (2 header + 250 data)
- **Error Correction**: BCH(250,202) with 48-bit parity
- **LFSR**: x²³ + x¹⁸ + 1 (T.018 Table 2.2 validated)

## Available Tools

### IQ Signal Generator
**generate_oqpsk_iq.py** - T.018-compliant OQPSK IQ generator

```bash
# Generate IQ file from hex frame
./generate_oqpsk_iq.py <250bit_hex_frame> -o output.iq

# Example with validated frame
./generate_oqpsk_iq.py 89C3F45639195999A02B33326C3EC4400007FFF00C0283200000DCA2C07A361 -o beacon.iq
```

**Features**:
- ✓ Correct LFSR (X0 ⊕ X18, shift RIGHT)
- ✓ Validated against T.018 Table 2.2: 8000 0108 4212 84A1
- ✓ 400 kHz sample rate
- ✓ OQPSK modulation with Tc/2 offset
- ✓ DSSS spreading (256 chips/bit)

### Validated Test Frames

**Frame 1** (EPIRB France Normal mode):
```
89C3F45639195999A02B33326C3EC4400007FFF00C0283200000DCA2C07A361
✓ BCH valid, France EPIRB, TAC:9999, 43.20°N 5.40°E
```

**Frame 2** (EPIRB France):
```
0C0E7456390956CCD02799A2468ACF135787FFF00C02832000037707609BC0F
✓ BCH valid, France EPIRB, TAC:12345, 42.85°N 4.95°E
```

## IMPORTANT LIMITATIONS

### ⚠ No 2G Demodulator Yet

The gr-cospas module (/lib/cospas_sarsat_decoder_impl.cc) currently supports **1G beacons ONLY** (Biphase-L).

**Missing for 2G**:
- OQPSK demodulator
- PN despreading (256 chips → 1 bit)
- Carrier/timing recovery
- BCH(250,202) error correction

**Development Time**: Estimated 1-2 weeks for production-ready 2G demodulator.

---

**Last Updated**: 2025-10-17
**LFSR Fix**: 2025-10-16 (X0 ⊕ X18, validated Table 2.2)
