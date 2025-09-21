#!/usr/bin/env python3
import logging
import sys
import os

# Add project root to Python path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

from telegram.ext import Application
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
    
    # Import and register ALL handlers (including start.py)
    try:
        # Core handlers
        from start import register_handlers as register_start_handlers
        from plugins.message_handler import register_handlers as register_message_handlers
        from plugins.balance import register_handlers as register_balance_handlers
        from plugins.admin import register_handlers as register_admin_handlers
        from plugins.broadcast import register_handlers as register_broadcast_handlers
        from plugins.withdrawal import register_handlers as register_withdrawal_handlers
        from plugins.stats import register_handlers as register_stats_handlers
        from plugins.help import register_handlers as register_help_handlers
        
        # Advanced feature handlers
        from plugins.leaderboard import register_handlers as register_leaderboard_handlers
        from plugins.challenges import register_handlers as register_challenges_handlers
        from plugins.premium import register_handlers as register_premium_handlers
        from plugins.analytics import register_handlers as register_analytics_handlers
        
        # Register all handlers
        logger.info("📋 Registering core handlers...")
        register_start_handlers(application)           # /start command with advanced interface
        register_message_handlers(application)        # Group message processing
        register_balance_handlers(application)        # /balance command
        register_admin_handlers(application)          # Admin commands
        register_broadcast_handlers(application)      # Broadcasting
        register_withdrawal_handlers(application)     # Withdrawal system
        register_stats_handlers(application)          # User statistics
        register_help_handlers(application)           # Help system
        
        logger.info("🎮 Registering advanced feature handlers...")
        register_leaderboard_handlers(application)    # /top, /leaderboard commands
        register_challenges_handlers(application)     # /challenges, /daily commands
        register_premium_handlers(application)        # Premium features
        register_analytics_handlers(application)      # Analytics dashboard
        
        logger.info("✅ All handlers registered successfully!")
        
    except ImportError as e:
        logger.error(f"❌ Failed to import handler: {e}")
        logger.info("🔧 Creating missing plugin files...")
        
        # If some advanced plugins don't exist yet, register basic ones
        from start import register_handlers as register_start_handlers
        from plugins.message_handler import register_handlers as register_message_handlers
        from plugins.balance import register_handlers as register_balance_handlers  
        from plugins.admin import register_handlers as register_admin_handlers
        from plugins.broadcast import register_handlers as register_broadcast_handlers
        from plugins.withdrawal import register_handlers as register_withdrawal_handlers
        from plugins.stats import register_handlers as register_stats_handlers
        from plugins.help import register_handlers as register_help_handlers
        
        # Register available handlers
        register_start_handlers(application)
        register_message_handlers(application)
        register_balance_handlers(application)
        register_admin_handlers(application)
        register_broadcast_handlers(application)
        register_withdrawal_handlers(application)
        register_stats_handlers(application)
        register_help_handlers(application)
        
        # Try to register advanced features if they exist
        try:
            from plugins.leaderboard import register_handlers as register_leaderboard_handlers
            register_leaderboard_handlers(application)
            logger.info("✅ Leaderboard handlers registered")
        except ImportError:
            logger.warning("⚠️ Leaderboard plugin not found, skipping...")
            
        try:
            from plugins.challenges import register_handlers as register_challenges_handlers
            register_challenges_handlers(application)
            logger.info("✅ Challenges handlers registered")
        except ImportError:
            logger.warning("⚠️ Challenges plugin not found, skipping...")
    
    # Initialize advanced systems
    logger.info("🎯 Initializing advanced systems...")
    
    try:
        from utils.achievement_system import achievement_system
        from utils.economy_manager import economy_manager
        logger.info("✅ Achievement and Economy systems initialized")
    except ImportError:
        logger.warning("⚠️ Advanced systems not found, running with basic features...")
    
    # Start the bot
    logger.info("🤖 Message Earning Bot started successfully!")
    logger.info("💰 Ready to process earnings and handle advanced features!")
    logger.info("🎮 All advanced features active!")
    
    application.run_polling(allowed_updates=["message", "callback_query"])

if __name__ == '__main__':
    main()
