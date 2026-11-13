import struct, zlib, hashlib


def region_digest(data, box, energy=False):
    assert data[:8] == b"\x89PNG\r\n\x1a\n"
    pos = 8
    packed = bytearray()
    size = None
    while pos < len(data):
        length = struct.unpack(">I", data[pos : pos + 4])[0]
        kind = data[pos + 4 : pos + 8]
        chunk = data[pos + 8 : pos + 8 + length]
        pos += 12 + length
        if kind == b"IHDR":
            w, h, depth, color, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", chunk
            )
            assert depth == 8 and color in (2, 6) and interlace == 0
            size = (w, h)
            bpp = 3 if color == 2 else 4
        elif kind == b"IDAT":
            packed.extend(chunk)
        elif kind == b"IEND":
            break
    raw = zlib.decompress(packed)
    stride = w * bpp
    rows = []
    prior = bytearray(stride)
    offset = 0
    for _ in range(h):
        mode = raw[offset]
        offset += 1
        row = bytearray(raw[offset : offset + stride])
        offset += stride
        for x in range(stride):
            a = row[x - bpp] if x >= bpp else 0
            b = prior[x]
            c = prior[x - bpp] if x >= bpp else 0
            if mode == 1:
                value = a
            elif mode == 2:
                value = b
            elif mode == 3:
                value = (a + b) // 2
            elif mode == 4:
                p = a + b - c
                pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
                value = a if pa <= pb and pa <= pc else b if pb <= pc else c
            else:
                assert mode == 0
                value = 0
            row[x] = (row[x] + value) & 255
        rows.append(row)
        prior = row
    left, top, right, bottom = box
    if energy:
        return sum(
            max(0, rows[y][x * bpp + 2] - rows[y][x * bpp])
            for y in range(top, min(bottom, h))
            for x in range(left, min(right, w))
            if 28**2 < (x - 500) ** 2 + (y - 378) ** 2 < 49**2
        )
    return hashlib.sha256(
        b"".join(rows[y][left * bpp : right * bpp] for y in range(top, min(bottom, h)))
    ).hexdigest()
