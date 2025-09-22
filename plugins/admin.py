from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import sys
import os
from collections import defaultdict

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import ADMIN_IDS, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to ban a user"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ **Usage:** `/ban <user_id> [reason]`\n\n"
            "**Example:** `/ban 123456789 Spamming`"
        )
        return
    
    try:
        target_user_id = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Banned by admin"
        
        # Ban user in database
        success = await db.ban_user(target_user_id, reason)
        
        if success:
            # Try to get user info
            try:
                user_info = await context.bot.get_chat(target_user_id)
                user_name = user_info.first_name or "User"
            except:
                user_name = "User"
            
            await update.message.reply_text(
                f"✅ **User Banned**\n\n"
                f"👤 **User:** {user_name} ({target_user_id})\n"
                f"📝 **Reason:** {reason}\n"
                f"👨‍💼 **Banned by:** Admin {user_id}"
            )
            
            logger.info(f"Admin {user_id} banned user {target_user_id}: {reason}")
        else:
            await update.message.reply_text("❌ Failed to ban user. User may not exist.")
    
    except Exception as e:
        logger.error(f"Error in ban command: {e}")
        await update.message.reply_text("❌ Error occurred while banning user.")

async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to unban a user"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            "❌ **Usage:** `/unban <user_id>`\n\n"
            "**Example:** `/unban 123456789`"
        )
        return
    
    try:
        target_user_id = context.args[0]
        
        # Unban user in database
        success = await db.unban_user(target_user_id)
        
        if success:
            # Try to get user info
            try:
                user_info = await context.bot.get_chat(target_user_id)
                user_name = user_info.first_name or "User"
            except:
                user_name = "User"
            
            await update.message.reply_text(
                f"✅ **User Unbanned**\n\n"
                f"👤 **User:** {user_name} ({target_user_id})\n"
                f"👨‍💼 **Unbanned by:** Admin {user_id}"
            )
            
            logger.info(f"Admin {user_id} unbanned user {target_user_id}")
        else:
            await update.message.reply_text("❌ Failed to unban user. User may not exist.")
    
    except Exception as e:
        logger.error(f"Error in unban command: {e}")
        await update.message.reply_text("❌ Error occurred while unbanning user.")

async def reset_spam_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset spam warnings for a user"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            "❌ **Usage:** `/resetspam <user_id>`\n\n"
            "**Example:** `/resetspam 123456789`"
        )
        return
    
    try:
        target_user = context.args[0]
        
        # Import spam tracking from message_handler
        from plugins.message_handler import user_warnings, user_cooldowns
        
        # Reset warnings and cooldowns
        if target_user in user_warnings:
            old_warnings = user_warnings[target_user]
            user_warnings[target_user] = 0
        else:
            old_warnings = 0
        
        if target_user in user_cooldowns:
            del user_cooldowns[target_user]
        
        await update.message.reply_text(
            f"✅ **Spam Data Reset**\n\n"
            f"👤 **User ID:** {target_user}\n"
            f"📊 **Previous Warnings:** {old_warnings}\n"
            f"🔄 **Cooldown Removed:** Yes\n"
            f"👨‍💼 **Reset by:** Admin {user_id}"
        )
        
        logger.info(f"Admin {user_id} reset spam warnings for user {target_user}")
    
    except Exception as e:
        logger.error(f"Error in reset spam: {e}")
        await update.message.reply_text("❌ Error occurred while resetting spam data.")

async def ban_spammer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick ban for spammers - reply to their message"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    # Check if replying to a message
    if not update.message.reply_to_message:
        await update.message.reply_text(
            "❌ **Usage:** Reply to a spam message with `/banspam`\n\n"
            "This will immediately ban the user who sent that message."
        )
        return
    
    try:
        spammer_id = str(update.message.reply_to_message.from_user.id)
        spammer_name = update.message.reply_to_message.from_user.first_name or "User"
        spam_text = update.message.reply_to_message.text[:50] if update.message.reply_to_message.text else "No text"
        
        # Ban in database
        await db.ban_user(spammer_id, "Manual admin ban for spam")
        
        # Try to ban from group
        try:
            await context.bot.ban_chat_member(
                chat_id=update.effective_chat.id,
                user_id=int(spammer_id)
            )
        except Exception as e:
            logger.error(f"Failed to ban from group: {e}")
        
        # Delete the spam message
        try:
            await context.bot.delete_message(
                chat_id=update.effective_chat.id,
                message_id=update.message.reply_to_message.message_id
            )
        except:
            pass
        
        await update.message.reply_text(
            f"🚫 **Spammer Banned!**\n\n"
            f"👤 **User:** {spammer_name} ({spammer_id})\n"
            f"💬 **Message:** {spam_text}...\n"
            f"👨‍💼 **Banned by:** Admin {user_id}"
        )
        
        logger.info(f"Admin {user_id} banned spammer {spammer_id}: {spam_text}")
    
    except Exception as e:
        logger.error(f"Error in ban spammer: {e}")
        await update.message.reply_text("❌ Error occurred while banning spammer.")

async def view_spam_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View spam statistics"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    try:
        from plugins.message_handler import user_warnings, user_cooldowns
        import time
        
        # Count active warnings and cooldowns
        total_warnings = len(user_warnings)
        total_warned_users = sum(1 for w in user_warnings.values() if w > 0)
        active_cooldowns = sum(1 for t in user_cooldowns.values() if time.time() < t)
        
        # Get top offenders
        top_offenders = sorted(user_warnings.items(), key=lambda x: x[1], reverse=True)[:5]
        
        stats_text = (
            f"📊 **SPAM STATISTICS**\n\n"
            f"⚠️ **Total Users with Warnings:** {total_warned_users}\n"
            f"🔇 **Users in Cooldown:** {active_cooldowns}\n"
            f"📈 **Total Warning Records:** {total_warnings}\n\n"
        )
        
        if top_offenders:
            stats_text += "🥇 **Top Offenders:**\n"
            for i, (uid, warnings) in enumerate(top_offenders[:3], 1):
                if warnings > 0:
                    try:
                        user_info = await context.bot.get_chat(uid)
                        name = user_info.first_name or "Unknown"
                    except:
                        name = "Unknown"
                    stats_text += f"{i}. {name} ({uid}) - {warnings} warnings\n"
        
        stats_text += f"\n🔧 **Anti-Spam Commands:**\n"
        stats_text += f"• `/banspam` - Ban user (reply to message)\n"
        stats_text += f"• `/resetspam <user_id>` - Reset warnings\n"
        stats_text += f"• `/spamstats` - View these statistics"
        
        await update.message.reply_text(stats_text)
    
    except Exception as e:
        logger.error(f"Error in spam stats: {e}")
        await update.message.reply_text("❌ Error occurred while getting spam statistics.")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast message to all users"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ This command is for administrators only.")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            "❌ **Usage:** `/broadcast <message>`\n\n"
            "**Example:** `/broadcast Important update for all users!`"
        )
        return
    
    try:
        message = " ".join(context.args)
        
        # Get all users
        users = await db.get_all_users()
        
        sent_count = 0
        failed_count = 0
        
        await update.message.reply_text(f"📡 **Broadcasting to {len(users)} users...**")
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user["user_id"],
                    text=f"📢 **ANNOUNCEMENT**\n\n{message}"
                )
                sent_count += 1
            except:
                failed_count += 1
        
        await update.message.reply_text(
            f"✅ **Broadcast Complete**\n\n"
            f"📤 **Sent:** {sent_count} users\n"
            f"❌ **Failed:** {failed_count} users\n"
            f"👨‍💼 **Broadcast by:** Admin {user_id}"
        )
        
        logger.info(f"Admin {user_id} broadcasted to {sent_count} users")
    
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await update.message.reply_text("❌ Error occurred while broadcasting.")

def register_handlers(application: Application):
    """Register admin command handlers"""
    logger.info("Registering admin handlers")
    
    # User management commands
    application.add_handler(CommandHandler("ban", ban_user_command))
    application.add_handler(CommandHandler("unban", unban_user_command))
    
    # Anti-spam commands
    application.add_handler(CommandHandler("resetspam", reset_spam_warnings))
    application.add_handler(CommandHandler("banspam", ban_spammer))
    application.add_handler(CommandHandler("spamstats", view_spam_stats))
    
    # Broadcast command
    application.add_handler(CommandHandler("broadcast", broadcast_message))
    
    logger.info("✅ Admin handlers registered successfully")
