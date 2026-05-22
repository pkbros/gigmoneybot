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
from handlers.base import track_user

logger = logging.getLogger(__name__)

# Conversation states
DELETE_SELECTION = range(1)

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

    response = "📜 **Your active listings:**\n\n"
    for i, item in enumerate(listings, 1):
        response += f"{i}. \"{item.skill_text}\" — {item.fee_text}\n"
    
    response += "\nTo delete a listing, use /deleteskill"
    await update.message.reply_text(response, parse_mode="Markdown")

async def start_delete_skill(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /deleteskill flow."""
    await track_user(update)
    telegram_id = update.effective_user.id
    
    listings = await db_service.get_user_listings(telegram_id)
    
    if not listings:
        await update.message.reply_text("You don't have any listings to delete. 🤷‍♂️")
        return ConversationHandler.END

    response = "Select a listing to **DELETE**:\n\n"
    context.user_data["delete_listings_ref"] = listings 
    
    for i, item in enumerate(listings, 1):
        response += f"{i}. \"{item.skill_text}\" — {item.fee_text}\n"
    
    response += "\nReply with the number to delete, or /cancel."
    await update.message.reply_text(response, parse_mode="Markdown")
    
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
        await update.message.reply_text(f"✅ **Deleted:** \"{listing_to_delete.skill_text}\"")
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
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("register", lambda u, c: ConversationHandler.END),
        CommandHandler("search", lambda u, c: ConversationHandler.END),
        CommandHandler("myskills", lambda u, c: ConversationHandler.END),
        CommandHandler("deleteskill", lambda u, c: ConversationHandler.END),
    ],
    allow_reentry=True,
)
