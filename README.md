# Indic OCR Benchmark

Seven open-source OCR engines tested on 20 Indian languages (printed, handwritten, degraded, forms).
Each engine ran alone: no vision model or LLM was used to help or correct it.

Engines: Indra OCR, Surya, PaddleOCR, EasyOCR, Tesseract, docTR, RapidOCR.

## See the results

| What | Where |
|---|---|
| Interactive dashboard (with evidence images) | `dashboard\index.html` (double-click) |
| PDF report (25 pages) | `report\Indic-OCR-Benchmark.pdf` |

## Folders

| Folder | Contents |
|---|---|
| `dashboard\` | Built dashboard page |
| `report\` | Built PDF report |
| `results\raw\` | Raw output of every engine on every image (the source of truth) |
| `results\dashboard_data.json` | Scores calculated from the raw output |
| `data\` | Test images and ground-truth text (`images\` and `gt\` per set) |
| `data_src\` | Downloaded source material used to make the test sets |
| `bench\` | All scripts |
| `envs\` | One Python environment per engine (don't edit) |
| `tessdata\` | Tesseract language packs |
| `logs\` | Run logs |
| `archive\` | Old scripts and results, kept just in case |

## Directions

Run these by double-clicking, or from a terminal in this folder.

- **Rebuild the dashboard:** `build_dashboard.cmd`
- **Rebuild the PDF:** `build_report.cmd`
- **Re-run an engine:** `run_engine.cmd tesseract`
  (engines: `tesseract easyocr doctr rapidocr paddleocr surya indra`).
  Finished images are skipped, so you can stop and resume.
  Add `--per-group 3` for slow engines (Surya, PaddleOCR, EasyOCR) to use 3 images per language and set.
  Then rebuild the dashboard and PDF.

## Scoring in one line

CER (character error rate) and WER (word error rate), computed on Unicode-normalised text and capped at 1 per image. Lower is better.

## Known limits

- No labelled data for Bodo, Dogri, Konkani, Garo, Kokborok, Lepcha, Limbu, Sikkimese; Khasi was not downloaded.
- Handwriting is scored only for Hindi and Tamil. Other handwriting crops are unlabelled (shown, not scored).
- Ten languages use rendered text, not scans.
- Surya, PaddleOCR and EasyOCR cells use only 3 images each (n=3).
- Speeds were measured with engines running in parallel, so they are inflated.
- EasyOCR fails on Tamil (a model-loading bug); the failures are recorded as errors.
