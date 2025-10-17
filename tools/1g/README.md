# tools/1g - First Generation (1G) COSPAS-SARSAT Tools

**Status**: Empty (no 1G-specific tools yet)

## Overview

This directory is reserved for tools specific to **1st generation COSPAS-SARSAT beacons**.

### 1G Beacon Specifications
- **Modulation**: Biphase-L (Manchester)
- **Data Rate**: 400 bps
- **Frame Length**: 112 bits (short), 144 bits (long)
- **Error Detection**: CRC
- **Protocols**: Location (Standard, National, ELT-DT, RLS), User (Orbitography, Aviation, Maritime, Serial)

## Available Tools

Currently no 1G-specific tools. The 1G decoder is in `/lib/cospas_sarsat_decoder_impl.cc` and is fully functional.

For 1G examples and tests, see `/examples/1g/`.

## Related Directories

- `/examples/1g/` - 1G test scripts and examples
- `/lib/` - Core 1G decoder implementation (C++)
- `/python/cospas/` - 1G generator module

---

**Last Updated**: 2025-10-17
