import logging
from telegram import Update, ReplyKeyboardRemove
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    CommandHandler,
    MessageHandler,
    filters,
)
from services.db import db_service
from handlers.base import track_user, escape

logger = logging.getLogger(__name__)

# Conversation states
DELETE_SELECTION = range(1)

async def _cancel_fallback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Async fallback to end conversation."""
    return ConversationHandler.END

async def view_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Lists the user's active listings (View Only)."""
    await track_user(update)
    telegram_id = update.effective_user.id
    
    listings = await db_service.get_user_listings(telegram_id)
    
    if not listings:
        await update.message.reply_text(
            "You don't have any active listings. 😕\n"
            "Register one with /register"
        )
        return

    response = "📜 <b>Your active listings:</b>\n\n"
    for i, item in enumerate(listings, 1):
        skill_text = escape(item.skill_text)
        fee_text = escape(item.fee_text)
        response += f"{i}. \"{skill_text}\" — {fee_text}\n"
    
    response += "\nTo delete a listing, use /deleteskill"
    await update.message.reply_text(response, parse_mode="HTML")

async def start_delete_skill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /deleteskill flow."""
    await track_user(update)
    telegram_id = update.effective_user.id
    
    listings = await db_service.get_user_listings(telegram_id)
    
    if not listings:
        await update.message.reply_text("You don't have any listings to delete. 🤷‍♂️")
        return ConversationHandler.END

    response = "Select a listing to <b>DELETE</b>:\n\n"
    context.user_data["delete_listings_ref"] = listings 
    
    for i, item in enumerate(listings, 1):
        skill_text = escape(item.skill_text)
        fee_text = escape(item.fee_text)
        response += f"{i}. \"{skill_text}\" — {fee_text}\n"
    
    response += "\nReply with the number to delete, or /cancel."
    await update.message.reply_text(response, parse_mode="HTML")
    
    return DELETE_SELECTION

async def handle_deletion(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Deletes the selected listing."""
    text = update.message.text
    if not text.isdigit():
        await update.message.reply_text("Please enter a valid number, or /cancel.")
        return DELETE_SELECTION

    index = int(text) - 1
    listings = context.user_data.get("delete_listings_ref", [])
    
    if index < 0 or index >= len(listings):
        await update.message.reply_text(f"Invalid number. Choose between 1 and {len(listings)}.")
        return DELETE_SELECTION

    listing_to_delete = listings[index]
    telegram_id = update.effective_user.id

    success = await db_service.delete_listing(str(listing_to_delete.id), telegram_id)
    
    if success:
        skill_escaped = escape(listing_to_delete.skill_text)
        await update.message.reply_text(f"✅ <b>Deleted:</b> \"{skill_escaped}\"", parse_mode="HTML")
    else:
        await update.message.reply_text("❌ Failed to delete listing. Please try again.")

    return ConversationHandler.END

# View handler is just a command
myskills_view_handler = CommandHandler("myskills", view_skills)

# Delete handler is a conversation
deleteskill_handler = ConversationHandler(
    entry_points=[CommandHandler("deleteskill", start_delete_skill)],
    states={
        DELETE_SELECTION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_deletion)],
    },
    fallbacks=[
        CommandHandler("cancel", _cancel_fallback),
        CommandHandler("register", _cancel_fallback),
        CommandHandler("search", _cancel_fallback),
        CommandHandler("myskills", _cancel_fallback),
        CommandHandler("deleteskill", _cancel_fallback),
    ],
    allow_reentry=True,
)
