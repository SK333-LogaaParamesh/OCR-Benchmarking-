"""Build report/Indic-OCR-Benchmark.pdf from results/dashboard_data.json (run build_dashboard_data.py first).
Writes report/report.html (print-styled) and has headless Edge print it to PDF."""
import html, json, subprocess, time
from pathlib import Path

R = Path(__file__).resolve().parent.parent
D = json.loads((R / "results/dashboard_data.json").read_text(encoding="utf-8"))
EDGE = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
E = [e for e in D["engines"] if D["counts"].get(e)]
LANG_ORDER = ["hin", "tam", "tel", "kan"] + [l for l in D["langs"] if l not in ("hin", "tam", "tel", "kan")]
SPOT = ("hin", "tam", "tel", "kan")
COLOR = {"indra": "#2a78d6", "surya": "#eb6834", "paddleocr": "#1baf7a", "easyocr": "#eda100", "tesseract": "#e87ba4", "doctr": "#008300", "rapidocr": "#6250d6"}
TAB = {"printed": "Printed text, rendered", "printed_bench": "Printed text, real corpus", "printed_deg": "Printed text, degraded",
       "handwritten": "Handwritten words", "handwritten_deg": "Handwritten words, degraded", "forms": "Forms (English)", "handwritten_wild": "Handwritten words, unlabelled"}
NOTE = {
    "printed": "Clean printed lines in 20 Indian languages plus English. Real FLORES-200 sentences drawn by a browser with correct script shaping.",
    "printed_bench": "Printed line images from the OCR-Bench1000 corpus (Bengali, Gujarati, Kannada, Malayalam, Marathi, Punjabi, Telugu; 30 images each): mixed fonts, long lines, digits.",
    "printed_deg": "The rendered printed set after heavy damage. Same text, same ground truth.",
    "handwritten": "Real handwritten words (IIIT-INDIC-HW-WORDS). Hindi and Tamil only: the only labelled handwriting sets that could be obtained.",
    "handwritten_deg": "The handwritten words after heavy damage.",
    "forms": "Full-page English form scans (FUNSD), scored against words in reading order.",
    "handwritten_wild": "Telugu, Bengali, Kannada, Gujarati and Malayalam word crops with no transcriptions. Not scored; raw outputs shown.",
}
esc = lambda s: html.escape(str(s))
pct = lambda x: "–" if x is None else f"{round(x * 100)}%"
mean = lambda a: sum(a) / len(a) if a else None

def ramp(v):   # white -> slate, text flips to white on dark cells
    v = min(max(v, 0), 1); lo, hi = (236, 239, 243), (47, 68, 104)
    c = tuple(round(lo[i] + (hi[i] - lo[i]) * v) for i in range(3))
    return f"background:rgb{c};color:{'#fff' if v > .52 else '#14181f'}"

def cell(c, l, e): return D["heat"].get(c, {}).get(l, {}).get(e)
def ok(x): return x and x["n"] > 0
def langs_of(c): return [l for l in LANG_ORDER if D["total"].get(c, {}).get(l)]

def agg(c, e, ls):
    cs = [cell(c, l, e) for l in ls if ok(cell(c, l, e))]
    n = sum(x["ran"] for x in cs)
    return dict(cer=mean([x["cer"] for x in cs]), wer=mean([x["wer"] for x in cs]), n=sum(x["n"] for x in cs), langs=len(cs),
                sec=sum(x["ran"] * (x["sec"] or 0) for x in cs) / n if n else None, empty=sum(x["empty"] for x in cs) / n if n else None)

def ranking_table(c):
    ls = langs_of(c); rows = []
    for e in E:
        a = agg(c, e, ls); nat = agg(c, e, [l for l in ls if (cell(c, l, e) or {}).get("mode") == "native"])
        rows.append((e, a, nat, sum(1 for l in ls if ok(cell(c, l, e)) and cell(c, l, e)["mode"] == "native")))
    rows.sort(key=lambda r: r[1]["cer"] if r[1]["cer"] is not None else 9)
    h = "<table class='rank'><tr><th>Engine</th><th>CER all languages</th><th>CER native only</th><th>WER</th><th>No text</th><th>Native langs</th><th>Sec/img</th><th>Images</th></tr>"
    for e, a, nat, nn in rows:
        sec = "–" if a["sec"] is None else (f"{a['sec']:.1f}" if a["sec"] < 10 else str(round(a["sec"])))
        h += (f"<tr><td><span class='dot' style='background:{COLOR[e]}'></span><b>{D['meta'][e]['name']}</b></td>"
              f"<td class='n'>{'no data' if a['cer'] is None else pct(a['cer'])}</td><td class='n'>{pct(nat['cer'])} <small>({nat['langs']})</small></td>"
              f"<td class='n'>{pct(a['wer'])}</td><td class='n'>{pct(a['empty'])}</td><td class='n'>{nn}/{len(ls)}</td><td class='n'>{sec}</td><td class='n'>{a['n']}</td></tr>")
    return h + "</table>"

def heat_table(c):
    ls = langs_of(c); h = "<table class='heat'><tr><th></th>" + "".join(f"<th>{D['meta'][e]['name']}</th>" for e in E) + "</tr>"
    for l in ls:
        h += f"<tr><th class='l'>{D['langs'][l]}</th>"
        for e in E:
            x = cell(c, l, e)
            if ok(x):
                tag = {"script": "≈", "none": "∅"}.get(x["mode"], "")
                h += f"<td style='{ramp(x['cer'])}'>{round(x['cer'] * 100)}<sup>{tag}</sup><small> n{x['n']}</small></td>"
            elif x and x["ran"] and x["err"] >= x["ran"]: h += "<td class='err'>err</td>"
            else: h += "<td class='nr'>·</td>"
        h += "</tr>"
    return h + "</table><p class='key'>CER %, lower is better; n = images scored. No mark: model built for the language. ≈ model for a related language in the same script. ∅ no relevant model, default Latin or English model ran. err = failed on every image. · = not run.</p>"

def robustness():
    out = ""
    for dc, title in (("printed_deg", "Printed text"), ("handwritten_deg", "Handwritten words")):
        P = D["paired"].get(dc, {})
        out += f"<h3>{title}: clean vs degraded CER</h3><table class='rank'><tr><th>Engine</th><th>Clean</th><th>Degraded</th><th>Images</th></tr>"
        for e in sorted(P, key=lambda e: P[e]["degraded"]):
            out += f"<tr><td><span class='dot' style='background:{COLOR[e]}'></span><b>{D['meta'][e]['name']}</b></td><td class='n'>{pct(P[e]['clean'])}</td><td class='n'>{pct(P[e]['degraded'])}</td><td class='n'>{P[e]['n']}</td></tr>"
        out += "</table>" if P else "<tr><td colspan=4>No engine has results on both versions yet.</td></tr></table>"
    return out

def evidence(cond, langs, per):
    out = ""
    for l in langs:
        ss = [s for s in D["samples"] if s["cond"] == cond and s["lang"] == l][:per]
        for s in ss:
            rows = sorted(((e, s["results"][e]) for e in D["engines"] if e in s["results"]), key=lambda t: t[1]["cer"] if t[1]["cer"] is not None else 9)
            imgs = (f"<figure><figcaption>Original</figcaption><img src='{s['orig']}'></figure>" if s.get("orig") else "") + f"<figure><figcaption>{'Degraded (test input)' if s.get('orig') else 'Test input'}</figcaption><img src='{s['img']}'></figure>"
            gt = f"<div class='gt'><b>Ground truth</b> {esc(s['ref']) or '(empty)'}</div>" if s["ref"] is not None else "<div class='gt none'><b>Ground truth</b> none: this image has no transcription</div>"
            t = "<table class='out'>"
            for e, r in rows:
                cer = "–" if r["cer"] is None else pct(r["cer"])
                txt = f"<i>failed: {esc(r['err'] or 'error')}</i>" if r["status"] == "error" else (esc(r["hyp"]) or "<i>returned no text</i>")
                mk = {"script": " ≈", "none": " ∅"}.get(r.get("mode"), "")
                t += f"<tr><td class='e'><span class='dot' style='background:{COLOR[e]}'></span>{D['meta'][e]['name']}{mk}</td><td class='n'>{cer}</td><td class='o'>{txt}</td></tr>"
            out += f"<div class='card'><div class='ch'>{D['langs'][l]} · {esc(s['id'])} · {esc(D['dsLabel'][s['dataset']])}</div><div class='imgs'>{imgs}</div>{gt}{t}</table></div>"
    return out

gaps = """<ul>
<li><b>No labelled OCR data found:</b> Bodo, Dogri, Konkani (not in FLORES-200, no public OCR set located); Garo, Kokborok, Lepcha, Limbu, Sikkimese (no public text or OCR data located); Khasi (Hugging Face sets exist but were not downloaded).</li>
<li><b>Handwriting with scores:</b> only Hindi and Tamil (IIIT-INDIC-HW-WORDS). Telugu, Bengali, Kannada, Gujarati and Malayalam crops from IIIT-INDIC-HW-WILD have no transcriptions, so they are shown unscored. Odia and Punjabi handwriting exists only inside PHDIndic_11 (IEEE DataPort), which could not be fetched. DohaScript has no text labels; IIIT-HW-Telugu is a 3.6 GB nested archive.</li>
<li><b>Why the unlabelled words were not transcribed here:</b> a vision model reading these crops was unreliable (roughly one word in eight had a trustworthy reading, all in clear hands), so the labels would be wrong or biased toward easy writing. A native reader labelling the crops would fix this.</li>
<li><b>Rendered text, not scans:</b> Assamese, Kashmiri, Maithili, Manipuri, Nepali, Sanskrit, Santali, Sindhi, Urdu and Mizo use real FLORES-200 sentences drawn by a browser. They test script coverage, not paper. Manipuri is tested in Bengali script.</li></ul>"""
method = """<ul>
<li><b>OCR only.</b> Each engine ran alone. No language model, vision model, spell-check or post-correction touched any output. Worker agents only launched each engine and checked the result files.</li>
<li><b>Every engine on every language.</b> Where an engine has no model for a language it still ran, using the closest model it has (marked ≈ or ∅).</li>
<li><b>No preprocessing.</b> Every engine reads the raw image. Tesseract uses the documented page-segmentation mode for the input type (word, line or full page); its default mode returned nothing on single lines.</li>
<li><b>Scoring.</b> Unicode NFC, whitespace collapsed; CER is edit distance over reference characters, capped at 100% per image, then averaged. "Native only" averages just the languages an engine was built for.</li>
<li><b>Hardware.</b> One Windows laptop, 8 logical cores, no GPU. Engines ran in parallel, so seconds-per-image are indicative and inflated for every engine.</li>
<li><b>Subsamples.</b> Indra, Tesseract, docTR and RapidOCR ran every image. Surya, PaddleOCR and EasyOCR ran 3 images per language and test set because of CPU speed, so their cells are small samples.</li>
<li><b>Versions and limits.</b> Surya is surya-ocr 0.17 because the current release needs a binary this machine's policy blocks. EasyOCR's Tamil model fails to load in v1.7.2 (shown as an error). Tesseract has no packs for Maithili, Kashmiri, Manipuri, Santali or Mizo. Most test images are single lines or words, so results say little about full pages, tables or photographed documents.</li></ul>"""

CSS = """
@page{size:A4;margin:13mm 12mm}
*{box-sizing:border-box}body{font:9.5pt/1.45 'Segoe UI','Nirmala UI',system-ui,sans-serif;color:#14181f;margin:0}
h1{font-size:25pt;margin:0 0 4pt;letter-spacing:-.02em}h2{font-size:14pt;margin:0 0 3pt;padding-top:2pt;break-after:avoid}h3{font-size:10.5pt;margin:10pt 0 4pt;break-after:avoid}
p{margin:3pt 0 6pt}.sub{color:#4a5463}.lede{color:#4a5463;margin-bottom:6pt}
section{margin-top:14pt}.pb{break-before:page}
table{border-collapse:collapse;width:100%;break-inside:auto}tr{break-inside:avoid}
th{font-size:7.5pt;text-transform:uppercase;letter-spacing:.05em;color:#6b7585;text-align:left;padding:3pt 5pt;border-bottom:1px solid #c9d0da}
td{padding:4pt 5pt;border-bottom:1px solid #e4e8ee;vertical-align:top}.n{font-family:Consolas,monospace;text-align:right;white-space:nowrap}
.dot{display:inline-block;width:7pt;height:7pt;border-radius:2pt;margin-right:5pt}
.heat td{text-align:center;padding:2.5pt 2pt;font:8pt Consolas,monospace;border:1.5px solid #fff}.heat th.l{font-size:8pt;text-transform:none;letter-spacing:0;color:#14181f;white-space:nowrap;border:0}
.heat small{font-size:5.5pt;opacity:.7}.heat sup{font-size:6pt}.heat td.err{color:#b3372f;box-shadow:inset 0 0 0 1px #b3372f;background:#fff}.heat td.nr{color:#9aa3b0;background:#f5f6f8}
.key{font-size:7.5pt;color:#6b7585}
.card{border:1px solid #d9dee6;border-radius:4pt;margin:0 0 8pt;break-inside:avoid;overflow:hidden}.ch{background:#eceff3;padding:3pt 7pt;font:7.5pt Consolas,monospace;color:#4a5463}
.imgs{display:flex;gap:8pt;padding:6pt 7pt 3pt}figure{margin:0;flex:1;min-width:0}figcaption{font-size:6.5pt;text-transform:uppercase;letter-spacing:.06em;color:#6b7585}
figure img{max-width:100%;max-height:55mm;border:1px solid #d9dee6;display:block}
.gt{margin:3pt 7pt 5pt;padding:4pt 7pt;border-left:3px solid #1f7a4d;background:#f1f4f7;font-size:10.5pt}.gt.none{border-color:#8b95a5;font-size:8.5pt}.gt b{display:block;font-size:6.5pt;text-transform:uppercase;letter-spacing:.06em;color:#6b7585}
table.out td{font-size:9pt}table.out td.e{white-space:nowrap;width:26%;font-weight:600}table.out td.o{font-size:10pt;overflow-wrap:anywhere}table.out td.n{width:9%}
ul{margin:3pt 0;padding-left:14pt}li{margin:3pt 0}small{color:#6b7585}
"""

def section(c):
    return (f"<section class='pb'><h2>{TAB[c]}</h2><p class='lede'>{NOTE[c]}</p>"
            + ("" if c == "handwritten_wild" else f"<h3>Ranking</h3>{ranking_table(c)}<h3>Every language, every engine</h3>{heat_table(c)}"))

body = f"""<h1>Indic OCR Benchmark</h1>
<p class='sub'>Seven open-source OCR engines run on CPU against {D['nImages']} images across 20 Indian languages and English. Each engine was run on every language with no language model, vision model or post-correction. Generated {time.strftime('%d %B %Y')}.</p>
<section><h2>Summary: printed text, rendered</h2>{ranking_table('printed')}<p class='key'>Interim numbers are marked by small image counts; engines that ran a subsample show it in the Images column.</p></section>
<section><h2>What damage does to accuracy</h2><p class='lede'>The same images scored twice, clean and degraded: one geometric change (tilt or perspective) plus three of blur, noise, speckle, low resolution, JPEG artefacts, uneven light, stains and ink bleed.</p>{robustness()}</section>
"""
for c in ("printed", "printed_bench", "printed_deg", "handwritten", "handwritten_deg", "forms"):
    if D["total"].get(c): body += section(c)
body += "<section class='pb'><h2>Evidence: Hindi, Tamil, Telugu, Kannada</h2><p class='lede'>The input image, the ground truth and the exact text each engine returned. All samples are in the interactive dashboard; these are the spotlight languages.</p>"
for c in ("printed", "printed_deg", "handwritten", "handwritten_deg"):
    ls = [l for l in SPOT if any(s["cond"] == c and s["lang"] == l for s in D["samples"])]
    if ls: body += f"<h3>{TAB[c]}</h3>" + evidence(c, ls, 2 if c.startswith("printed") else 3)
if D["total"].get("handwritten_wild"):
    body += f"<h3>{TAB['handwritten_wild']}</h3><p class='lede'>{NOTE['handwritten_wild']}</p>" + evidence("handwritten_wild", ["tel", "kan"], 4)
body += f"</section><section class='pb'><h2>What was not tested</h2>{gaps}</section><section><h2>How this was run</h2>{method}</section>"

out = R / "report"; out.mkdir(exist_ok=True)
(out / "report.html").write_text(f"<!doctype html><html lang='en'><head><meta charset='utf-8'><title>Indic OCR Benchmark</title><style>{CSS}</style></head><body>{body}</body></html>", encoding="utf-8")
pdf = out / "Indic-OCR-Benchmark.pdf"; pdf.unlink(missing_ok=True)
prof = Path(__import__("tempfile").mkdtemp())
proc = subprocess.Popen([EDGE, "--headless=new", "--disable-gpu", "--no-pdf-header-footer", f"--print-to-pdf={pdf}", f"--user-data-dir={prof}", "--no-first-run",
                         (out / "report.html").as_uri()], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
for _ in range(240):
    if pdf.exists() and pdf.stat().st_size > 0: time.sleep(1.5); break
    time.sleep(0.5)
subprocess.run(["taskkill", "/F", "/T", "/PID", str(proc.pid)], capture_output=True)
print(pdf, pdf.stat().st_size // 1024 if pdf.exists() else "NOT WRITTEN", "KB")
