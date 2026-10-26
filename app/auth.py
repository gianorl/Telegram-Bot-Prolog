import logging

from telegram import Update
from telegram.ext import ApplicationHandlerStop, ContextTypes

from app.config import OWNER_ID

logger = logging.getLogger(__name__)


async def owner_guard(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Runs before every handler (group -1). Non-owners get silence."""
    user = update.effective_user
    if user is None or user.id != OWNER_ID:
        logger.info(
            "Ignored update from non-owner user id %s", user.id if user else None
        )
        raise ApplicationHandlerStop  # stops all other handlers for this update
