from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import sys
import os
from datetime import datetime, timezone

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def approve_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to approve withdrawal by user ID and amount"""
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    # Check arguments
    if len(context.args) < 2:
        await update.message.reply_text(
            f"❌ **Invalid usage**\n\n"
            f"**Correct format:**\n"
            f"`/approve <user_id> <amount>`\n\n"
            f"**Example:**\n"
            f"`/approve 123456789 1000`"
        )
        return
    
    try:
        target_user_id = str(context.args[0])
        amount = int(context.args[1])
    except ValueError:
        await update.message.reply_text(
            f"❌ **Invalid format**\n\n"
            f"Amount must be a number.\n"
            f"Example: `/approve 123456789 1000`"
        )
        return
    
    # Get target user
    user = await db.get_user(target_user_id)
    if not user:
        await update.message.reply_text(f"❌ User {target_user_id} not found.")
        return
    
    # Find pending withdrawal
    pending_withdrawals = user.get("pending_withdrawals", [])
    withdrawal = None
    withdrawal_index = None
    
    for i, w in enumerate(pending_withdrawals):
        if w.get("amount") == amount and w.get("status") == "PENDING":
            withdrawal = w
            withdrawal_index = i
            break
    
    if not withdrawal:
        await update.message.reply_text(
            f"❌ **No pending withdrawal found**\n\n"
            f"User: {target_user_id}\n"
            f"Amount: {amount:,} {CURRENCY}\n\n"
            f"Check `/list` for all pending withdrawals."
        )
        return
    
    # Approve withdrawal
    total_withdrawn = user.get("total_withdrawn", 0) + amount
    
    # Update withdrawal status
    pending_withdrawals[withdrawal_index]["status"] = "APPROVED"
    pending_withdrawals[withdrawal_index]["approved_by"] = user_id
    pending_withdrawals[withdrawal_index]["approved_at"] = datetime.now(timezone.utc).isoformat()
    
    await db.update_user(target_user_id, {
        "total_withdrawn": total_withdrawn,
        "last_withdrawal": datetime.now(timezone.utc),
        "pending_withdrawals": pending_withdrawals
    })
    
    # Get user's name
    try:
        telegram_user = await context.bot.get_chat(target_user_id)
        user_name = telegram_user.first_name or "User"
    except:
        user_name = user.get("first_name", "User")
    
    # Notify admin
    await update.message.reply_text(
        f"✅ **WITHDRAWAL APPROVED**\n\n"
        f"👤 **User:** {user_name} ({target_user_id})\n"
        f"💰 **Amount:** {amount:,} {CURRENCY}\n"
        f"💳 **Method:** {withdrawal['payment_method']}\n"
        f"📅 **Approved:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"👨‍💼 **By:** Admin {user_id}\n\n"
        f"💵 **Balance was already deducted when user submitted**\n"
        f"🔔 **User has been notified**"
    )
    
    # Notify user
    try:
        current_balance = user.get("balance", 0)
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                f"✅ **WITHDRAWAL APPROVED!**\n\n"
                f"💰 **Amount:** {amount:,} {CURRENCY}\n"
                f"💳 **Method:** {withdrawal['payment_method']}\n"
                f"💵 **Current Balance:** {int(current_balance)} {CURRENCY}\n\n"
                f"🎉 Your withdrawal has been processed successfully!\n"
                f"💸 **Payment is being sent to your account!**\n\n"
                f"📞 **Support:** @When_the_night_falls_my_soul_se\n\n"
                f"သင့်ငွေထုတ်မှုကို အတည်ပြုပါသည်။\n"
                f"ငွေကို သင့်အကောင့်သို့ ပို့နေပါသည်။"
            )
        )
    except Exception as e:
        logger.error(f"Failed to notify user {target_user_id}: {e}")
        await update.message.reply_text(f"⚠️ **Approved but failed to notify user**")
    
    logger.info(f"Admin {user_id} approved withdrawal: {target_user_id} - {amount} {CURRENCY}")

async def reject_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to reject withdrawal by user ID and amount"""
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    # Check arguments
    if len(context.args) < 2:
        await update.message.reply_text(
            f"❌ **Invalid usage**\n\n"
            f"**Correct format:**\n"
            f"`/reject <user_id> <amount>`\n\n"
            f"**Example:**\n"
            f"`/reject 123456789 1000`\n\n"
            f"**Optional reason:**\n"
            f"`/reject 123456789 1000 Invalid details`"
        )
        return
    
    try:
        target_user_id = str(context.args[0])
        amount = int(context.args[1])
        reason = " ".join(context.args[2:]) if len(context.args) > 2 else "No reason provided"
    except ValueError:
        await update.message.reply_text(
            f"❌ **Invalid format**\n\n"
            f"Amount must be a number.\n"
            f"Example: `/reject 123456789 1000`"
        )
        return
    
    # Get target user
    user = await db.get_user(target_user_id)
    if not user:
        await update.message.reply_text(f"❌ User {target_user_id} not found.")
        return
    
    # Find pending withdrawal
    pending_withdrawals = user.get("pending_withdrawals", [])
    withdrawal = None
    withdrawal_index = None
    
    for i, w in enumerate(pending_withdrawals):
        if w.get("amount") == amount and w.get("status") == "PENDING":
            withdrawal = w
            withdrawal_index = i
            break
    
    if not withdrawal:
        await update.message.reply_text(
            f"❌ **No pending withdrawal found**\n\n"
            f"User: {target_user_id}\n"
            f"Amount: {amount:,} {CURRENCY}\n\n"
            f"Check `/list` for all pending withdrawals."
        )
        return
    
    # Reject withdrawal - REFUND the balance
    current_balance = user.get("balance", 0)
    refunded_balance = current_balance + amount
    withdrawn_today = user.get("withdrawn_today", 0) - amount
    
    # Update withdrawal status
    pending_withdrawals[withdrawal_index]["status"] = "REJECTED"
    pending_withdrawals[withdrawal_index]["rejected_by"] = user_id
    pending_withdrawals[withdrawal_index]["rejected_at"] = datetime.now(timezone.utc).isoformat()
    pending_withdrawals[withdrawal_index]["rejection_reason"] = reason
    
    await db.update_user(target_user_id, {
        "balance": refunded_balance,
        "withdrawn_today": max(0, withdrawn_today),
        "pending_withdrawals": pending_withdrawals
    })
    
    # Get user's name
    try:
        telegram_user = await context.bot.get_chat(target_user_id)
        user_name = telegram_user.first_name or "User"
    except:
        user_name = user.get("first_name", "User")
    
    # Notify admin
    await update.message.reply_text(
        f"❌ **WITHDRAWAL REJECTED**\n\n"
        f"👤 **User:** {user_name} ({target_user_id})\n"
        f"💰 **Amount:** {amount:,} {CURRENCY}\n"
        f"💳 **Method:** {withdrawal['payment_method']}\n"
        f"📝 **Reason:** {reason}\n"
        f"📅 **Rejected:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
        f"👨‍💼 **By:** Admin {user_id}\n\n"
        f"🔄 **Balance refunded:** {amount:,} {CURRENCY}\n"
        f"💵 **New balance:** {int(refunded_balance)} {CURRENCY}\n"
        f"🔔 **User has been notified**"
    )
    
    # Notify user
    try:
        await context.bot.send_message(
            chat_id=target_user_id,
            text=(
                f"❌ **WITHDRAWAL REJECTED**\n\n"
                f"💰 **Amount:** {amount:,} {CURRENCY}\n"
                f"💳 **Method:** {withdrawal['payment_method']}\n"
                f"📝 **Reason:** {reason}\n\n"
                f"💵 **Previous Balance:** {int(current_balance)} {CURRENCY}\n"
                f"💵 **Refunded Balance:** {int(refunded_balance)} {CURRENCY}\n\n"
                f"🔄 **Your balance has been fully restored**\n"
                f"✅ **You can now request withdrawal again**\n\n"
                f"📞 **Support:** @When_the_night_falls_my_soul_se\n\n"
                f"သင့်ငွေထုတ်မှုကို ငြင်းပယ်ပြီး လက်ကျန်ငွေ ပြန်လည်ထည့်သွင်းပေးပါသည်။"
            )
        )
    except Exception as e:
        logger.error(f"Failed to notify user {target_user_id}: {e}")
        await update.message.reply_text(f"⚠️ **Rejected but failed to notify user**")
    
    logger.info(f"Admin {user_id} rejected and refunded withdrawal: {target_user_id} - {amount} {CURRENCY}")

async def list_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to list all pending withdrawals"""
    user_id = str(update.effective_user.id)
    
    # Check if user is admin
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    # Get all users with pending withdrawals
    users = await db.get_all_users()
    all_pending = []
    
    for user in users:
        pending_withdrawals = user.get("pending_withdrawals", [])
        for withdrawal in pending_withdrawals:
            if withdrawal.get("status") == "PENDING":
                withdrawal["user_id"] = user["user_id"]
                withdrawal["user_name"] = user.get("first_name", "Unknown")
                all_pending.append(withdrawal)
    
    if not all_pending:
        await update.message.reply_text(
            f"✅ **NO PENDING WITHDRAWALS**\n\n"
            f"All withdrawal requests have been processed!\n\n"
            f"📊 **Admin Commands:**\n"
            f"• `/approve <user_id> <amount>` - Approve withdrawal\n"
            f"• `/reject <user_id> <amount>` - Reject withdrawal\n"
            f"• `/list` - List all pending withdrawals"
        )
        return
    
    # Sort by request time (newest first)
    all_pending.sort(key=lambda x: x.get("request_time", ""), reverse=True)
    
    list_text = f"📋 **PENDING WITHDRAWALS ({len(all_pending)})**\n\n"
    
    for i, withdrawal in enumerate(all_pending[:10], 1):  # Show max 10
        user_id_short = withdrawal["user_id"]
        user_name = withdrawal["user_name"]
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
        
        list_text += f"**{i}. {user_name}** ({user_id_short})\n"
        list_text += f"   💰 {amount:,} {CURRENCY} via {method}\n"
        list_text += f"   📅 {date_str}\n"
        list_text += f"   ✅ `/approve {user_id_short} {amount}`\n"
        list_text += f"   ❌ `/reject {user_id_short} {amount}`\n\n"
    
    if len(all_pending) > 10:
        list_text += f"... and {len(all_pending) - 10} more\n\n"
    
    list_text += f"🔧 **Quick Actions:**\n"
    list_text += f"• Copy the approve/reject commands above\n"
    list_text += f"• Add reason to reject: `/reject <id> <amount> reason`\n"
    list_text += f"• Use `/pending` as regular user to check status"
    
    await update.message.reply_text(list_text)

def register_handlers(application: Application):
    """Register admin approval/rejection command handlers"""
    logger.info("Registering admin approval/rejection commands")
    application.add_handler(CommandHandler("approve", approve_command))
    application.add_handler(CommandHandler("reject", reject_command))
    application.add_handler(CommandHandler("list", list_command))
    logger.info("✅ Admin approval/rejection commands registered successfully")
