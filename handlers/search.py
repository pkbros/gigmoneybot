import logging
import html
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
from handlers.base import track_user, check_college, escape

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
        return ConversationHandler.END
        
    college_escaped = escape(user.college)
    status_msg = await update.message.reply_text(f"🔍 Searching in {college_escaped}...")

    # Log the search for analytics
    await db_service.log_search(
        telegram_id=user.telegram_id,
        username=update.effective_user.username,
        query=query,
        college=user.college
    )

    try:
        query_embedding = await ai_service.get_embedding(query, task_type="RETRIEVAL_QUERY")
        results = await db_service.match_listings(query_embedding, college=user.college, threshold=0.75)

        if not results:
            await status_msg.edit_text(
                f"No one in <b>{college_escaped}</b> has listed that yet. 😕\n\n"
                "📢 <b>Sending an alert...</b> I'll notify students across all campuses. "
                "If someone can help, they'll add the skill. Retry in a bit!",
                parse_mode="HTML"
            )
            # Background Global Alert
            await _broadcast_search_alert(update, query)
        else:
            response = f"🔍 <b>Found {len(results)} students in {college_escaped} who can help:</b>\n\n"
            for i, res in enumerate(results, 1):
                username_val = res.username if res.username else res.display_name
                username = f"@{escape(username_val)}" if res.username else escape(username_val)
                skill_text = escape(res.skill_text)
                description = escape(res.description)
                fee_text = escape(res.fee_text)

                response += f"{i}. {username} — <b>\"{skill_text}\"</b>\n"
                if description:
                    response += f"   📝 <i>{description}</i>\n"
                response += f"   💰 {fee_text}\n\n"
            
            response += "DM them directly to get it done! 👍"
            await status_msg.edit_text(response, parse_mode="HTML")
            
    except Exception as e:
        logger.error(f"Search failed: {e}")
        await status_msg.edit_text("❌ Sorry, something went wrong while searching. Please try again later.")

    return ConversationHandler.END

async def _broadcast_search_alert(update: Update, skill_name: str) -> None:
    """Sends a global notification to all users about a missing skill."""
    users = await db_service.get_all_users()
    searcher_tg = update.effective_user
    
    skill_escaped = escape(skill_name)
    alert_text = (
        f"🚨 <b>New Skill Request!</b>\n\n"
        f"Someone just searched for: <b>\"{skill_escaped}\"</b>\n"
        f"It's not available yet. If you can help with this, use /register to list it now!"
    )
    
    # In a real production app, we would use a task queue (like Celery/Google Tasks)
    # For now, we'll do a simple async loop
    for user in users:
        # Don't alert the searcher themselves
        if user.telegram_id == searcher_tg.id:
            continue
            
        try:
            await update.get_bot().send_message(
                chat_id=user.telegram_id,
                text=alert_text,
                parse_mode="HTML"
            )
        except Exception as e:
            # User might have blocked the bot
            logger.warning(f"Failed to send alert to {user.telegram_id}: {e}")

async def show_all_college_skills(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Displays all skills available in the user's college."""
    user = await check_college(update, context)
    if not user:
        return

    college_escaped = escape(user.college)
    status_msg = await update.message.reply_text(f"📚 Fetching all skills in {college_escaped}...")
    
    try:
        listings = await db_service.get_all_college_listings(user.college)
        
        if not listings:
            await status_msg.edit_text(f"No skills have been registered in <b>{college_escaped}</b> yet. 🏜️", parse_mode="HTML")
            return

        response = f"🏫 <b>Everything available in {college_escaped}:</b>\n\n"
        for i, res in enumerate(listings, 1):
            skill_text = escape(res.skill_text)
            fee_text = escape(res.fee_text)
            response += f"{i}. <b>{skill_text}</b> — {fee_text}\n"
        
        response += "\n🔍 Use /search to find specific help or see details."
        await status_msg.edit_text(response, parse_mode="HTML")
        
    except Exception as e:
        logger.error(f"Failed to fetch all skills: {e}")
        await status_msg.edit_text("❌ Failed to fetch the skill list. Please try again later.")

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
