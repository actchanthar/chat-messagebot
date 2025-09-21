#!/usr/bin/env python3
import logging
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from telegram.ext import Application, CommandHandler
from config import BOT_TOKEN
from database.database import db

logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def main():
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    logger.info("🚀 Starting World's Most Advanced Message Earning Bot...")
    
    # Import and register core handlers FIRST
    try:
        logger.info("📋 Registering core handlers...")
        
        # Import start.py FIRST to override default start
        from start import register_handlers as register_start_handlers
        register_start_handlers(application)
        logger.info("✅ Advanced start handlers registered")
        
        # Then register other handlers
        from plugins.message_handler import register_handlers as register_message_handlers
        from plugins.balance import register_handlers as register_balance_handlers
        from plugins.admin import register_handlers as register_admin_handlers
        from plugins.broadcast import register_handlers as register_broadcast_handlers
        from plugins.withdrawal import register_handlers as register_withdrawal_handlers
        from plugins.stats import register_handlers as register_stats_handlers
        from plugins.help import register_handlers as register_help_handlers
        
        register_message_handlers(application)
        register_balance_handlers(application)
        register_admin_handlers(application)
        register_broadcast_handlers(application)
        register_withdrawal_handlers(application)
        register_stats_handlers(application)
        register_help_handlers(application)
        
        logger.info("✅ Core handlers registered successfully!")
        
    except ImportError as e:
        logger.error(f"❌ Failed to import core handler: {e}")
        
        # Fallback - add basic start command if start.py fails
        async def basic_start_command(update, context):
            user_id = str(update.effective_user.id)
            user_name = {
                "first_name": update.effective_user.first_name or "",
                "last_name": update.effective_user.last_name or ""
            }
            
            user = await db.get_user(user_id)
            if not user:
                await db.create_user(user_id, user_name)
                await update.message.reply_text("Welcome! You've been registered.")
            else:
                balance = user.get('balance', 0)
                await update.message.reply_text(f"Welcome back! Balance: {int(balance)} kyat")
        
        application.add_handler(CommandHandler("start", basic_start_command))
    
    # Try to register advanced feature handlers
    try:
        logger.info("🎮 Registering advanced features...")
        
        try:
            from plugins.leaderboard import register_handlers as register_leaderboard_handlers
            register_leaderboard_handlers(application)
            logger.info("✅ Leaderboard handlers registered")
        except ImportError:
            logger.warning("⚠️ Leaderboard plugin not found")
            
            async def basic_top_command(update, context):
                try:
                    top_users = await db.get_top_users(10, "total_earnings")
                    if not top_users:
                        await update.message.reply_text("📊 No users found yet!")
                        return
                    
                    leaderboard_text = "🏆 **TOP EARNERS LEADERBOARD**\n\n"
                    
                    for i, user in enumerate(top_users[:10], 1):
                        name = user.get('first_name', 'Unknown')[:15]
                        earnings = user.get('total_earnings', 0)
                        medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                        leaderboard_text += f"{medal} {name} - {int(earnings)} kyat\n"
                    
                    leaderboard_text += "\n🎯 Keep earning to climb the leaderboard!"
                    await update.message.reply_text(leaderboard_text)
                except Exception as e:
                    logger.error(f"Error in basic top command: {e}")
                    await update.message.reply_text("❌ Error loading leaderboard")
            
            application.add_handler(CommandHandler("top", basic_top_command))
            
        try:
            from plugins.challenges import register_handlers as register_challenges_handlers
            register_challenges_handlers(application)
            logger.info("✅ Challenges handlers registered")
        except ImportError:
            logger.warning("⚠️ Challenges plugin not found")
            
    except Exception as e:
        logger.error(f"❌ Error registering advanced handlers: {e}")
    
    # Start the bot
    logger.info("🤖 Message Earning Bot started successfully!")
    logger.info("💰 Ready to process earnings!")
    
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == '__main__':
    main()
