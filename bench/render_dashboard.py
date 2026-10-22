"""Build the standalone local dashboard: dashboard/index.html (all data, images and scripts inline; works offline).
Run bench/build_dashboard_data.py first (build_dashboard.cmd does both)."""
import re
from pathlib import Path
R = Path(__file__).resolve().parent.parent
t = (R / "bench/dashboard_template.html").read_text(encoding="utf-8")
d = (R / "results/dashboard_data.json").read_text(encoding="utf-8").replace("</", "<\/")
t = t.replace("/*__DATA__*/null", d)
t = re.sub(r'<link rel="(preconnect|stylesheet)"[^>]*>\s*', "", t)          # no web fonts: stays fully offline, system fonts are in the stacks
t = t.replace('<meta name="claude:viewport-fit-sides" content="cover">\n', "")
split = t.index("</style>") + len("</style>")
page = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n<meta name="viewport" content="width=device-width,initial-scale=1">\n'
        '<style>html{color-scheme:light}body{margin:0}img{max-width:100%}[hidden]{display:none!important}</style>\n'
        + t[:split] + "\n</head>\n<body>\n" + t[split:] + "\n</body>\n</html>\n")
out = R / "dashboard"; out.mkdir(exist_ok=True)
(out / "index.html").write_text(page, encoding="utf-8")
print(out / "index.html", len(page) // 1024, "KB")
