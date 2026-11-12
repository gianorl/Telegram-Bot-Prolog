"""Image bytes -> text, with the Tesseract program installed on the machine.

Server: sudo apt install tesseract-ocr tesseract-ocr-ind
Mac:    brew install tesseract tesseract-lang
"""

import io
import subprocess

from PIL import Image

SCALE = 3  # phone screenshots have ~10px letters; Tesseract likes ~30px
MAX_SIDE = 6000  # after enlarging: keeps memory and time small on a 2 GB server
TIMEOUT_SECONDS = 60


def prepare(image_bytes):
    """Gray and 3x bigger, saved as PNG bytes."""
    img = Image.open(io.BytesIO(image_bytes)).convert("L")
    scale = min(SCALE, MAX_SIDE / max(img.size))  # big photos: enlarge less
    if scale > 1:
        img = img.resize(
            (round(img.width * scale), round(img.height * scale)), Image.LANCZOS
        )
    out = io.BytesIO()
    img.save(out, format="PNG")
    return out.getvalue()


def read_text(image_bytes):
    """Same as typing: tesseract image stdout -l ind+eng --psm 6

    "stdin" = take the image from what we pipe in, no temp file needed.
    A list of arguments, no shell: nothing in the photo can become a command.
    """
    result = subprocess.run(
        ["tesseract", "stdin", "stdout", "-l", "ind+eng", "--psm", "6"],
        input=prepare(image_bytes),
        capture_output=True,
        timeout=TIMEOUT_SECONDS,
        check=True,  # tesseract failed -> CalledProcessError, not empty text
    )
    return result.stdout.decode("utf-8", errors="replace")
