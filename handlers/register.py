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
from handlers.base import track_user, check_college, escape

logger = logging.getLogger(__name__)

# Conversation states
SKILL_TEXT, DESCRIPTION, FEE = range(3)

async def _cancel_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Async fallback to end conversation."""
    return ConversationHandler.END

async def start_register(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /register flow."""
    tg_user = update.effective_user
    if not tg_user.username:
        await update.message.reply_text(
            "❌ <b>Username Missing</b>\n\n"
            "You need a Telegram @username so others can contact you.\n"
            "Set it in Settings and try again.",
            parse_mode="HTML"
        )
        return ConversationHandler.END

    user = await check_college(update, context)
    if not user:
        return ConversationHandler.END

    await update.message.reply_text(
        "✨ <b>Register a new skill!</b>\n\n"
        "1️⃣ <b>First, give it a short name.</b>\n"
        "e.g. 'Java Tutoring', 'Maggi Service'\n"
        "(Type /cancel to abort)",
        parse_mode="HTML"
    )
    return SKILL_TEXT

async def get_skill_text(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the skill name and asks for a description."""
    context.user_data["skill_text"] = update.message.text
    await update.message.reply_text(
        "2️⃣ <b>Now, elaborate a bit.</b>\n"
        "Describe exactly what you offer so people can find you easily.\n"
        "(Type /cancel to abort)",
        parse_mode="HTML"
    )
    return DESCRIPTION

async def get_description(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Stores the description and asks for the fee."""
    context.user_data["description"] = update.message.text
    await update.message.reply_text(
        "3️⃣ <b>How much do you charge?</b> (₹/Treat/Free)\n"
        "(Type /cancel to abort)",
        parse_mode="HTML"
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

        skill_esc = escape(skill_text)
        desc_esc = escape(description)
        fee_esc = escape(fee_display)
        coll_esc = escape(college)

        await status_msg.edit_text(
            f"✅ <b>Skill Listed Successfully!</b>\n\n"
            f"🛠 <b>{skill_esc}</b>\n"
            f"📝 {desc_esc}\n"
            f"💰 {fee_esc}\n"
            f"🏫 {coll_esc}\n\n"
            "Students can now find you in /search!",
            parse_mode="HTML"
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
        CommandHandler("cancel", _cancel_fallback),
        CommandHandler("search", _cancel_fallback),
        CommandHandler("myskills", _cancel_fallback),
        CommandHandler("register", _cancel_fallback),
    ],
    allow_reentry=True,
)
