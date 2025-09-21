from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import sys
import os
from datetime import datetime

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def withdrawals_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show withdrawal history and status"""
    user_id = str(update.effective_user.id)
    
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ User not found. Please use /start first.")
        return
    
    pending_withdrawals = user.get("pending_withdrawals", [])
    total_withdrawn = user.get("total_withdrawn", 0)
    
    if not pending_withdrawals:
        await update.message.reply_text(
            f"💸 **WITHDRAWAL HISTORY**\n\n"
            f"📊 **Total Withdrawn:** {int(total_withdrawn)} {CURRENCY}\n"
            f"📋 **Recent Requests:** None\n\n"
            f"💡 Use `/withdraw` to request a new withdrawal!"
        )
        return
    
    history_text = f"💸 **WITHDRAWAL HISTORY**\n\n"
    history_text += f"📊 **Total Withdrawn:** {int(total_withdrawn)} {CURRENCY}\n\n"
    history_text += f"📋 **Recent Requests:**\n\n"
    
    for i, withdrawal in enumerate(pending_withdrawals[-5:], 1):  # Last 5 withdrawals
        amount = withdrawal.get("amount", 0)
        method = withdrawal.get("payment_method", "Unknown")
        status = withdrawal.get("status", "UNKNOWN")
        request_time = withdrawal.get("request_time", "")
        
        # Format date
        try:
            if isinstance(request_time, str):
                date_obj = datetime.fromisoformat(request_time.replace('Z', '+00:00'))
                date_str = date_obj.strftime('%m/%d %H:%M')
            else:
                date_str = "Unknown"
        except:
            date_str = "Unknown"
        
        status_emoji = "✅" if status == "APPROVED" else "❌" if status == "REJECTED" else "⏳"
        
        history_text += f"{i}. **{amount} {CURRENCY}** via {method}\n"
        history_text += f"   📅 {date_str} | {status_emoji} {status}\n\n"
    
    # Add current balance
    current_balance = user.get("balance", 0)
    history_text += f"💰 **Current Balance:** {int(current_balance)} {CURRENCY}\n"
    history_text += f"💡 Use `/withdraw` to request new withdrawal"
    
    await update.message.reply_text(history_text)

def register_handlers(application: Application):
    """Register withdrawals command handler"""
    logger.info("Registering withdrawals command handler")
    application.add_handler(CommandHandler("withdrawals", withdrawals_command))
    logger.info("✅ Withdrawals command registered successfully")
