from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY, ADMIN_IDS, RECEIPT_CHANNEL_NAME

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def receipts_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show receipt channel info and latest receipts"""
    
    receipts_text = f"""
🧾 **WITHDRAWAL RECEIPTS**

🏆 **Trust & Transparency**
Our bot publishes every withdrawal receipt to prove we pay real money to users!

📋 **Receipt Channel:** {RECEIPT_CHANNEL_NAME}

✅ **What receipts show:**
• Real withdrawal amounts
• User verification (anonymous)
• Processing timestamps
• Admin approval confirmations

🎯 **Why we do this:**
• Build user trust
• Prove legitimacy
• Show active community
• Encourage new users

💰 **Recent Activity:**
• Today's Withdrawals: Calculating...
• This Week: Calculating...
• Total Processed: Calculating...

📢 **Share the receipt channel with friends!**
Prove that our bot actually pays money!

🚀 **Start Earning:** /start
    """
    
    keyboard = [
        [InlineKeyboardButton("🧾 View Receipts", url=f"https://t.me/{RECEIPT_CHANNEL_NAME[1:]}")],
        [InlineKeyboardButton("💰 Start Earning", callback_data="start_earning")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(receipts_text, reply_markup=reply_markup)

def register_handlers(application: Application):
    """Register receipt handlers"""
    logger.info("Registering receipt handlers")
    application.add_handler(CommandHandler("receipts", receipts_command))
    logger.info("✅ Receipt handlers registered successfully")
