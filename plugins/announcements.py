from telegram import Update
from telegram.ext import Application, ContextTypes
import logging
from datetime import datetime, timezone
import asyncio
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import (
    ANNOUNCEMENT_GROUPS, 
    GENERAL_ANNOUNCEMENT_GROUPS,
    RECEIPT_CHANNEL_ID,
    AUTO_ANNOUNCE_WITHDRAWALS, 
    AUTO_ANNOUNCE_NEW_USERS, 
    AUTO_ANNOUNCE_MILESTONES,
    CURRENCY,
    MIN_WITHDRAWAL
)

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

class AnnouncementSystem:
    def __init__(self):
        self.enabled = True
        logger.info("Announcement system initialized")

    async def announce_withdrawal_success(self, user_id: str, user_name: str, amount: int, method: str, context):
        """Announce successful withdrawal - ONLY to proof channel"""
        try:
            if not AUTO_ANNOUNCE_WITHDRAWALS:
                return
                
            announcement_text = f"""💸 **WITHDRAWAL SUCCESSFUL!**

🎉 **{user_name} just received {amount:,} {CURRENCY}!**
💳 **Method:** {method}
📅 **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

✅ **PROOF OUR BOT PAYS REAL MONEY!**

💰 **Start earning too:**
• Chat in groups = Earn {CURRENCY}
• Minimum withdrawal: {MIN_WITHDRAWAL} {CURRENCY}
• Fast processing: 2-24 hours

🚀 **Join now:** t.me/{context.bot.username}

#Withdrawal #Success #RealPayments"""

            # Send only to proof channel
            try:
                await context.bot.send_message(
                    chat_id=RECEIPT_CHANNEL_ID,
                    text=announcement_text
                )
                logger.info(f"✅ Withdrawal announcement sent to proof channel {RECEIPT_CHANNEL_ID}")
            except Exception as e:
                logger.error(f"❌ Failed to send withdrawal announcement: {e}")
                
                # Fallback: try announcement groups
                for group_id in ANNOUNCEMENT_GROUPS:
                    try:
                        await context.bot.send_message(
                            chat_id=group_id,
                            text=announcement_text
                        )
                        logger.info(f"✅ Fallback: Sent to {group_id}")
                        break
                    except Exception as e2:
                        logger.error(f"❌ Fallback failed for {group_id}: {e2}")
                
        except Exception as e:
            logger.error(f"Error in announce_withdrawal_success: {e}")

    async def announce_new_user(self, user_id: str, user_name: str, referred_by: str, context):
        """Announce new user - to main groups"""
        try:
            if not AUTO_ANNOUNCE_NEW_USERS:
                return
                
            if referred_by:
                referrer = await db.get_user(referred_by)
                referrer_name = referrer.get('first_name', 'Someone') if referrer else 'Someone'
                announcement_text = f"""🎉 **New Member Alert!**

👤 **{user_name}** joined through **{referrer_name}**'s referral link!

💰 **Welcome to our earning community!** 
🚀 Start chatting to earn {CURRENCY}!

#NewMember #Referral #Welcome"""
            else:
                announcement_text = f"""🎉 **New Member Alert!**

👤 **{user_name}** just joined our earning community!

💰 **Welcome!** Start chatting to earn {CURRENCY}!
🔗 **Invite friends:** Share your referral link

#NewMember #Welcome"""

            # Send to general announcement groups (main earning groups)
            for group_id in GENERAL_ANNOUNCEMENT_GROUPS:
                try:
                    await context.bot.send_message(
                        chat_id=group_id,
                        text=announcement_text
                    )
                    logger.info(f"✅ New user announcement sent to {group_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to announce new user to {group_id}: {e}")
                    
        except Exception as e:
            logger.error(f"Error in announce_new_user: {e}")

    async def announce_milestone_reached(self, user_id: str, user_name: str, milestone_type: str, amount: int, context):
        """Announce milestone achievements - to main groups"""
        try:
            if not AUTO_ANNOUNCE_MILESTONES:
                return

            if milestone_type == "earnings":
                milestone_text = f"""🏆 **MILESTONE ACHIEVED!**

🎉 **{user_name}** just reached **{amount:,} {CURRENCY}** total earnings!

💰 **Amazing achievement!** Keep chatting to earn more!
🔥 **Join the earning race!**

#Milestone #Earnings #Achievement"""
            
            elif milestone_type == "referrals":
                milestone_text = f"""👥 **REFERRAL CHAMPION!**

🎉 **{user_name}** just reached **{amount} successful referrals!**

🔗 **Amazing networking!** Share your link to earn more!
💰 **Each referral = more {CURRENCY}!**

#Milestone #Referral #Champion"""
            
            elif milestone_type == "messages":
                milestone_text = f"""📝 **CHAT CHAMPION!**

🎉 **{user_name}** just sent their **{amount:,}th message!**

💬 **Keep chatting to earn more {CURRENCY}!**
🚀 **Every message counts!**

#Milestone #Messages #Champion"""
            
            else:
                return

            # Send to general announcement groups
            for group_id in GENERAL_ANNOUNCEMENT_GROUPS:
                try:
                    await context.bot.send_message(
                        chat_id=group_id,
                        text=milestone_text
                    )
                    logger.info(f"✅ Milestone announcement sent to {group_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to announce milestone to {group_id}: {e}")

        except Exception as e:
            logger.error(f"Error in announce_milestone_reached: {e}")

    async def announce_top_earner(self, user_id: str, user_name: str, rank: int, amount: int, context):
        """Announce top earner achievements"""
        try:
            if rank <= 3:  # Only announce top 3
                rank_emoji = ["🥇", "🥈", "🥉"][rank - 1]
                
                announcement_text = f"""🏆 **TOP EARNER ALERT!**

{rank_emoji} **{user_name}** is now #{rank} with **{amount:,} {CURRENCY}** earned!

💰 **Join the leaderboard race!**
🚀 **Chat more to climb the rankings!**

#TopEarner #Leaderboard #Achievement"""

                # Send to general announcement groups
                for group_id in GENERAL_ANNOUNCEMENT_GROUPS:
                    try:
                        await context.bot.send_message(
                            chat_id=group_id,
                            text=announcement_text
                        )
                        logger.info(f"✅ Top earner announcement sent to {group_id}")
                    except Exception as e:
                        logger.error(f"❌ Failed to announce top earner to {group_id}: {e}")

        except Exception as e:
            logger.error(f"Error in announce_top_earner: {e}")

    async def announce_daily_stats(self, context, total_users: int, total_messages: int, total_earnings: int):
        """Announce daily statistics"""
        try:
            stats_text = f"""📊 **DAILY STATS UPDATE**

👥 **Total Users:** {total_users:,}
💬 **Messages Today:** {total_messages:,}
💰 **Total Earnings:** {total_earnings:,} {CURRENCY}

🚀 **Keep the momentum going!**
💪 **Chat more, earn more!**

#DailyStats #Growth #Community"""

            # Send to general announcement groups
            for group_id in GENERAL_ANNOUNCEMENT_GROUPS:
                try:
                    await context.bot.send_message(
                        chat_id=group_id,
                        text=stats_text
                    )
                    logger.info(f"✅ Daily stats sent to {group_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to send daily stats to {group_id}: {e}")

        except Exception as e:
            logger.error(f"Error in announce_daily_stats: {e}")

    async def announce_system_update(self, message: str, context):
        """Announce system updates to all groups"""
        try:
            update_text = f"""🔔 **SYSTEM UPDATE**

{message}

📅 **Date:** {datetime.now().strftime('%Y-%m-%d %H:%M')}

#SystemUpdate #Announcement"""

            # Send to all groups (both announcement and general)
            all_groups = list(set(ANNOUNCEMENT_GROUPS + GENERAL_ANNOUNCEMENT_GROUPS))
            
            for group_id in all_groups:
                try:
                    await context.bot.send_message(
                        chat_id=group_id,
                        text=update_text
                    )
                    logger.info(f"✅ System update sent to {group_id}")
                except Exception as e:
                    logger.error(f"❌ Failed to send system update to {group_id}: {e}")

        except Exception as e:
            logger.error(f"Error in announce_system_update: {e}")

    async def test_announcements(self, context):
        """Test announcement system"""
        try:
            test_text = f"""🧪 **ANNOUNCEMENT SYSTEM TEST**

✅ **System Status:** Online
📅 **Test Time:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

🔧 **Channels Configured:**
• Proof Channel: {RECEIPT_CHANNEL_ID}
• Main Groups: {len(GENERAL_ANNOUNCEMENT_GROUPS)} groups

#SystemTest #AnnouncementTest"""

            # Test proof channel
            try:
                await context.bot.send_message(
                    chat_id=RECEIPT_CHANNEL_ID,
                    text=f"🧪 **PROOF CHANNEL TEST**\n\n{test_text}"
                )
                logger.info("✅ Proof channel test successful")
            except Exception as e:
                logger.error(f"❌ Proof channel test failed: {e}")

            # Test general groups
            for group_id in GENERAL_ANNOUNCEMENT_GROUPS:
                try:
                    await context.bot.send_message(
                        chat_id=group_id,
                        text=f"🧪 **MAIN GROUP TEST**\n\n{test_text}"
                    )
                    logger.info(f"✅ Group {group_id} test successful")
                except Exception as e:
                    logger.error(f"❌ Group {group_id} test failed: {e}")

        except Exception as e:
            logger.error(f"Error in test_announcements: {e}")

# Create global announcement system instance
announcement_system = AnnouncementSystem()

def register_handlers(application: Application):
    """Register announcement system"""
    logger.info("Registering announcement system")
    # Announcement system doesn't need specific handlers
    # It's called from other modules
    logger.info("✅ Announcement system registered successfully")
