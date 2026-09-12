"""Validate full PNG content, not merely the filename or eight-byte signature."""
from pathlib import Path
import struct
import zlib
import pytest

ROOT = Path(__file__).resolve().parents[1]
ASSETS = [
    ("custom_components/health_link/brand/icon.png", (256, 256)),
    ("custom_components/health_link/brand/logo.png", (600, 200)),
    ("custom_components/health_link/frontend/brand/logo.png", (600, 200)),
    ("assets/healthlink-icon.png", (256, 256)),
    ("assets/healthlink-logo-wide.png", (600, 200)),
]


def validate_png(data, expected_size):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    offset = 8
    compressed = bytearray()
    header = None
    end = False
    while offset < len(data):
        assert offset + 12 <= len(data), "Truncated PNG chunk header"
        length, kind = struct.unpack(">I4s", data[offset:offset+8])
        assert offset + length + 12 <= len(data), "Truncated PNG chunk payload"
        payload = data[offset+8:offset+8+length]
        crc, = struct.unpack(">I", data[offset+8+length:offset+12+length])
        assert zlib.crc32(kind + payload) & 0xffffffff == crc, "Invalid PNG CRC"
        if kind == b"IHDR": header = struct.unpack(">IIBBBBB", payload)
        if kind == b"IDAT": compressed.extend(payload)
        offset += length + 12
        if kind == b"IEND":
            end = True
            assert offset == len(data)
            break
    assert end and header and compressed, "Incomplete PNG"
    width, height, depth, color, compression, filtering, interlace = header
    assert (width, height) == expected_size
    assert (depth, color, compression, filtering, interlace) == (8, 6, 0, 0, 0)
    raw = zlib.decompress(compressed)
    assert len(raw) == height * (1 + width * 4), "Incomplete decoded pixels"


@pytest.mark.parametrize("name,size", ASSETS)
def test_approved_png_is_complete(name, size):
    validate_png((ROOT/name).read_bytes(), size)


def test_truncated_png_cannot_pass_release_validation():
    data = (ROOT/ASSETS[0][0]).read_bytes()
    with pytest.raises(AssertionError): validate_png(data[:len(data)//2], (256, 256))


def test_studio_and_native_brand_use_same_artwork():
    assert (ROOT/ASSETS[1][0]).read_bytes() == (ROOT/ASSETS[2][0]).read_bytes()
    assert (ROOT/ASSETS[0][0]).read_bytes() == (ROOT/ASSETS[3][0]).read_bytes()
