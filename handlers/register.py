import logging
from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from services.db import db_service
from services.ai import ai_service
from models.schemas import Listing
from handlers.base import track_user, check_college

logger = logging.getLogger(__name__)

# Conversation states
SKILL_TEXT, FEE = range(2)

async def start_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /register flow."""
    user = await check_college(update, context)
    if not user:
        return ConversationHandler.END

    await update.message.reply_text(
        "What's the skill? Describe it like you're texting a friend.\n"
        "e.g. 'set up VS Code with JDK', 'cook maggi at 2am', 'explain DBMS normalization'"
    )
    return SKILL_TEXT

async def get_skill_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the skill text and asks for the fee."""
    context.user_data["skill_text"] = update.message.text
    await update.message.reply_text("How much do you charge for this? (₹)")
    return FEE

async def get_fee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the fee exactly as typed, generates embedding, and saves the listing."""
    fee_display = update.message.text.strip()
    skill_text = context.user_data["skill_text"]
    
    # Get user to get their college
    user = await track_user(update)
    telegram_id = user.telegram_id
    college = user.college

    status_msg = await update.message.reply_text("⏳ Processing your listing...")

    try:
        # Generate embedding
        embedding = await ai_service.get_embedding(skill_text, task_type="RETRIEVAL_DOCUMENT")
        
        # Save to DB
        listing = Listing(
            telegram_id=telegram_id,
            skill_text=skill_text,
            fee_text=fee_display,
            college=college,
            embedding=embedding
        )
        await db_service.create_listing(listing)

        await status_msg.edit_text(
            f"✅ **Listed!**\n\n"
            f"\"{skill_text}\" — {fee_display}\n"
            f"College: {college}\n\n"
            "Add more skills anytime with /register",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        await status_msg.edit_text("❌ Sorry, something went wrong while saving your listing. Please try again later.")

    return ConversationHandler.END

register_handler = ConversationHandler(
    entry_points=[CommandHandler("register", start_register)],
    states={
        SKILL_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_skill_text)],
        FEE: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_fee)],
    },
    fallbacks=[
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("search", lambda u, c: ConversationHandler.END),
        CommandHandler("myskills", lambda u, c: ConversationHandler.END),
        CommandHandler("register", lambda u, c: ConversationHandler.END),
    ],
    allow_reentry=True,
)
