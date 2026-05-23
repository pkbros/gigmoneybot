import logging
from typing import Optional
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from services.db import db_service
from models.schemas import User

# Predefined list of colleges
COLLEGES = [
    "AKGEC", "KIET", "ABES EC", "ABESIT", "RKGIT", "IPEC", "IMSEC", "Nitra", 
    "Ideal IT", "KEC", "HRIT", "MIT Ghaziabad", "BBDIT", "RKGITM", "VITS", 
    "ACE", "HIET", "Lord Krishna", "Neelkanth", "SRM Ghaziabad", "Amity Noida", 
    "JIIT", "Galgotias EC", "Galgotias University", "NIET", "JSSATE", 
    "Sharda University", "GL Bajaj", "Bennett University", "DTC Greater Noida", 
    "Mangalmay", "Accurate", "Dronacharya", "IIMT", "KCC", "RICS Amity", 
    "Shiv Nadar", "GNIOT", "Skyline", "Lloyd"
]

# Helper to create keyboard
def get_college_keyboard():
    # Split colleges into rows of 2 for better UI
    keyboard = [COLLEGES[i:i + 2] for i in range(0, len(COLLEGES), 2)]
    return ReplyKeyboardMarkup(keyboard, one_time_keyboard=True, resize_keyboard=True)

logger = logging.getLogger(__name__)

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Cancels and ends the conversation."""
    await update.message.reply_text("Operation cancelled. 👍", reply_markup=ReplyKeyboardRemove())
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
            "⚠️ **Action Required!**\n\n"
            "You need to register your college before you can list or search for skills.\n"
            "👉 Use /profile to set your college now.",
            parse_mode="Markdown"
        )
        return None
    return user

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    user = await track_user(update)
    tg_user = update.effective_user
    
    welcome_text = (
        f"👋 Welcome to **SkillToken**, {tg_user.first_name}!\n\n"
        "The micro-gig marketplace for our campus.\n"
        "Find help or earn by helping others with simple tasks.\n\n"
    )
    
    if not tg_user.username:
        welcome_text += (
            "⚠️ **Username Required!**\n"
            "You don't have a Telegram @username set. Others won't be able to DM you for help.\n\n"
            "1. Go to Telegram Settings\n"
            "2. Edit Profile > Username\n"
            "3. Set a username and come back here!"
        )
    elif not user.college:
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
            "/myskills - View your active listings\n"
            "/deleteskill - Delete a listing\n"
            "/profile - Change your college or info"
        )
        
    await update.message.reply_text(welcome_text, parse_mode="Markdown")

# Conversation states for Profile
SET_COLLEGE = range(1)

async def start_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /profile flow."""
    tg_user = update.effective_user
    
    if not tg_user.username:
        await update.message.reply_text(
            "❌ **Username Missing**\n\n"
            "You must set a Telegram **@username** before you can register on SkillToken.\n"
            "Otherwise, other students won't be able to contact you.\n\n"
            "Please set your username in Telegram Settings and then type /profile again.",
            parse_mode="Markdown"
        )
        return ConversationHandler.END

    user = await track_user(update)
    current_college = user.college if user.college else "Not set"
    await update.message.reply_text(
        f"👤 **Your Profile**\n\n"
        f"Name: {user.display_name}\n"
        f"Username: @{tg_user.username}\n"
        f"College: {current_college}\n\n"
        "Please select your college from the list below:\n"
        "_(Type /cancel to abort)_",
        reply_markup=get_college_keyboard(),
        parse_mode="Markdown"
    )
    return SET_COLLEGE

async def get_college(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Updates the user's college."""
    college_name = update.message.text.strip()
    
    if college_name not in COLLEGES:
        await update.message.reply_text(
            "❌ Please select a college from the list provided.\n"
            "If yours isn't there, pick the closest one or type /cancel.",
            reply_markup=get_college_keyboard()
        )
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
        "Now you can /register or /search for help.",
        reply_markup=ReplyKeyboardRemove()
    )
    return ConversationHandler.END
