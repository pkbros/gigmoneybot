import logging
import uvicorn
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, Response, status
from telegram import Update, BotCommand
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    ContextTypes,
    MessageHandler,
    filters,
    ConversationHandler,
)

from models.config import settings
from handlers.base import start, start_profile, get_college, SET_COLLEGE, cancel
from handlers.register import register_handler
from handlers.search import search_handler, direct_search
from handlers.myskills import myskills_view_handler, deleteskill_handler

# Configure logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Initialize PTB Application
ptb_app = (
    ApplicationBuilder()
    .token(settings.TELEGRAM_BOT_TOKEN)
    .connect_timeout(30)
    .read_timeout(30)
    .write_timeout(30)
    .pool_timeout(30)
    .build()
)

async def error_handler(update: object, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Log the error and send a telegram message to notify the developer."""
    logger.error("Exception while handling an update:", exc_info=context.error)
    if isinstance(update, Update) and update.effective_message:
        await update.effective_message.reply_text(
            "❌ An unexpected error occurred. Please try again later or type /cancel to reset."
        )

# Profile handler
profile_handler = ConversationHandler(
    entry_points=[CommandHandler("profile", start_profile)],
    states={
        SET_COLLEGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_college)],
    },
    fallbacks=[CommandHandler("cancel", cancel)],
    allow_reentry=True,
)

# Register Handlers
ptb_app.add_handler(CommandHandler("start", start))
ptb_app.add_handler(profile_handler)
ptb_app.add_handler(register_handler)
ptb_app.add_handler(search_handler)
ptb_app.add_handler(myskills_view_handler)
ptb_app.add_handler(deleteskill_handler)

# Direct search handler (catch-all for text that isn't a command)
ptb_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, direct_search))

ptb_app.add_error_handler(error_handler)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Handles FastAPI startup and shutdown."""
    # Start PTB application
    await ptb_app.initialize()
    await ptb_app.start()
    
    # Set Bot Commands (for the UI list)
    commands = [
        BotCommand("start", "Welcome and info"),
        BotCommand("register", "List a new skill"),
        BotCommand("search", "Find someone who can help"),
        BotCommand("myskills", "View your active listings"),
        BotCommand("deleteskill", "Delete a listing"),
        BotCommand("profile", "Update your college/profile"),
        BotCommand("cancel", "Cancel current operation"),
    ]
    await ptb_app.bot.set_my_commands(commands)
    
    # Set Telegram Webhook
    if settings.WEBHOOK_URL:
        logger.info(f"Setting webhook to: {settings.WEBHOOK_URL}")
        await ptb_app.bot.set_webhook(url=settings.WEBHOOK_URL)
    else:
        logger.warning("WEBHOOK_URL not set, skipping set_webhook.")
    
    yield
    
    # Stop PTB application
    await ptb_app.stop()
    await ptb_app.shutdown()

app = FastAPI(lifespan=lifespan)

@app.post("/webhook")
async def telegram_webhook(request: Request):
    """Endpoint for Telegram webhook updates."""
    try:
        data = await request.json()
        update = Update.de_json(data, ptb_app.bot)
        # Process in background to avoid Telegram webhook timeout
        asyncio.create_task(ptb_app.process_update(update))
        return Response(status_code=status.HTTP_200_OK)
    except Exception as e:
        logger.error(f"Error processing update: {e}")
        return Response(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR)

@app.get("/health")
async def health_check():
    """Simple health check for Cloud Run."""
    return {"status": "ok"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=settings.PORT)
