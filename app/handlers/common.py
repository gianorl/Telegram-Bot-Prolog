import logging

from telegram import BotCommand, Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)

# One list feeds both /help and the "/" menu in Telegram
COMMANDS = [
    ("catat", "Catat pengeluaran"),
    ("masuk", "Catat pemasukan (gaji, dll)"),
    ("pindah", "Pindah dana antar akun (top up, tarik tunai)"),
    ("saldo", "Saldo semua akun"),
    ("bulan", "Ringkasan siklus gajian ini"),
    ("riwayat", "Lihat, ubah, atau hapus catatan"),
    ("ekspor", "Unduh saldo + semua transaksi (CSV untuk Excel/Sheets)"),
    ("budget", "Lihat atau atur budget per kategori"),
    ("hutang", "Hutang & piutang"),
    ("langganan", "Langganan & tagihan rutin"),
    ("sesuaikan", "Samakan saldo dengan aplikasi bank"),
    ("akun", "Tambah akun (bank, e-wallet, cash)"),
    ("hapus", "Hapus catatan terakhir"),
    ("batal", "Batalkan yang sedang berjalan"),
    ("help", "Daftar perintah"),
]


async def set_commands(app):
    """Runs once at startup. Same as BotFather's /setcommands."""
    await app.bot.set_my_commands([BotCommand(name, desc) for name, desc in COMMANDS])


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    lines = ["Prolog: catatan keuangan kamu.", ""]
    lines += [f"/{name} - {desc}" for name, desc in COMMANDS]
    await update.message.reply_text("\n".join(lines))


async def unknown(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Aku belum ngerti. Ketik /help untuk daftar perintah."
    )


async def stale_button(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """A tap on an old button that no flow is waiting for."""
    await update.callback_query.answer("Tombol ini sudah tidak berlaku.")


async def on_error(update: object, context: ContextTypes.DEFAULT_TYPE):
    logger.error("Unhandled error", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text("Maaf, ada error. Coba lagi ya.")
