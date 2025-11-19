# gr-cospas

GNU Radio Out-of-Tree (OOT) Module for COSPAS-SARSAT 406 MHz Beacon Decoder

## Overview

This module provides a decoder for COSPAS-SARSAT 406 MHz emergency beacons using GNU Radio. COSPAS-SARSAT is an international satellite-based search and rescue system.

### Signal Characteristics
- **Frequency**: 406 MHz (centered)
- **Modulation**: Biphase-L (Manchester-like)
- **Data rate**: 400 bps
- **Frame structure**:
  - 160 ms unmodulated carrier (6400 samples @ 40 kHz)
  - 15-bit preamble (all '1's)
  - 9-bit frame sync (000101111 normal, 011010000 self-test)
  - 120-bit message (long format) or 88-bit (short format)

## Status

✅ **FULLY FUNCTIONAL** - 100% deterministic decoding achieved!

- **Success rate**: **100%** (30/30 tests passed)
- **Solution**: Buffer accumulation architecture
- **Previous issue**: GNU Radio scheduler fragmentation (SOLVED)

See [`ANALYSE_BUG_NON_DETERMINISME.md`](ANALYSE_BUG_NON_DETERMINISME.md) for detailed problem analysis.

See [`RESUME_FINAL.md`](RESUME_FINAL.md) for solution overview.

## Features

- ✅ Biphase-L demodulation
- ✅ Carrier detection (160 ms @ 1544 Hz)
- ✅ Initial phase jump detection
- ✅ Preamble synchronization
- ✅ Frame sync detection (normal/test modes)
- ✅ Long (144-bit) and short (112-bit) frame support
- ✅ **100% deterministic decoding** (buffer accumulation)

## Installation

### Prerequisites

```bash
sudo apt-get install gnuradio gnuradio-dev cmake python3-numpy
```

### Build and Install

```bash
mkdir build
cd build
cmake ..
make
sudo make install
sudo ldconfig
```

## Usage

### Python Example

```python
from gnuradio import gr, blocks
import cospas

class decoder_flowgraph(gr.top_block):
    def __init__(self, iq_file):
        gr.top_block.__init__(self)

        # File source (40 kHz IQ samples)
        self.file_source = blocks.file_source(
            gr.sizeof_gr_complex, iq_file, False
        )

        # COSPAS-SARSAT decoder
        self.decoder = cospas.cospas_sarsat_decoder(
            sample_rate=40000,
            debug_mode=True
        )

        # Vector sink to collect output
        self.vector_sink = blocks.vector_sink_b()

        # Connect blocks
        self.connect(self.file_source, self.decoder, self.vector_sink)

# Run
tb = decoder_flowgraph("beacon_signal.iq")
tb.set_max_noutput_items(8192)  # Important for determinism!
tb.run()
```

See [`examples/decode_iq_40khz.py`](examples/decode_iq_40khz.py) for complete example.

## Testing

```bash
cd examples

# Test 30 times to check determinism
bash test_stable.sh

# Find first failure with debug output
bash find_failure.sh
```

## Known Issues

### ~~Non-Deterministic Decoding~~ ✅ **SOLVED!**

**Problem** (was): Same IQ file produced different results on repeated runs (47-63% success rate)

**Cause identified**: GNU Radio scheduler fragments buffers dynamically, causing state machine to behave differently

**Solution implemented**: Buffer accumulation architecture
- Accumulates 21,000 samples before processing
- Guarantees consistent state machine execution
- **Result**: 100% deterministic (30/30 tests passed)

See commit `02cf681` for implementation details.

## Documentation

- [`ANALYSE_BUG_NON_DETERMINISME.md`](ANALYSE_BUG_NON_DETERMINISME.md) - Complete technical analysis of non-determinism issue
- [`PLAN_REFACTOR_BUFFER_CIRCULAIRE.md`](PLAN_REFACTOR_BUFFER_CIRCULAIRE.md) - Proposed refactoring plan
- [`RESUME_FINAL.md`](RESUME_FINAL.md) - Quick summary and status

## Contributing

Contributions are welcome! Areas needing help:

1. **Buffer accumulation implementation** (see plan document)
2. **Testing with real RTL-SDR captures**
3. **Performance optimization**
4. **Documentation improvements**

Please open an issue before starting major work.

## References

- [COSPAS-SARSAT System](https://www.cospas-sarsat.int/)
- [C/S T.001 Specification](https://www.cospas-sarsat.int/en/documents-pro/documents-specifications)
- [GNU Radio](https://www.gnuradio.org/)
- [gr-satellites COSPAS-SARSAT decoder](https://github.com/daniestevez/gr-satellites)

## License

[Your license choice - typically GPL v3 for GNU Radio modules]

## Author

F4MLV

## Acknowledgments

- Original COSPAS-SARSAT specification documents
- GNU Radio community
- Claude (Anthropic) for debugging assistance
