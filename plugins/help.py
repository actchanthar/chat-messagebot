import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)



from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
from config import CURRENCY, MIN_WITHDRAWAL, MAX_DAILY_WITHDRAWAL, MESSAGE_RATE

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show help information"""
    user_id = str(update.effective_user.id)
    
    help_text = f"""
🤖 **Message Earning Bot Help**

💰 **How to Earn:**
• Send messages in approved groups
• {MESSAGE_RATE} messages = 1 {CURRENCY}
• Minimum withdrawal: {MIN_WITHDRAWAL} {CURRENCY}

📋 **User Commands:**
/balance - Check your balance
/withdraw <amount> <method> <phone> - Request withdrawal
/stats - View your statistics
/withdrawals - View withdrawal history
/referral - Get your referral link
/help - Show this help

💸 **Withdrawal Methods:**
• KPay: `/withdraw 1000 kpay 09123456789`
• Wave Pay: `/withdraw 1000 wavepay 09123456789`
• AYA Pay: `/withdraw 1000 ayapay 09123456789`
• CB Pay: `/withdraw 1000 cbpay 09123456789`

🎯 **Daily Limits:**
• Maximum withdrawal: {MAX_DAILY_WITHDRAWAL:,} {CURRENCY} per day
• Processing time: 24-48 hours

Start chatting in approved groups to earn! 💪
    """
    
    await update.message.reply_text(help_text)

async def referral_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show user's referral link"""
    user_id = str(update.effective_user.id)
    
    bot_username = context.bot.username or "YourBotUsername"
    referral_link = f"https://t.me/{bot_username}?start=ref_{user_id}"
    
    referral_text = f"""
👥 **Invite Friends & Earn!**

🔗 **Your Referral Link:**
`{referral_link}`

💰 **Earn 25 {CURRENCY} for each friend who:**
• Clicks your link
• Starts using the bot
• Sends their first message

📊 **Your Referral Stats:**
Use /stats to see how many people you've referred!

💡 **Tips:**
• Share in groups and social media
• Explain how the bot works
• Help friends get started

Start sharing and earn more! 🚀
    """
    
    await update.message.reply_text(referral_text)

def register_handlers(application: Application):
    """Register help handlers"""
    application.add_handler(CommandHandler("help", help_command))
    application.add_handler(CommandHandler("referral", referral_command))
