#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import asyncio
import logging
import sys
import os
from telegram import Update
from telegram.ext import Application, ContextTypes

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Import configuration
from config import BOT_TOKEN

# Import database
from database.database import init_database

# Import all plugins
from plugins import start, withdrawal, message_handler, admin, leaderboard, force_join

# Set up logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

async def post_init(application: Application) -> None:
    """Initialize database and other async components after bot starts"""
    try:
        logger.info("🔄 Initializing database connection...")
        await init_database()
        logger.info("✅ Database connected successfully")
        
        # Get bot info
        bot_info = await application.bot.get_me()
        logger.info(f"🤖 Bot started: @{bot_info.username} ({bot_info.first_name})")
        
    except Exception as e:
        logger.error(f"❌ Failed to initialize components: {e}")
        raise

async def post_shutdown(application: Application) -> None:
    """Clean up resources when bot shuts down"""
    try:
        logger.info("🔄 Shutting down bot...")
        
        # Close database connection
        from database.database import db
        await db.close()
        logger.info("✅ Database connection closed")
        
    except Exception as e:
        logger.error(f"❌ Error during shutdown: {e}")

def main() -> None:
    """Start the bot"""
    try:
        logger.info("🚀 Starting Telegram Bot...")
        
        # Create the Application
        application = Application.builder().token(BOT_TOKEN).build()
        
        # Register handlers from all plugins
        logger.info("📝 Registering handlers...")
        
        # Register plugin handlers in order of priority
        start.register_handlers(application)
        withdrawal.register_handlers(application)
        message_handler.register_handlers(application)
        admin.register_handlers(application)
        leaderboard.register_handlers(application)
        force_join.register_handlers(application)
        
        logger.info("✅ All handlers registered successfully")
        
        # Set post init and shutdown hooks
        application.post_init = post_init
        application.post_shutdown = post_shutdown
        
        # Start the bot
        logger.info("🏃‍♂️ Bot is running! Press Ctrl+C to stop.")
        application.run_polling(
            allowed_updates=Update.ALL_TYPES,
            drop_pending_updates=True,
            close_loop=False
        )
        
    except KeyboardInterrupt:
        logger.info("⏹️ Bot stopped by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == '__main__':
    main()
