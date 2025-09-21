from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
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

async def pending_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check pending withdrawal requests"""
    user_id = str(update.effective_user.id)
    
    user = await db.get_user(user_id)
    if not user:
        await update.message.reply_text("❌ User not found. Please use /start first.")
        return
    
    pending_withdrawals = user.get("pending_withdrawals", [])
    
    if not pending_withdrawals:
        await update.message.reply_text(
            f"📋 **No Withdrawal History**\n\n"
            f"You haven't made any withdrawal requests yet.\n\n"
            f"💡 Use `/withdraw` to request a withdrawal!"
        )
        return
    
    # Filter pending requests
    pending_requests = [w for w in pending_withdrawals if w.get("status") == "PENDING"]
    approved_requests = [w for w in pending_withdrawals if w.get("status") == "APPROVED"]
    rejected_requests = [w for w in pending_withdrawals if w.get("status") == "REJECTED"]
    
    pending_text = f"📋 **WITHDRAWAL STATUS**\n\n"
    
    # Show pending requests
    if pending_requests:
        pending_text += f"⏳ **PENDING REQUESTS ({len(pending_requests)}):**\n\n"
        for i, withdrawal in enumerate(pending_requests, 1):
            amount = withdrawal.get("amount", 0)
            method = withdrawal.get("payment_method", "Unknown")
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
            
            pending_text += f"{i}. **{amount:,} {CURRENCY}** via {method}\n"
            pending_text += f"   📅 Requested: {date_str}\n"
            pending_text += f"   ⏳ Status: Waiting for admin approval\n\n"
    
    # Show recent completed requests
    recent_completed = approved_requests[-3:] + rejected_requests[-3:]
    recent_completed.sort(key=lambda x: x.get("request_time", ""), reverse=True)
    
    if recent_completed:
        pending_text += f"📜 **RECENT HISTORY ({len(recent_completed)}):**\n\n"
        for i, withdrawal in enumerate(recent_completed[:5], 1):
            amount = withdrawal.get("amount", 0)
            method = withdrawal.get("payment_method", "Unknown")
            status = withdrawal.get("status", "UNKNOWN")
            request_time = withdrawal.get("request_time", "")
            
            try:
                if isinstance(request_time, str):
                    date_obj = datetime.fromisoformat(request_time.replace('Z', '+00:00'))
                    date_str = date_obj.strftime('%m/%d %H:%M')
                else:
                    date_str = "Unknown"
            except:
                date_str = "Unknown"
            
            status_emoji = "✅" if status == "APPROVED" else "❌" if status == "REJECTED" else "⏳"
            
            pending_text += f"{i}. **{amount:,} {CURRENCY}** via {method}\n"
            pending_text += f"   📅 {date_str} | {status_emoji} {status}\n\n"
    
    # Add current balance and summary
    current_balance = user.get("balance", 0)
    total_withdrawn = user.get("total_withdrawn", 0)
    
    pending_text += f"💰 **CURRENT STATUS:**\n"
    pending_text += f"• Balance: {int(current_balance)} {CURRENCY}\n"
    pending_text += f"• Total Withdrawn: {int(total_withdrawn)} {CURRENCY}\n"
    pending_text += f"• Pending Requests: {len(pending_requests)}\n\n"
    
    if pending_requests:
        pending_text += f"⏰ **Please wait for admin approval**\n"
        pending_text += f"📞 **Support:** @When_the_night_falls_my_soul_se"
    else:
        pending_text += f"✅ **No pending requests - you can withdraw again!**"
    
    await update.message.reply_text(pending_text)

def register_handlers(application: Application):
    """Register pending withdrawal handlers"""
    logger.info("Registering pending withdrawal command")
    application.add_handler(CommandHandler("pending", pending_command))
    application.add_handler(CommandHandler("check", pending_command))  # Alternative command
    logger.info("✅ Pending withdrawal command registered successfully")
