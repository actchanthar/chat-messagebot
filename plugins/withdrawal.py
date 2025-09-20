from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
from database.database import db
import logging
import re
from datetime import datetime
from config import ADMIN_IDS, LOG_CHANNEL_ID, CURRENCY, MIN_WITHDRAWAL, MAX_DAILY_WITHDRAWAL

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

PAYMENT_PATTERNS = {
    "kpay": r"^09\d{7,9}$",
    "wavepay": r"^09\d{7,9}$",  
    "ayapay": r"^09\d{7,9}$",
    "cbpay": r"^09\d{7,9}$",
}

PAYMENT_METHODS = {
    "kpay": "KBZ Pay",
    "wavepay": "Wave Pay", 
    "ayapay": "AYA Pay",
    "cbpay": "CB Pay"
}

async def request_withdrawal(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal requests"""
    user_id = str(update.effective_user.id)
    chat_id = update.effective_chat.id
    
    # Check if command is used in private chat
    if chat_id != int(user_id):
        await update.message.reply_text(
            "⚠️ For security, withdrawal requests must be made in private chat.\n"
            "Please message me directly."
        )
        return
    
    # Validate arguments
    if not context.args or len(context.args) < 3:
        usage_text = f"""
💸 **Withdrawal Request Format:**

**Usage:** `/withdraw <amount> <method> <phone_number>`

**Available Methods:**
• `kpay` - KBZ Pay
• `wavepay` - Wave Pay  
• `ayapay` - AYA Pay
• `cbpay` - CB Pay

**Examples:**
• `/withdraw 1000 kpay 09123456789`
• `/withdraw 2000 wavepay 09987654321`

**Requirements:**
• Minimum: {MIN_WITHDRAWAL} {CURRENCY}
• Maximum per day: {MAX_DAILY_WITHDRAWAL:,} {CURRENCY}
• Processing time: 24-48 hours
        """
        await update.message.reply_text(usage_text)
        return
    
    try:
        # Parse arguments
        amount_str = context.args[0]
        method = context.args[1].lower()
        phone_number = context.args[2]
        
        # Validate amount
        try:
            amount = int(float(amount_str))
        except ValueError:
            await update.message.reply_text("❌ Invalid amount. Please enter a whole number.")
            return
        
        # Validate minimum amount
        if amount < MIN_WITHDRAWAL:
            await update.message.reply_text(f"❌ Minimum withdrawal amount is {MIN_WITHDRAWAL} {CURRENCY}")
            return
        
        # Validate maximum amount  
        if amount > MAX_DAILY_WITHDRAWAL:
            await update.message.reply_text(f"❌ Maximum withdrawal amount is {MAX_DAILY_WITHDRAWAL:,} {CURRENCY} per day")
            return
        
        # Validate payment method
        if method not in PAYMENT_METHODS:
            methods_list = ", ".join([f"`{k}`" for k in PAYMENT_METHODS.keys()])
            await update.message.reply_text(f"❌ Invalid payment method. Available: {methods_list}")
            return
        
        # Validate phone number format
        if method in PAYMENT_PATTERNS:
            if not re.match(PAYMENT_PATTERNS[method], phone_number):
                await update.message.reply_text(
                    f"❌ Invalid phone number format for {PAYMENT_METHODS[method]}.\n"
                    f"Expected format: 09XXXXXXXX"
                )
                return
        
        # Get user data
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found. Please start with /start")
            return
        
        # Check if user is banned
        if user.get("banned", False):
            await update.message.reply_text("❌ Your account is suspended.")
            return
        
        # Validate user balance
        current_balance = user.get("balance", 0)
        if current_balance < amount:
            await update.message.reply_text(
                f"❌ Insufficient balance!\n"
                f"💰 Your balance: {int(current_balance)} {CURRENCY}\n"
                f"💸 Requested: {amount} {CURRENCY}"
            )
            return
        
        # Create withdrawal request confirmation
        confirmation_text = f"""
🔍 **Withdrawal Request Confirmation**

💰 **Amount:** {amount:,} {CURRENCY}
📱 **Method:** {PAYMENT_METHODS[method]}
📞 **Phone:** {phone_number}
💳 **Current Balance:** {int(current_balance)} {CURRENCY}
💵 **After Withdrawal:** {int(current_balance - amount)} {CURRENCY}

⏱️ **Processing Time:** 24-48 hours
💼 **Status:** Pending Admin Approval

❓ **Confirm this withdrawal request?**
        """
        
        # Create confirmation keyboard
        keyboard = [
            [
                InlineKeyboardButton("✅ Confirm", callback_data=f"confirm_withdraw:{amount}:{method}:{phone_number}"),
                InlineKeyboardButton("❌ Cancel", callback_data="cancel_withdraw")
            ]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(confirmation_text, reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error processing withdrawal request: {e}")
        await update.message.reply_text("❌ An error occurred. Please try again.")

async def handle_withdrawal_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle withdrawal confirmation callbacks"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    
    try:
        if data == "cancel_withdraw":
            await query.edit_message_text("❌ Withdrawal request cancelled.")
            return
        
        if data.startswith("confirm_withdraw:"):
            # Parse callback data
            _, amount_str, method, phone_number = data.split(":", 3)
            amount = int(float(amount_str))
            
            # Create withdrawal request
            result = await db.create_withdrawal_request(
                user_id=user_id,
                amount=amount,
                payment_method=method,
                payment_details=phone_number
            )
            
            if result["success"]:
                withdrawal_id = result["withdrawal_id"]
                
                success_text = f"""
✅ **Withdrawal Request Submitted!**

🆔 **Request ID:** `{withdrawal_id}`
💰 **Amount:** {amount:,} {CURRENCY}
📱 **Method:** {PAYMENT_METHODS[method]}
📞 **Phone:** {phone_number}

📋 **Status:** Pending Review
⏱️ **Processing Time:** 24-48 hours
🔔 **You will be notified when processed**

💡 **Note:** Your balance has been reserved for this withdrawal.
                """
                
                await query.edit_message_text(success_text)
                
                # Notify admins
                try:
                    admin_notification = f"""
🔔 **New Withdrawal Request**

👤 **User:** {query.from_user.first_name} ({user_id})
🆔 **Request ID:** `{withdrawal_id}`
💰 **Amount:** {amount:,} {CURRENCY}
📱 **Method:** {PAYMENT_METHODS[method]}
📞 **Phone:** {phone_number}
📅 **Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')}
                    """
                    
                    await context.bot.send_message(
                        chat_id=LOG_CHANNEL_ID,
                        text=admin_notification
                    )
                except:
                    pass
                
            else:
                error_reason = result.get("reason", "Unknown error")
                await query.edit_message_text(f"❌ Withdrawal failed: {error_reason}")
                
    except Exception as e:
        logger.error(f"Error handling withdrawal callback: {e}")
        await query.edit_message_text("❌ An error occurred.")

async def withdrawal_history(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's withdrawal history"""
    user_id = str(update.effective_user.id)
    
    try:
        user = await db.get_user(user_id)
        if not user:
            await update.message.reply_text("❌ User not found.")
            return
        
        # Get recent withdrawals (simplified)
        pending_withdrawals = user.get("pending_withdrawals", [])
        
        if not pending_withdrawals:
            await update.message.reply_text("📋 No withdrawal history found.")
            return
        
        history_text = "💸 **Your Recent Withdrawals:**\n\n"
        
        for withdrawal in pending_withdrawals[-5:]:  # Show last 5
            amount = withdrawal.get("amount", 0)
            status = withdrawal.get("status", "pending").title()
            
            status_emoji = {
                "Pending": "⏳",
                "Approved": "✅", 
                "Completed": "✅",
                "Rejected": "❌"
            }.get(status, "❓")
            
            history_text += f"{status_emoji} **{amount:,} {CURRENCY}** - {status}\n"
        
        await update.message.reply_text(history_text)
        
    except Exception as e:
        logger.error(f"Error getting withdrawal history: {e}")
        await update.message.reply_text("❌ Error retrieving history.")

def register_handlers(application: Application):
    """Register withdrawal handlers"""
    application.add_handler(CommandHandler("withdraw", request_withdrawal))
    application.add_handler(CommandHandler("withdrawals", withdrawal_history))
    application.add_handler(CallbackQueryHandler(handle_withdrawal_callback, pattern="^(confirm_withdraw|cancel_withdraw)"))
