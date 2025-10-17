# examples/1g - First Generation (1G) COSPAS-SARSAT Examples

**Status**: Fully Operational ✓ (100% deterministic)

## Overview

Examples and test scripts for **1st generation COSPAS-SARSAT beacons**.

### 1G Beacon Specifications
- **Modulation**: Biphase-L (Manchester)
- **Data Rate**: 400 bps
- **Frame Length**: 112 bits (short), 144 bits (long)
- **Error Detection**: CRC
- **Sample Rate**: 48 kHz (audio)

## Available Scripts

### Demodulation & Analysis
- `decode_wav.py` - Decode 1G beacon from WAV file
- `analyze_wav.py` - Analyze 1G WAV signal (GUI)
- `analyze_wav_nogui.py` - Analyze 1G WAV signal (no GUI)
- `plot_wav_full.py` - Plot WAV signal
- `plot_signal.py` - Signal visualization

### Testing & Validation
- `test_cospas_decoder.py` - Test decoder functionality
- `test_generator_decoder.py` - Test generator + decoder chain
- `test_real_frame.py` - Test with real beacon frames
- `test_selftest_mode.py` - Test self-test mode
- `test_short_frame.py` - Test short frame format
- `verify_decoding.py` - Verify decode correctness
- `verify_generator.py` - Verify generator output

### Debug & Analysis
- `debug_initial_jump.py` - Debug initial synchronization
- `test_all_files.sh` - Batch test all files
- `test_determinism.sh` - Check 100% determinism
- `test_stable.sh` - Stability testing
- `test_errors.sh` - Error handling tests
- `analyze_errors.sh` - Error analysis
- `find_failure.sh` - Find failure cases

## Status

**Production Ready**: 100% deterministic decoding (30/30 tests passing)

The 1G decoder (`/lib/cospas_sarsat_decoder_impl.cc`) is fully operational with:
- 5-state machine: CARRIER_SEARCH → INITIAL_JUMP → PREAMBLE_SYNC → FRAME_SYNC → DATA_DECODE
- Buffer accumulation for determinism
- Biphase-L demodulation
- CRC validation

## Usage Example

```bash
# Decode 1G beacon from WAV
./decode_wav.py beacon_1g.wav

# Test determinism (should show 30/30 success)
./test_determinism.sh
```

## Related

- **Generator**: `/python/cospas/cospas_generator.py` (1G signal synthesis)
- **Decoder**: `/lib/cospas_sarsat_decoder_impl.cc` (C++ core)
- **GRC Files**: `*.grc` - GNU Radio Companion flowgraphs

---

**Last Updated**: 2025-10-17
