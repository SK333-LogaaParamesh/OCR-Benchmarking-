"""Range-fetch a few MB at several offsets from each IIIT-INDIC-HW-WILD language tar and extract word crops
(CC BY 4.0 'iiit-indic-hw-wild' origin only). Output: data_src/wild/<lang>/<name>.png (unlabelled candidates)."""
import io, random, sys
from pathlib import Path
import requests
from PIL import Image
BASE = "https://huggingface.co/datasets/evanilalitha/IIIT-INDIC-HW-WILD/resolve/main/images/"
TARS = {"tel": "telugu", "ben": "bengali", "kan": "kannada", "guj": "gujarati", "mal": "malayalam"}
SIZE = {"telugu": 768593920, "bengali": 2253803520, "kannada": 755732480, "gujarati": 409620480, "malayalam": 689797120}
CHUNK, N_OFF, KEEP = 5 * 1024 * 1024, 6, 36
random.seed(5)
for code, name in TARS.items():
    out = Path("data_src/wild") / code; out.mkdir(parents=True, exist_ok=True)
    cands = []
    for k in range(N_OFF):
        off = (int(SIZE[name] * (k + 0.5) / N_OFF) // 512) * 512
        r = requests.get(BASE + name + ".tar", headers={"Range": f"bytes={off}-{off + CHUNK - 1}"}, timeout=180)
        buf = r.content; pos = 0
        while pos + 512 <= len(buf):
            if buf[pos + 257:pos + 262] == b"ustar":
                fname = buf[pos:pos + 100].split(b"\0")[0].decode(errors="ignore")
                size = int(buf[pos + 124:pos + 135].split(b"\0")[0].strip() or b"0", 8)
                data = buf[pos + 512:pos + 512 + size]
                if len(data) == size and "iiit-indic-hw-wild" in fname:
                    try:
                        im = Image.open(io.BytesIO(data)); w, h = im.size
                        if w >= 70 and h >= 32 and w / h < 8: cands.append((fname.split("/")[-1], data))
                    except Exception: pass
                pos += 512 + ((size + 511) // 512) * 512
            else: pos += 512
    random.shuffle(cands)
    for fn, data in cands[:KEEP]: (out / fn).write_bytes(data)
    print(code, "candidates", len(cands), "kept", min(len(cands), KEEP), flush=True)
