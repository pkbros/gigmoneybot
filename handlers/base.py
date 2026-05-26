import logging
import html
from typing import Optional
from telegram import Update, ReplyKeyboardMarkup, ReplyKeyboardRemove
from telegram.ext import ContextTypes, ConversationHandler

from services.db import db_service
from models.schemas import User

def escape(text: Optional[str]) -> str:
    """Safely escapes text for Telegram HTML parse mode."""
    if not text:
        return ""
    return html.escape(text)

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
    await update.message.reply_text("Operation cancelled. 👍", reply_markup=ReplyKeyboardRemove(), parse_mode="HTML")
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
            "⚠️ <b>Action Required!</b>\n\n"
            "You need to register your college before you can list or search for skills.\n"
            "👉 Use /profile to set your college now.",
            parse_mode="HTML"
        )
        return None
    return user

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles the /start command."""
    user = await track_user(update)
    tg_user = update.effective_user
    
    first_name = escape(tg_user.first_name)
    welcome_text = (
        f"👋 Welcome to <b>SkillToken</b>, {first_name}!\n\n"
        "The micro-gig marketplace for our campus.\n"
        "Find help or earn by helping others with simple tasks.\n\n"
    )
    
    if not tg_user.username:
        welcome_text += (
            "⚠️ <b>Username Required!</b>\n"
            "You don't have a Telegram @username set. Others won't be able to DM you for help.\n\n"
            "1. Go to Telegram Settings\n"
            "2. Edit Profile > Username\n"
            "3. Set a username and come back here!"
        )
    elif not user.college:
        welcome_text += (
            "❗ <b>Action Required:</b>\n"
            "You haven't set your college yet. You can only see listings from your own college.\n"
            "👉 Use /profile to set it now."
        )
    else:
        college = escape(user.college)
        welcome_text += (
            f"🎓 <b>College:</b> {college}\n\n"
            "🚀 <b>Commands:</b>\n"
            "/register - List a skill you can help with\n"
            "/search - Find someone to help you\n"
            "/allskills - See all skills in your college\n"
            "/myskills - View your active listings\n"
            "/deleteskill - Delete a listing\n"
            "/profile - Change your college or info"
        )
        
    await update.message.reply_text(welcome_text, parse_mode="HTML")

# Conversation states for Profile
SET_COLLEGE = range(1)

async def start_profile(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /profile flow."""
    tg_user = update.effective_user
    
    if not tg_user.username:
        await update.message.reply_text(
            "❌ <b>Username Missing</b>\n\n"
            "You must set a Telegram <b>@username</b> before you can register on SkillToken.\n"
            "Otherwise, other students won't be able to contact you.\n\n"
            "Please set your username in Telegram Settings and then type /profile again.",
            parse_mode="HTML"
        )
        return ConversationHandler.END

    user = await track_user(update)
    display_name = escape(user.display_name)
    username = escape(tg_user.username)
    current_college = escape(user.college) if user.college else "Not set"
    
    await update.message.reply_text(
        f"👤 <b>Your Profile</b>\n\n"
        f"Name: {display_name}\n"
        f"Username: @{username}\n"
        f"College: {current_college}\n\n"
        "Please select your college from the list below:\n"
        "(Type /cancel to abort)",
        reply_markup=get_college_keyboard(),
        parse_mode="HTML"
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
    
    college_escaped = escape(college_name)
    await update.message.reply_text(
        f"✅ <b>Profile Updated!</b>\n"
        f"College set to: {college_escaped}\n\n"
        "Now you can /register or /search for help.",
        reply_markup=ReplyKeyboardRemove(),
        parse_mode="HTML"
    )
    return ConversationHandler.END
