import logging
from typing import Optional
from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
from services.db import db_service
from models.schemas import User

logger = logging.getLogger(__name__)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Operation cancelled. 👍")
    return ConversationHandler.END

async def track_user(update: Update) -> Optional[User]:
    """Ensures the user exists in our database and returns the User object."""
    tg_user = update.effective_user
    if not tg_user:
        return None

    # Check if user already exists to preserve college
    existing_user = await db_service.get_user(tg_user.id)
    
    user = User(
        telegram_id=tg_user.id,
        username=tg_user.username,
        display_name=tg_user.full_name,
        college=existing_user.college if existing_user else None
    )
    await db_service.upsert_user(user)
    return user

async def check_college(update: Update, context: ContextTypes.DEFAULT_TYPE) -> Optional[User]:
    """Verifies if the user has registered their college. Returns User if yes, else None."""
    user = await track_user(update)
    if not user or not user.college:
        await update.message.reply_text(
            "⚠️ Please register your college first!\n"
            "Use /profile to set your college name."
        )
        return None
    return user

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    user = await track_user(update)
    
    welcome_text = (
        f"👋 Welcome to **SkillToken**, {update.effective_user.first_name}!\n\n"
        "The micro-gig marketplace for our campus.\n"
        "Find help or earn by helping others with simple tasks.\n\n"
    )
    
    if not user.college:
        welcome_text += (
            "❗ **Action Required:**\n"
            "You haven't set your college yet. You can only see listings from your own college.\n"
            "👉 Use /profile to set it now."
        )
    else:
        welcome_text += (
            f"🎓 **College:** {user.college}\n\n"
            "🚀 **Commands:**\n"
            "/register - List a skill you can help with\n"
            "/search - Find someone to help you\n"
            "/myskills - View or delete your listings\n"
            "/profile - Change your college or info"
        )
        
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Conversation states for Profile
SET_COLLEGE = range(1)

async def start_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /profile flow."""
    user = await track_user(update)
    current_college = user.college if user.college else "Not set"
    await update.message.reply_text(
        f"👤 **Your Profile**\n\n"
        f"Name: {user.display_name}\n"
        f"College: {current_college}\n\n"
        "What is your college name? (Be specific, e.g., 'RKGIT Ghaziabad')",
        parse_mode="Markdown"
    )
    return SET_COLLEGE

async def get_college(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Updates the user's college."""
    college_name = update.message.text.strip()
    if len(college_name) < 3:
        await update.message.reply_text("Please enter a valid college name (at least 3 characters).")
        return SET_COLLEGE

    tg_user = update.effective_user
    user = User(
        telegram_id=tg_user.id,
        college=college_name
    )
    await db_service.upsert_user(user)
    
    await update.message.reply_text(
        f"✅ **Profile Updated!**\n"
        f"College set to: {college_name}\n\n"
        "Now you can /register or /search for help."
    )
    return -1 # ConversationHandler.END
