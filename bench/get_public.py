# Small public subset: FUNSD forms (words concatenated in reading order as ground truth).
from pathlib import Path
from datasets import load_dataset
out = Path("data/funsd"); (out / "images").mkdir(parents=True, exist_ok=True); (out / "gt").mkdir(exist_ok=True)
ds = load_dataset("nielsr/funsd-layoutlmv3", split="test[:20]")
for i, ex in enumerate(ds):
    ex["image"].convert("RGB").save(out / "images" / f"funsd_{i}.png")
    (out / "gt" / f"funsd_{i}.txt").write_text(" ".join(ex["tokens"]), encoding="utf-8")
print(len(ds), "funsd docs")
