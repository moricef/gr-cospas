# gr-cospas

**GNU Radio module for COSPAS-SARSAT 406 MHz beacon decoding**

## Quick Start

```bash
# Installation
mkdir build && cd build
cmake .. && make -j$(nproc) && sudo make install

# Run scanner
python3 scripts/scan406_iq.py 406.000 406.100 55 7
```

## Features

- **1G Beacons**: 80-100% success rate (BPSK, 400 bps)
  - Strong signals (local): 100% success
  - Weak signals (80km distance): 80-100% success
- **Autocorrelation burst detection**: Inspired by dec406_V7 algorithm
- **Adaptive thresholds**: Automatic adjustment based on signal strength (SNR)
  - Strong signals: strict phase variance threshold (0.15 rad)
  - Weak signals: relaxed threshold (0.7 rad)
  - Linear interpolation for intermediate levels
- **Real-time I/Q**: Direct RTL-SDR integration
- **Auto-scan**: rtl_power frequency detection
- **Email alerts**: Immediate notification on detection
- **Continuous operation**: 56s cycles with USB reset

## Architecture

### Signal Processing Chain

```
RTL-SDR (240 kHz)
    ↓ Decimation (÷6)
40 kHz I/Q samples
    ↓ Lowpass filter (20 kHz)
Filtered signal
    ↓ Normalizer (×0.15)
Normalized I/Q
    ↓ Burst Detector (autocorrelation, adaptive threshold)
Detected bursts
    ↓ Burst Router (1G/2G classification)
1G bursts only
    ↓ BPSK Demodulator (adaptive phase variance, freq tracking)
Demodulated bits
    ↓ Frame Parser (CRC validation)
Decoded frame (112 or 144 bits)
    ↓ Channel Filter (authorized frequencies)
Email Alert
```

### Core Components

**C++ Blocks** (`lib/`):
- `cospas_burst_detector`: Autocorrelation-based burst detection (dec406_V7 algorithm)
- `burst_router`: Routes bursts to 1G or 2G demodulator
- `cospas_sarsat_demodulator`: BPSK demodulation with adaptive thresholds
  - Automatic phase variance adjustment (0.15-0.7 rad)
  - Frequency offset correction with PLL
  - Bit synchronization validation (≥13/15 bits)
- `dec406_v1g`: 1G frame decoder with orbitography support

**Python Modules** (`python/cospas/`):
- `cospas_generator`: Beacon signal synthesis (test)
- `decode_monitor`: Frame completion tracking via PMT messages

**Scanner** (`scripts/`):
- `scan406_iq.py`: Production scanner with continuous operation

## Usage

### Basic Scan

Scan a frequency range and monitor for beacons:

```bash
python3 scripts/scan406_iq.py 406.000 406.100 55 7
```

**Arguments:**
- `f1_MHz`: Start frequency (MHz)
- `f2_MHz`: End frequency (MHz) - use same as f1 for fixed frequency
- `ppm`: RTL-SDR frequency correction (default: 0)
- `snr_threshold`: Detection threshold in dB above noise (default: 7)

**Examples:**

```bash
# Scan 406.0-406.1 MHz with 55 ppm correction
python3 scripts/scan406_iq.py 406.000 406.100 55 7

# Monitor fixed frequency 406.040 MHz
python3 scripts/scan406_iq.py 406.040 406.040 55 7

# More sensitive detection (5 dB threshold)
python3 scripts/scan406_iq.py 406.000 406.100 55 5
```

## Performance

### Validation Results

Tested with RTL-SDR on real CNES test beacons:

| Scenario | Success Rate | Notes |
|----------|--------------|-------|
| **Local (403.040 MHz)** | 100% | Strong signal, 6/6 bursts decoded |
| **Distant (406.022 MHz, 80km)** | 80-100% | Weak signal, adaptive threshold at 0.7 rad |
| **Distant (406.051 MHz)** | 33% | Very weak signal, new beacon detected (Country 228) |

**Key Features:**
- **Automatic adaptation**: No manual tuning required
- **Robust to noise**: Correct rejection of false positives (residual >0.3 rad)
- **CRC validation**: All decoded frames pass CRC1 check
- **Multiple beacons**: Simultaneous detection of 3 different beacons

### Operation Cycle

The scanner runs in continuous cycles:

1. **Frequency Scan** (55s): `rtl_power` scans the range and finds strongest signal
2. **Signal Capture** (56s): Flowgraph opens and captures continuously
   - Multiple frames can be detected during this period
   - Email sent immediately after each frame detection
   - RTL-SDR stays open for stability
3. **USB Reset**: Device reset between cycles to prevent lock-ups
4. **Loop**: Returns to step 1

## Configuration

### Email Alerts

Create `data/config_mail.txt`:

```ini
utilisateur=your.email@gmail.com
password=app_password
destinataires=alert@example.com
smtp_serveur=smtp.gmail.com:587
log_file=../data/mail.log
```

**Note**: For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

### RTL-SDR Setup

**Find PPM correction:**
```bash
rtl_test -p
# Let it run for ~5 minutes, note the final PPM value
```

**Test RTL-SDR:**
```bash
rtl_test -t
rtl_sdr -f 406040000 -s 240000 - | hexdump -C | head
```

**Reset USB device** (if needed):
```bash
sudo ./utils/reset_usb /dev/bus/usb/001/XXX
```

### Channel Filtering

Only authorized COSPAS-SARSAT channels trigger email alerts:

| Channel | Frequency | Status | Alert |
|---------|-----------|--------|-------|
| A | 406.022 MHz | System/Calibration | ❌ Filtered |
| B | 406.025 MHz | Active (TA < 2002) | ✅ |
| C | 406.028 MHz | Active (TA < 2007) | ✅ |
| D | 406.031 MHz | Active (TA < 2025) | ✅ |
| F | 406.037 MHz | Active (TA < 2012) | ✅ |
| G | 406.040 MHz | Active (TA < 2017) | ✅ |
| S | 406.076 MHz | Active (TA ≥ 2025) | ✅ |

Test channel at **403.040 MHz** is enabled for development (remove in production).

## Project Structure

```
lib/                   # C++ signal processing
python/cospas/         # Python utilities
scripts/               # Production scanners
examples/1g/           # 1G tests (100% deterministic)
examples/2g/           # 2G (in development)
```

## Troubleshooting

### No Signal Detected

**Check RTL-SDR:**
```bash
rtl_test -t  # Device should be found
```

**Verify frequency and PPM:**
```bash
# Test with known beacon or use gqrx to find exact frequency
python3 scripts/scan406_iq.py 406.040 406.040 55 7
```

**Lower SNR threshold:**
```bash
# Try 5 dB instead of 7 dB for weak signals
python3 scripts/scan406_iq.py 406.000 406.100 55 5
```

### CRC Errors / Failed Decoding

- **Check antenna**: Use proper 406 MHz antenna (1/4 wave = 18.4 cm)
- **Reduce interference**: Move away from strong RF sources
- **Verify PPM correction**: Run `rtl_test -p` for accurate value

### RTL-SDR Not Found

```bash
# Check device
lsusb | grep Realtek

# Blacklist DVB-T driver
echo 'blacklist dvb_usb_rtl28xxu' | sudo tee /etc/modprobe.d/blacklist-rtl.conf
sudo rmmod dvb_usb_rtl28xxu
```

### Email Not Sending

**Test sendemail:**
```bash
sendemail -f from@example.com -t to@example.com \
  -u "Test Subject" -m "Test message" \
  -s smtp.gmail.com:587 \
  -xu your.email@gmail.com -xp your_app_password \
  -o tls=yes
```

**Check logs:**
```bash
tail -f data/mail.log
```

## Documentation

- **1G Examples**: `examples/1g/README.md`
- **Architecture Details**: `docs/ARCHITECTURE_CIBLE.md`
- **2G Status**: `docs/ETAT_GENERATEUR_2G.md`

## Author

**F4MLV** - <f4mlv09@gmail.com>

## Credits

Part of the code is derived from F4EHY's work:
- **scan406** and **dec406** by F4EHY
- Original implementation: http://f4ehy.free.fr/406.htm

## References

- **COSPAS-SARSAT System**: https://www.cospas-sarsat.int/
- **GNU Radio**: https://www.gnuradio.org/
- **F4EHY's 406 MHz Tools**: http://f4ehy.free.fr/406.htm

## License

GNU General Public License v3.0

This program is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

See [LICENSE](LICENSE) file for details.

---

**Last Updated**: 2025-11-20
