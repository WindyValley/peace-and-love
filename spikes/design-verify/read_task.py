"""读取任务卡内容（绕过 BOM/CRLF 导致的二进制误判）"""
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
name = sys.argv[1] if len(sys.argv) > 1 else "T-SETUP-003"
f = ROOT / "docs" / "tasks" / f"{name}.md"
print(f.read_text(encoding="utf-8-sig"))
