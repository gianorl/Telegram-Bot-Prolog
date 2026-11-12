"""Send a photo of a receipt or payment screenshot: the bot reads it.

Step 1 = read only. Nothing is saved: you check what it reads, and each
misread becomes a test in tests/test_receipt.py. Step 2 will save.
"""

import asyncio
import logging
import subprocess

from telegram import Update
from telegram.ext import ContextTypes, MessageHandler, filters

from app import ocr
from app.formatters import receipt_summary
from app.handlers.shared import now
from app.receipt import parse_receipt

logger = logging.getLogger(__name__)

MAX_RAW_TEXT = 3000  # a Telegram message holds 4096 characters


async def read_receipt(update: Update, context: ContextTypes.DEFAULT_TYPE):
    waiting = await update.message.reply_text("⏳ Membaca struk...")

    # Telegram keeps several sizes of each photo; the last one is the biggest
    photo = await update.message.photo[-1].get_file()
    image = bytes(await photo.download_as_bytearray())

    try:
        # OCR takes a few seconds. In a thread, so the bot keeps answering
        # other messages meanwhile instead of freezing.
        text = await asyncio.to_thread(ocr.read_text, image)
    except (OSError, subprocess.SubprocessError):
        # OSError: not an image, or tesseract not installed
        logger.exception("Could not read receipt photo")
        await waiting.edit_text("Gagal membaca gambar. Catat manual dengan /catat ya.")
        return

    found = parse_receipt(text, now())
    raw = text.strip()[:MAX_RAW_TEXT] or "(kosong)"
    await waiting.edit_text(
        "🧾 Terbaca (belum disimpan, masih tes):\n"
        f"{receipt_summary(found)}\n\n"
        f"Teks mentah:\n{raw}"
    )


def register(app):
    app.add_handler(MessageHandler(filters.UpdateType.MESSAGE & filters.PHOTO, read_receipt))
