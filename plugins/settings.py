from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import ADMIN_IDS, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def set_referral_reward(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to set referral reward amount"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            f"❌ **Invalid usage**\n\n"
            f"**Correct format:**\n"
            f"`/setreferral <amount>`\n\n"
            f"**Example:**\n"
            f"`/setreferral 50`"
        )
        return
    
    try:
        amount = int(context.args[0])
        if amount < 0:
            await update.message.reply_text("❌ Amount must be positive")
            return
        
        # Update in database
        await db.update_settings({"referral_reward": amount})
        
        await update.message.reply_text(
            f"✅ **Referral reward updated**\n\n"
            f"💰 **New reward:** {amount} {CURRENCY} per referral\n"
            f"👨‍💼 **Updated by:** Admin {user_id}"
        )
        
        logger.info(f"Admin {user_id} set referral reward to {amount} {CURRENCY}")
        
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number")

async def set_message_rate(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to set message earning rate"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            f"❌ **Invalid usage**\n\n"
            f"**Correct format:**\n"
            f"`/setrate <messages_per_kyat>`\n\n"
            f"**Example:**\n"
            f"`/setrate 3` (3 messages = 1 kyat)\n"
            f"`/setrate 1` (1 message = 1 kyat)"
        )
        return
    
    try:
        rate = int(context.args[0])
        if rate < 1:
            await update.message.reply_text("❌ Rate must be at least 1")
            return
        
        # Update in database
        await db.update_settings({"message_rate": rate})
        
        await update.message.reply_text(
            f"✅ **Message earning rate updated**\n\n"
            f"📊 **New rate:** {rate} messages = 1 {CURRENCY}\n"
            f"👨‍💼 **Updated by:** Admin {user_id}"
        )
        
        logger.info(f"Admin {user_id} set message rate to {rate} messages per {CURRENCY}")
        
    except ValueError:
        await update.message.reply_text("❌ Please enter a valid number")

async def view_settings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to view current bot settings"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    try:
        # Get current settings
        referral_reward = await db.get_referral_reward()
        message_rate = await db.get_message_rate()
        
        settings_text = (
            f"⚙️ **BOT SETTINGS**\n\n"
            f"💰 **Referral Reward:** {referral_reward} {CURRENCY} per referral\n"
            f"📊 **Message Rate:** {message_rate} messages = 1 {CURRENCY}\n\n"
            f"🔧 **Admin Commands:**\n"
            f"• `/setreferral <amount>` - Set referral reward\n"
            f"• `/setrate <messages>` - Set earning rate\n"
            f"• `/viewsettings` - View current settings"
        )
        
        await update.message.reply_text(settings_text)
        
    except Exception as e:
        logger.error(f"Error viewing settings: {e}")
        await update.message.reply_text("❌ Error retrieving settings")

def register_handlers(application: Application):
    """Register settings command handlers"""
    logger.info("Registering settings commands")
    application.add_handler(CommandHandler("setreferral", set_referral_reward))
    application.add_handler(CommandHandler("setrate", set_message_rate))
    application.add_handler(CommandHandler("viewsettings", view_settings))
    logger.info("✅ Settings commands registered successfully")
