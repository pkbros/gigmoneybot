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
from handlers.base import track_user, check_college

logger = logging.getLogger(__name__)

# Conversation states
SEARCH_QUERY = range(1)

async def start_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Starts the /search flow."""
    user = await check_college(update, context)
    if not user:
        return ConversationHandler.END
        
    await update.message.reply_text("🔍 What do you need help with?")
    return SEARCH_QUERY

async def perform_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Performs semantic search and displays results."""
    query = update.message.text
    return await _execute_search(update, query)

async def direct_search(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handles direct text as a search query if not in a conversation."""
    query = update.message.text
    if query.startswith('/'):
        return
    await _execute_search(update, query)

async def _execute_search(update: Update, query: str) -> int:
    user = await track_user(update)
    if not user or not user.college:
        # Don't annoy users with direct search if they haven't set college
        return ConversationHandler.END
        
    status_msg = await update.message.reply_text(f"🔍 Searching in {user.college}...")

    try:
        # Generate embedding for query
        query_embedding = await ai_service.get_embedding(query, task_type="RETRIEVAL_QUERY")
        
        # Match in DB with college filter and higher threshold (0.5) to avoid irrelevant matches
        results = await db_service.match_listings(query_embedding, college=user.college, threshold=0.5)

        if not results:
            await status_msg.edit_text(
                f"No one in **{user.college}** has listed exactly that yet. 😕\n\n"
                "💡 **Pro-Tip:** Try describing what you need in more detail.\n"
                "Instead of just 'Math', try 'Help with Calculus integration'.",
                parse_mode="Markdown"
            )
        else:
            response = f"🔍 **Found {len(results)} students in {user.college} who can help:**\n\n"
            for i, res in enumerate(results, 1):
                username = f"@{res.username}" if res.username else res.display_name
                response += f"{i}. {username} — **\"{res.skill_text}\"**\n"
                if res.description:
                    response += f"   📝 _{res.description}_\n"
                response += f"   💰 {res.fee_text}\n\n"
            
            response += "DM them directly to get it done! 👍"
            await status_msg.edit_text(response, parse_mode="Markdown")
            
    except Exception as e:
        logger.error(f"Search failed: {e}")
        await status_msg.edit_text("❌ Sorry, something went wrong while searching. Please try again later.")

    return ConversationHandler.END

search_handler = ConversationHandler(
    entry_points=[CommandHandler("search", start_search)],
    states={
        SEARCH_QUERY: [MessageHandler(filters.TEXT & ~filters.COMMAND, perform_search)],
    },
    fallbacks=[
        CommandHandler("cancel", lambda u, c: ConversationHandler.END),
        CommandHandler("register", lambda u, c: ConversationHandler.END),
        CommandHandler("myskills", lambda u, c: ConversationHandler.END),
        CommandHandler("search", lambda u, c: ConversationHandler.END),
    ],
    allow_reentry=True,
)
