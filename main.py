#!/usr/bin/env python3
import logging
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from telegram.ext import Application, CommandHandler
from config import BOT_TOKEN
from database.database import db, init_database

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

    try:
        logger.info("📋 Registering handlers...")

        # Import start.py from PLUGINS directory
        from plugins.start import register_handlers as register_start_handlers
        register_start_handlers(application)
        logger.info("✅ Start handlers registered")

        # Import new handlers - Pending and Approve commands
        from plugins.pending import register_handlers as register_pending_handlers
        from plugins.approve import register_handlers as register_approve_handlers
        
        register_pending_handlers(application)
        register_approve_handlers(application)
        logger.info("✅ Pending and approve handlers registered")

        # Import settings handlers
        from plugins.settings import register_handlers as register_settings_handlers
        register_settings_handlers(application)
        logger.info("✅ Settings handlers registered")

        # Import core handlers
        from plugins.message_handler import register_handlers as register_message_handlers
        from plugins.balance import register_handlers as register_balance_handlers
        from plugins.admin import register_handlers as register_admin_handlers
        from plugins.broadcast import register_handlers as register_broadcast_handlers
        from plugins.withdrawal import register_handlers as register_withdrawal_handlers
        from plugins.withdrawals import register_handlers as register_withdrawals_handlers
        from plugins.stats import register_handlers as register_stats_handlers
        from plugins.help import register_handlers as register_help_handlers

        register_message_handlers(application)
        register_balance_handlers(application)
        register_admin_handlers(application)
        register_broadcast_handlers(application)
        register_withdrawal_handlers(application)
        register_withdrawals_handlers(application)
        register_stats_handlers(application)
        register_help_handlers(application)

        # Import advanced handlers
        from plugins.leaderboard import register_handlers as register_leaderboard_handlers
        from plugins.challenges import register_handlers as register_challenges_handlers
        from plugins.analytics import register_handlers as register_analytics_handlers

        register_leaderboard_handlers(application)
        register_challenges_handlers(application)
        register_analytics_handlers(application)

        # Import announcements system
        try:
            from plugins.announcements import register_handlers as register_announcements_handlers
            register_announcements_handlers(application)
            logger.info("✅ Announcements registered")
        except ImportError:
            logger.warning("⚠️ Announcements system not found, continuing without it")

        # Import auto-forward system
        try:
            from plugins.auto_forward import register_handlers as register_autoforward_handlers
            register_autoforward_handlers(application)
            logger.info("✅ Auto-forward handlers registered")
        except ImportError:
            logger.warning("⚠️ Auto-forward system not found, continuing without it")

        logger.info("✅ All handlers registered!")

    except ImportError as e:
        logger.error(f"❌ Import error: {e}")

        # Fallback start command
        async def basic_start(update, context):
            user_id = str(update.effective_user.id)
            user = await db.get_user(user_id)
            if not user:
                await db.create_user(user_id, {"first_name": update.effective_user.first_name or ""})
                await update.message.reply_text("Welcome! You're registered.")
            else:
                balance = user.get('balance', 0)
                await update.message.reply_text(f"Welcome back! Balance: {int(balance)} kyat")

        application.add_handler(CommandHandler("start", basic_start))

    # Initialize database connection manually before starting
    async def post_init(application):
        """Initialize database after app starts"""
        logger.info("🔗 Connecting to database...")
        try:
            await init_database()
            logger.info("✅ Database connected successfully")
        except Exception as e:
            logger.error(f"❌ Database connection failed: {e}")

    # Use post_init callback
    application.post_init = post_init

    # Start the bot
    logger.info("🤖 Bot started successfully!")
    logger.info("💰 Ready to process all commands!")
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == '__main__':
    main()
