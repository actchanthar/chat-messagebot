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

# Built-in start command (until start.py is created)
async def start_command(update, context):
    user_id = str(update.effective_user.id)
    user_name = {
        "first_name": update.effective_user.first_name or "",
        "last_name": update.effective_user.last_name or ""
    }
    
    # Check for referral
    referred_by = None
    if context.args and context.args[0].startswith("ref_"):
        referred_by = context.args[0][4:]
    
    user = await db.get_user(user_id)
    if not user:
        await db.create_user(user_id, user_name, referred_by)
        welcome_message = """
🎉 Welcome to the World's Most Advanced Earning Bot!

💰 Earn money by chatting in approved groups
📝 3 messages = 1 kyat
🎯 Minimum withdrawal: 200 kyat
💸 Daily limit: 10,000 kyat

Commands:
/balance - Check your earnings
/stats - View detailed statistics  
/withdraw - Request withdrawal
/help - Get help
/top - View leaderboards

Start chatting in approved groups to earn! 💪
        """
    else:
        current_balance = user.get('balance', 0)
        welcome_message = f"Welcome back! Your balance: {int(current_balance)} kyat\n\nUse /help to see all commands!"
    
    await update.message.reply_text(welcome_message)

def main():
    # Create application
    application = Application.builder().token(BOT_TOKEN).build()
    
    logger.info("🚀 Starting World's Most Advanced Message Earning Bot...")
    
    # Add built-in start command first
    application.add_handler(CommandHandler("start", start_command))
    
    # Import and register core handlers
    try:
        logger.info("📋 Registering core handlers...")
        
        from plugins.message_handler import register_handlers as register_message_handlers
        from plugins.balance import register_handlers as register_balance_handlers
        from plugins.admin import register_handlers as register_admin_handlers
        from plugins.broadcast import register_handlers as register_broadcast_handlers
        from plugins.withdrawal import register_handlers as register_withdrawal_handlers
        from plugins.stats import register_handlers as register_stats_handlers
        from plugins.help import register_handlers as register_help_handlers
        
        # Register core handlers
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
        logger.info("🔧 Some plugins missing, continuing with available ones...")
    
    # Try to register advanced feature handlers
    try:
        logger.info("🎮 Registering advanced feature handlers...")
        
        # Try to import advanced handlers
        try:
            from plugins.leaderboard import register_handlers as register_leaderboard_handlers
            register_leaderboard_handlers(application)
            logger.info("✅ Leaderboard handlers registered")
        except ImportError:
            logger.warning("⚠️ Leaderboard plugin not found, creating basic /top command...")
            
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
            logger.info("✅ Basic /top command registered")
            
        try:
            from plugins.challenges import register_handlers as register_challenges_handlers
            register_challenges_handlers(application)
            logger.info("✅ Challenges handlers registered")
        except ImportError:
            logger.warning("⚠️ Challenges plugin not found")
            
            async def basic_challenges_command(update, context):
                await update.message.reply_text(
                    "🎯 **Daily Challenges Coming Soon!**\n\n"
                    "Advanced challenge system is being prepared.\n"
                    "For now, keep earning by sending messages!"
                )
            
            application.add_handler(CommandHandler("challenges", basic_challenges_command))
            application.add_handler(CommandHandler("daily", basic_challenges_command))
            logger.info("✅ Basic challenges commands registered")
            
        try:
            from plugins.premium import register_handlers as register_premium_handlers
            register_premium_handlers(application)
            logger.info("✅ Premium handlers registered")
        except ImportError:
            logger.warning("⚠️ Premium plugin not found")
            
            async def basic_premium_command(update, context):
                await update.message.reply_text(
                    "👑 **Premium Features Coming Soon!**\n\n"
                    "Advanced VIP system is being developed.\n"
                    "Stay tuned for exclusive premium benefits!"
                )
            
            application.add_handler(CommandHandler("premium", basic_premium_command))
            logger.info("✅ Basic premium command registered")
            
        try:
            from plugins.analytics import register_handlers as register_analytics_handlers
            register_analytics_handlers(application)
            logger.info("✅ Analytics handlers registered")
        except ImportError:
            logger.warning("⚠️ Analytics plugin not found")
        
        # Try to register start.py handlers (if exists)
        try:
            from start import register_handlers as register_start_handlers
            register_start_handlers(application)
            logger.info("✅ Advanced start handlers registered")
        except ImportError:
            logger.info("✅ Using built-in start command")
            
    except Exception as e:
        logger.error(f"❌ Error registering advanced handlers: {e}")
    
    # Initialize advanced systems if available
    try:
        from utils.achievement_system import achievement_system
        from utils.economy_manager import economy_manager
        logger.info("✅ Achievement and Economy systems initialized")
    except ImportError:
        logger.info("✅ Running with core features (advanced systems will be added)")
    
    # Start the bot
    logger.info("🤖 Message Earning Bot started successfully!")
    logger.info("💰 Ready to process earnings!")
    logger.info("🎮 Available commands: /start, /balance, /withdraw, /stats, /help, /top")
    
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == '__main__':
    main()
