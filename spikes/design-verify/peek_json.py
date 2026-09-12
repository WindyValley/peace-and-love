import json
from pathlib import Path

p = Path(__file__).resolve().parent.parent / "r3-ai" / "neutralization_plan_v3.json"
d = json.loads(p.read_text(encoding="utf-8"))
print("顶层键:", list(d.keys()))
print("\ngoal_system[0]:")
print(json.dumps(d["goal_system"][0], ensure_ascii=False, indent=2))
print("\nbrain_system[0]:")
print(json.dumps(d["brain_system"][0], ensure_ascii=False, indent=2))
