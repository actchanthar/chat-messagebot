from telegram import Update
from telegram.ext import Application, ContextTypes
import logging
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import (
    BOT_TOKEN, CURRENCY, ANNOUNCEMENT_GROUPS, 
    RECEIPT_CHANNEL_ID, RECEIPT_CHANNEL_NAME
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class AnnouncementSystem:
    def __init__(self):
        self.app = None
        self.bot = None
        self.announced_today = set()  # Track announced events today
        
    async def set_app(self, application):
        """Set the application instance"""
        self.app = application
        self.bot = application.bot

    async def announce_new_user(self, user_id: str, user_name: str, referred_by: str = None, context: ContextTypes.DEFAULT_TYPE = None):
        """Announce new user registration (once per day)"""
        try:
            # Check if already announced today
            today_key = f"new_user_{user_id}_{datetime.now().date()}"
            if today_key in self.announced_today:
                return
            
            self.announced_today.add(today_key)
            
            # Get total users for milestone detection
            total_users = await db.get_total_users_count()
            
            # Create announcement based on referral status
            if referred_by:
                referrer = await db.get_user(referred_by)
                referrer_name = referrer.get('first_name', 'Someone') if referrer else 'Someone'
                
                announcement_text = f"""
🎉 **NEW USER JOINED VIA REFERRAL!**

👋 **Welcome:** {user_name}
🔗 **Referred by:** {referrer_name}
👥 **Total Users:** {total_users:,}
📈 **Growth:** +1 new member

💰 **Earn like them:**
• Chat in groups = Earn {CURRENCY}
• Invite friends = Get bonuses
• Be active = Level up!

🚀 **Join now:** @{context.bot.username if context else 'YourBot'}
                """
                
                # Notify referrer privately
                if context and referred_by:
                    try:
                        await context.bot.send_message(
                            chat_id=referred_by,
                            text=f"🎉 **Your referral link worked!**\n\n"
                                 f"👤 **{user_name}** joined using your link!\n"
                                 f"💰 **You earned:** 25 {CURRENCY}\n"
                                 f"🎯 **Keep sharing to earn more!**"
                        )
                    except Exception as e:
                        logger.error(f"Failed to notify referrer {referred_by}: {e}")
            else:
                announcement_text = f"""
🎉 **NEW USER JOINED!**

👋 **Welcome:** {user_name}
👥 **Total Users:** {total_users:,}
📈 **Community Growing!**

💰 **Start earning today:**
• Chat in groups = Earn {CURRENCY}
• Current rate: 3 messages = 1 {CURRENCY}
• Invite friends = Get 25 {CURRENCY} each!

🚀 **Join us:** @{context.bot.username if context else 'YourBot'}
                """
            
            # Send to announcement groups
            for group_id in ANNOUNCEMENT_GROUPS:
                try:
                    if context:
                        await context.bot.send_message(
                            chat_id=group_id,
                            text=announcement_text
                        )
                    logger.info(f"Announced new user to group {group_id}")
                except Exception as e:
                    logger.error(f"Failed to announce to group {group_id}: {e}")
            
            # Send to receipt channel
            try:
                if context:
                    receipt_text = f"""
📝 **USER REGISTRATION RECEIPT**

🆔 **User ID:** {user_id}
👤 **Name:** {user_name}
🔗 **Referral:** {'Yes' if referred_by else 'No'}
📅 **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
👥 **Total Users:** {total_users:,}

✅ **Verified Registration**
🤖 **Bot:** @{context.bot.username}

#NewUser #Registration #Growth
                    """
                    await context.bot.send_message(
                        chat_id=RECEIPT_CHANNEL_ID,
                        text=receipt_text
                    )
            except Exception as e:
                logger.error(f"Failed to send receipt: {e}")
                
        except Exception as e:
            logger.error(f"Error in announce_new_user: {e}")

    async def announce_milestone_reached(self, user_id: str, user_name: str, milestone_type: str, amount: int, context: ContextTypes.DEFAULT_TYPE = None):
        """Announce when user reaches earning milestones (100k, 50k, etc.)"""
        try:
            # Check if already announced this milestone today
            today_key = f"milestone_{user_id}_{milestone_type}_{amount}_{datetime.now().date()}"
            if today_key in self.announced_today:
                return
            
            self.announced_today.add(today_key)
            
            # Determine milestone emoji and text
            if milestone_type == "earnings":
                if amount >= 100000:
                    emoji = "👑"
                    title = "MEGA EARNER ALERT!"
                    description = f"earned {amount:,} {CURRENCY}!"
                elif amount >= 50000:
                    emoji = "💎"
                    title = "BIG EARNER ALERT!"
                    description = f"earned {amount:,} {CURRENCY}!"
                elif amount >= 10000:
                    emoji = "🏆"
                    title = "TOP EARNER!"
                    description = f"earned {amount:,} {CURRENCY}!"
                else:
                    return  # Don't announce smaller milestones
            elif milestone_type == "referrals":
                if amount >= 50:
                    emoji = "🌟"
                    title = "REFERRAL MASTER!"
                    description = f"referred {amount} people!"
                elif amount >= 20:
                    emoji = "🚀"
                    title = "REFERRAL CHAMPION!"
                    description = f"referred {amount} people!"
                else:
                    return
            else:
                return
            
            announcement_text = f"""
{emoji} **{title}**

🎉 **Congratulations {user_name}!**
📊 **Achievement:** Successfully {description}

💪 **This proves our bot pays REAL money!**

🔥 **You can do it too:**
• Chat in groups to earn
• Invite friends for bonuses
• Stay active for more rewards

💰 **Current rate:** 3 messages = 1 {CURRENCY}
🚀 **Join now:** @{context.bot.username if context else 'YourBot'}

#{milestone_type.title()} #Success #RealEarnings
            """
            
            # Send to announcement groups
            for group_id in ANNOUNCEMENT_GROUPS:
                try:
                    if context:
                        await context.bot.send_message(
                            chat_id=group_id,
                            text=announcement_text
                        )
                except Exception as e:
                    logger.error(f"Failed to announce milestone to group {group_id}: {e}")
            
            # Send receipt to channel
            try:
                if context:
                    receipt_text = f"""
🏆 **MILESTONE ACHIEVEMENT RECEIPT**

👤 **User:** {user_name} ({user_id})
🎯 **Milestone:** {milestone_type.title()}
💰 **Amount:** {amount:,} {CURRENCY if milestone_type == 'earnings' else 'referrals'}
📅 **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

✅ **Verified Achievement**
🤖 **Bot:** @{context.bot.username}

#Milestone #{milestone_type.title()} #Success
                    """
                    await context.bot.send_message(
                        chat_id=RECEIPT_CHANNEL_ID,
                        text=receipt_text
                    )
            except Exception as e:
                logger.error(f"Failed to send milestone receipt: {e}")
                
        except Exception as e:
            logger.error(f"Error in announce_milestone_reached: {e}")

    async def announce_withdrawal_success(self, user_id: str, user_name: str, amount: int, method: str, context: ContextTypes.DEFAULT_TYPE = None):
        """Announce successful withdrawal (already implemented in withdrawal.py)"""
        try:
            announcement_text = f"""
💸 **WITHDRAWAL SUCCESSFUL!**

🎉 **{user_name} just received {amount:,} {CURRENCY}!**
💳 **Method:** {method}
📅 **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

✅ **PROOF OUR BOT PAYS REAL MONEY!**

💰 **Start earning too:**
• Chat in groups = Earn {CURRENCY}
• Minimum withdrawal: 200 {CURRENCY}
• Fast processing: 2-24 hours

🚀 **Join now:** @{context.bot.username if context else 'YourBot'}

#Withdrawal #Success #RealPayments
            """
            
            # Send to announcement groups
            for group_id in ANNOUNCEMENT_GROUPS:
                try:
                    if context:
                        await context.bot.send_message(
                            chat_id=group_id,
                            text=announcement_text
                        )
                except Exception as e:
                    logger.error(f"Failed to announce withdrawal to group {group_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in announce_withdrawal_success: {e}")

    async def announce_daily_stats(self, context: ContextTypes.DEFAULT_TYPE = None):
        """Announce daily statistics (can be called via scheduler)"""
        try:
            # Get daily stats
            total_users = await db.get_total_users_count()
            new_users_today = await db.get_new_users_count(1)
            total_earnings = await db.get_total_earnings()
            total_withdrawals = await db.get_total_withdrawals()
            active_users = await db.get_active_users_count(24)
            
            stats_text = f"""
📊 **DAILY BOT STATISTICS**

👥 **Users:** {total_users:,} total ({new_users_today} new today)
💰 **Total Earned:** {int(total_earnings):,} {CURRENCY}
💸 **Total Withdrawn:** {int(total_withdrawals):,} {CURRENCY}
📈 **Active Today:** {active_users:,} users
⚖️ **Economy Health:** {((total_earnings - total_withdrawals) / max(total_earnings, 1) * 100):.1f}%

🔥 **Our bot is growing and paying real money!**

🚀 **Join the earning revolution:** @{context.bot.username if context else 'YourBot'}

#DailyStats #Growth #RealBot
            """
            
            # Send to receipt channel
            if context:
                await context.bot.send_message(
                    chat_id=RECEIPT_CHANNEL_ID,
                    text=stats_text
                )
                
        except Exception as e:
            logger.error(f"Error in announce_daily_stats: {e}")

# Global announcement system instance
announcement_system = AnnouncementSystem()

def register_handlers(application: Application):
    """Register announcement system"""
    logger.info("Registering announcement system")
    
    # Set the application for the announcement system
    async def init_announcements():
        await announcement_system.set_app(application)
    
    # You can schedule this to run on startup
    application.job_queue.run_once(
        lambda context: init_announcements(), 
        when=1
    )
    
    logger.info("✅ Announcement system registered successfully")
