"""
生成占位 mod 图标（64x64 PNG）
================================
mod 元数据里声明了 icon.png，文件缺失会导致加载器警告。
先放一个占位图，正式美术资源由 T-REL-002 替换。

不依赖 Pillow —— 手写最小 PNG，避免引入构建期依赖。
"""
import struct
import zlib
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
SIZE = 64


def make_png(path: Path):
    """生成一个绿色渐变方块作为占位图标"""
    rows = []
    for y in range(SIZE):
        row = bytearray([0])  # filter type 0
        for x in range(SIZE):
            # 绿色调渐变，呼应「和平」主题
            r = 40 + (x * 60 // SIZE)
            g = 120 + (y * 90 // SIZE)
            b = 60 + ((x + y) * 40 // (SIZE * 2))
            row += bytes([r, min(g, 255), b])
        rows.append(bytes(row))
    raw = b"".join(rows)

    def chunk(tag: bytes, data: bytes) -> bytes:
        c = struct.pack(">I", len(data)) + tag + data
        return c + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)

    png = b"\x89PNG\r\n\x1a\n"
    # IHDR: width, height, bitdepth=8, colortype=2(RGB), 0,0,0
    png += chunk(b"IHDR", struct.pack(">IIBBBBB", SIZE, SIZE, 8, 2, 0, 0, 0))
    png += chunk(b"IDAT", zlib.compress(raw, 9))
    png += chunk(b"IEND", b"")

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return len(png)


targets = [
    ROOT / "common/src/main/resources/assets/peaceandlove/icon.png",
    ROOT / "fabric/src/main/resources/assets/peaceandlove/icon.png",
    ROOT / "neoforge/src/main/resources/icon.png",
]

for t in targets:
    n = make_png(t)
    print(f"  {t.relative_to(ROOT)}  ({n} bytes)")

print("\n占位图标已生成（正式素材由 T-REL-002 替换）")
