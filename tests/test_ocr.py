"""Real OCR on a tiny drawn image. Skipped where Tesseract isn't installed."""

import io
import shutil

import pytest
from PIL import Image, ImageDraw, ImageFont

from app.ocr import prepare, read_text

needs_tesseract = pytest.mark.skipif(
    shutil.which("tesseract") is None, reason="tesseract not installed"
)


def png(width, height, text=""):
    img = Image.new("L", (width, height), 255)
    if text:
        font = ImageFont.load_default(size=28)
        ImageDraw.Draw(img).text((20, 20), text, fill=0, font=font)
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def test_prepare_enlarges_3x():
    assert Image.open(io.BytesIO(prepare(png(200, 100)))).size == (600, 300)


def test_prepare_enlarges_big_photo_less():
    # 2560 * 3 = 7680 would be too big: capped at 6000
    assert max(Image.open(io.BytesIO(prepare(png(2560, 100)))).size) == 6000


@needs_tesseract
def test_read_text():
    assert "TOTAL 64.380" in read_text(png(400, 80, "TOTAL 64.380"))


def test_not_an_image():
    with pytest.raises(OSError):
        read_text(b"this is not a picture")
