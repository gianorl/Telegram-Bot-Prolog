import logging

from telegram import Update
from telegram.ext import (
    ApplicationBuilder,
    CallbackQueryHandler,
    CommandHandler,
    MessageHandler,
    TypeHandler,
    filters,
)

from app import db
from app.auth import owner_guard
from app.config import DATABASE_URL, TELEGRAM_TOKEN, TZ_NAME
from app.handlers import common, flows, history, reports, subscriptions

logging.basicConfig(
    format="%(asctime)s %(levelname)s %(name)s: %(message)s", level=logging.INFO
)
# At INFO, httpx logs every request URL, and Telegram URLs contain the token
logging.getLogger("httpx").setLevel(logging.WARNING)
logging.getLogger("apscheduler").setLevel(logging.WARNING)  # logs every timeout timer
logger = logging.getLogger("prolog")


async def close_db(app):
    db.close_db()  # hand the connections back to Postgres cleanly on Ctrl + C


def build_app():
    app = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(common.set_commands)
        .post_shutdown(close_db)
        .build()
    )

    # Group -1 runs before everything else: non-owners stop here
    app.add_handler(TypeHandler(Update, owner_guard), group=-1)

    app.add_handler(CommandHandler(["start", "help"], common.help_command))
    app.add_handler(flows.conversation)  # every multi-step flow
    reports.register(app)
    history.register(app)
    subscriptions.register(app)  # also schedules the reminder check

    # Registered last: only runs when nothing above handled the update
    app.add_handler(
        MessageHandler(
            filters.UpdateType.MESSAGE & (filters.TEXT | filters.COMMAND),
            common.unknown,
        )
    )
    app.add_handler(CallbackQueryHandler(common.stale_button))

    app.add_error_handler(common.on_error)
    return app


def main():
    db.init_db(DATABASE_URL, TZ_NAME)
    app = build_app()
    logger.info("Bot is running...")
    app.run_polling()


if __name__ == "__main__":
    main()
