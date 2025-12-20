import sys
import struct
import binascii

# See https://github.com/f4exb/sdrangel/tree/master/plugins/samplesource/filesource

data = open(sys.argv[1], "rb").read()
out = open(sys.argv[2], "wb")

w = bytearray()
w += struct.pack("<I", 500000)  # Sample rate
w += struct.pack("<Q", 868000000)  # Center freq Hz
w += struct.pack("<Q", 0)  # Timestamp
w += struct.pack("<I", 16)  # Sample size 16 or 24 ?
w += struct.pack("<I", 0)  # Padding
out.write(w)
out.write(struct.pack("<I", binascii.crc32(w)))  # CRC32
out.write(data)
