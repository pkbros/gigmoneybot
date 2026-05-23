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
SKILL_TEXT, DESCRIPTION, FEE = range(3)

async def start_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /register flow."""
    tg_user = update.effective_user
    if not tg_user.username:
        await update.message.reply_text(
            "❌ **Username Missing**\n\n"
            "You need a Telegram @username so others can contact you.\n"
            "Set it in Settings and try again.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    user = await check_college(update, context)
    if not user:
        return ConversationHandler.END

    await update.message.reply_text(
        "✨ **Register a new skill!**\n\n"
        "1️⃣ **First, give it a short name.**\n"
        "e.g. 'Java Tutoring', 'Maggi Service'\n"
        "_(Type /cancel to abort)_",
        parse_mode="Markdown"
    )
    return SKILL_TEXT

async def get_skill_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the skill name and asks for a description."""
    context.user_data["skill_text"] = update.message.text
    await update.message.reply_text(
        "2️⃣ **Now, elaborate a bit.**\n"
        "Describe exactly what you offer so people can find you easily.\n"
        "_(Type /cancel to abort)_",
        parse_mode="Markdown"
    )
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the description and asks for the fee."""
    context.user_data["description"] = update.message.text
    await update.message.reply_text(
        "3️⃣ **How much do you charge?** (₹/Treat/Free)\n"
        "_(Type /cancel to abort)_"
    )
    return FEE

async def get_fee(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the fee, generates combined embedding, and saves the listing."""
    fee_display = update.message.text.strip()
    skill_text = context.user_data["skill_text"]
    description = context.user_data["description"]
    
    user = await track_user(update)
    telegram_id = user.telegram_id
    college = user.college

    status_msg = await update.message.reply_text("⏳ Processing your listing...")

    try:
        # Combine text for richer embedding context
        embedding_text = f"{skill_text}: {description}"
        embedding = await ai_service.get_embedding(embedding_text, task_type="RETRIEVAL_DOCUMENT")
        
        # Save to DB
        listing = Listing(
            telegram_id=telegram_id,
            skill_text=skill_text,
            description=description,
            fee_text=fee_display,
            college=college,
            embedding=embedding
        )
        await db_service.create_listing(listing)

        await status_msg.edit_text(
            f"✅ **Skill Listed Successfully!**\n\n"
            f"🛠 **{skill_text}**\n"
            f"📝 {description}\n"
            f"💰 {fee_display}\n"
            f"🏫 {college}\n\n"
            "Students can now find you in /search!",
            parse_mode="Markdown"
        )
    except Exception as e:
        logger.error(f"Registration failed: {e}")
        await status_msg.edit_text("❌ Failed to save listing. Please try again later.")

    return ConversationHandler.END

register_handler = ConversationHandler(
    entry_points=[CommandHandler("register", start_register)],
    states={
        SKILL_TEXT: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_skill_text)],
        DESCRIPTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, get_description)],
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
