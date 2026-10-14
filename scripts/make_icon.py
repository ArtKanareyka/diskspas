"""Generate assets/icon.ico and assets/icon.png (lifebuoy on a blue-violet tile). Pure standard library."""
import math
import os
import struct
import sys
import zlib

BLUE, VIOLET, ORANGE, WHITE = (79, 109, 245), (139, 92, 246), (255, 122, 69), (255, 255, 255)


def sample(x, y):
    """Colour at a point of the 64x64 design, or None if outside the rounded tile."""
    dx = max(15 - x, x - 49, 0)
    dy = max(15 - y, y - 49, 0)
    if x < 0 or y < 0 or x > 64 or y > 64 or dx * dx + dy * dy > 225:
        return None
    d = math.hypot(x - 32, y - 32)
    if 9.5 <= d <= 20.5:
        angle = math.degrees(math.atan2(y - 32, x - 32))
        return ORANGE if ((angle + 22.5) % 90) < 45 else WHITE
    t = (x + y) / 128
    return tuple(round(BLUE[i] + (VIOLET[i] - BLUE[i]) * t) for i in range(3))


def render_png(size, ss=3):
    rows = bytearray()
    n = ss * ss
    for py in range(size):
        rows.append(0)
        for px in range(size):
            r = g = b = hit = 0
            for sy in range(ss):
                for sx in range(ss):
                    c = sample((px + (sx + .5) / ss) / size * 64, (py + (sy + .5) / ss) / size * 64)
                    if c:
                        r, g, b, hit = r + c[0], g + c[1], b + c[2], hit + 1
            rows += bytes(4) if not hit else bytes((r // hit, g // hit, b // hit, 255 * hit // n))

    def chunk(tag, data):
        body = tag + data
        return struct.pack(">I", len(data)) + body + struct.pack(">I", zlib.crc32(body) & 0xFFFFFFFF)

    return (b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", struct.pack(">IIBBBBB", size, size, 8, 6, 0, 0, 0))
            + chunk(b"IDAT", zlib.compress(bytes(rows), 9)) + chunk(b"IEND", b""))


def main(out_dir):
    os.makedirs(out_dir, exist_ok=True)
    sizes = [16, 32, 48, 256]
    pngs = [render_png(s, 4 if s < 100 else 3) for s in sizes]
    with open(os.path.join(out_dir, "icon.png"), "wb") as f:
        f.write(pngs[-1])
    head = struct.pack("<HHH", 0, 1, len(sizes))
    offset = 6 + 16 * len(sizes)
    entries = b""
    for s, png in zip(sizes, pngs):
        entries += struct.pack("<BBBBHHII", s % 256, s % 256, 0, 0, 1, 32, len(png), offset)
        offset += len(png)
    with open(os.path.join(out_dir, "icon.ico"), "wb") as f:
        f.write(head + entries + b"".join(pngs))
    print("written:", [os.path.getsize(os.path.join(out_dir, n)) for n in ("icon.png", "icon.ico")], "bytes")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "assets")
