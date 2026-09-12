"""检查 03-tasks 下文件的编码，并统一为无 BOM 的 UTF-8 (LF)"""
from pathlib import Path

OUT = Path(__file__).resolve().parent.parent.parent / "03-tasks"

fixed = 0
for f in sorted(OUT.glob("*.md")):
    raw = f.read_bytes()
    head = raw[:4]
    note = []
    if raw.startswith(b"\xef\xbb\xbf"):
        note.append("BOM")
        raw = raw[3:]
    if b"\x00" in raw[:2000]:
        note.append("NUL!")
    if b"\r\n" in raw:
        note.append("CRLF")
        raw = raw.replace(b"\r\n", b"\n")
    if note:
        f.write_bytes(raw)
        fixed += 1
        print(f"{f.name:22s} 修正: {','.join(note)}")

print(f"\n共修正 {fixed} 个文件")

# 复验第一个文件
sample = OUT / "T-ANGER-003.md"
raw = sample.read_bytes()
print(f"\n复验 {sample.name}:")
print(f"  前 4 字节: {raw[:4]!r}")
print(f"  含 NUL: {b'NUL' if chr(0).encode() in raw else b'no'}")
has_crlf = b"\r\n" in raw
print(f"  含 CRLF: {has_crlf}")
print("\n--- 前 20 行 ---")
print("\n".join(raw.decode("utf-8").splitlines()[:20]))
