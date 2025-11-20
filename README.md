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

- **1G Beacons**: 92-100% success rate (BPSK, 400 bps)
- **Real-time I/Q**: Direct RTL-SDR integration
- **Auto-scan**: rtl_power frequency detection
- **Email alerts**: Immediate notification on detection
- **Continuous operation**: 56s cycles with USB reset

## Architecture

```
RTL-SDR → Decimator → Lowpass → Burst Detector → BPSK Demod → CRC Check → Alert
```

## scan406_iq.py Usage

```bash
python3 scripts/scan406_iq.py <f1_MHz> <f2_MHz> [ppm] [snr_threshold]

# Examples:
python3 scripts/scan406_iq.py 406.000 406.100 55 7  # Scan range
python3 scripts/scan406_iq.py 406.040 406.040 55 7  # Fixed frequency
```

The scanner performs:
1. Frequency scan with rtl_power (55s)
2. Continuous capture on detected frequency (56s)
3. Immediate email alerts on beacon detection
4. Automatic USB reset between cycles

## Email Configuration

Create `data/config_mail.txt`:

```ini
utilisateur=your.email@gmail.com
password=app_password
destinataires=alert@example.com
smtp_serveur=smtp.gmail.com:587
```

## Project Structure

```
lib/                   # C++ signal processing
python/cospas/         # Python utilities
scripts/               # Production scanners
examples/1g/           # 1G tests (100% deterministic)
examples/2g/           # 2G (in development)
```

## Documentation

- **1G Examples**: `examples/1g/README.md`
- **Architecture**: `docs/ARCHITECTURE_CIBLE.md`
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
