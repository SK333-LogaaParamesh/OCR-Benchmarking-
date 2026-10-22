import random, sys
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont, ImageFilter

FONT = "C:/Windows/Fonts/Nirmala.ttc"
ARIAL = "C:/Windows/Fonts/arial.ttf"
TEXTS = {
    "eng": ["The quick brown fox jumps over the lazy dog", "Invoice total due within thirty days of receipt",
            "Optical character recognition converts images to text", "Meeting scheduled for Monday at 10:30 in room 4B",
            "Please keep this receipt for your records"],
    "hin": ["भारत एक विशाल और विविधताओं से भरा देश है", "आज मौसम बहुत सुहावना है", "कृपया अपनी रसीद सुरक्षित रखें",
            "यह एक परीक्षण वाक्य है", "हम सब मिलकर काम करेंगे"],
    "tam": ["தமிழ் ஒரு பழமையான மொழி", "இன்று வானிலை மிகவும் நன்றாக உள்ளது", "உங்கள் ரசீதை பத்திரமாக வைத்திருக்கவும்",
            "இது ஒரு சோதனை வாக்கியம்", "நாம் அனைவரும் சேர்ந்து வேலை செய்வோம்"],
    "ben": ["বাংলা একটি সুন্দর ভাষা", "আজকের আবহাওয়া খুব সুন্দর", "অনুগ্রহ করে আপনার রসিদ সংরক্ষণ করুন",
            "এটি একটি পরীক্ষামূলক বাক্য", "আমরা সবাই মিলে কাজ করব"],
}
VARIANTS = ["clean", "blur", "noise", "rotate"]
random.seed(7)
out = Path("data/synthetic"); (out / "images").mkdir(parents=True, exist_ok=True); (out / "gt").mkdir(exist_ok=True)
for lang, lines in TEXTS.items():
    for i, line in enumerate(lines):
        for v in VARIANTS:
            font = ImageFont.truetype(ARIAL if lang == "eng" else FONT, 40)
            w = int(font.getlength(line)) + 80
            img = Image.new("L", (w, 120), 255)
            ImageDraw.Draw(img).text((40, 30), line, font=font, fill=0)
            if v == "blur": img = img.filter(ImageFilter.GaussianBlur(1.5))
            if v == "noise":
                px = img.load()
                for _ in range(w * 120 // 12):
                    px[random.randrange(w), random.randrange(120)] = random.choice((0, 255))
            if v == "rotate": img = img.rotate(random.uniform(-4, 4), expand=True, fillcolor=255)
            name = f"{lang}_{i}_{v}"
            img.convert("RGB").save(out / "images" / f"{name}.png")
            (out / "gt" / f"{name}.txt").write_text(line, encoding="utf-8")
print(len(list((out / "images").glob("*.png"))), "images")
