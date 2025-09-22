from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
import logging
import sys
import os
from collections import defaultdict
import time

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import ADMIN_IDS, CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def ban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to ban a user - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            f"❌ **အသုံးပြုပုံ:** `/ban <user_id> [အကြောင်းရင်း]`\n\n"
            f"**ဥပမာ:** `/ban 123456789 Spamming`"
        )
        return
    
    try:
        target_user_id = context.args[0]
        reason = " ".join(context.args[1:]) if len(context.args) > 1 else "Admin မှ ပိတ်ပင်ခြင်း"
        
        # Ban user in database
        success = await db.ban_user(target_user_id, reason)
        
        if success:
            # Try to get user info
            try:
                user_info = await context.bot.get_chat(target_user_id)
                user_name = user_info.first_name or "သုံးစွဲသူ"
            except:
                user_name = "သုံးစွဲသူ"
            
            await update.message.reply_text(
                f"✅ **သုံးစွဲသူကို ပိတ်ပင်ပြီးပါပြီ**\n\n"
                f"👤 **သုံးစွဲသူ:** {user_name} ({target_user_id})\n"
                f"📝 **အကြောင်းရင်း:** {reason}\n"
                f"👨‍💼 **ပိတ်ပင်သူ:** Admin {user_id}"
            )
            
            logger.info(f"Admin {user_id} banned user {target_user_id}: {reason}")
        else:
            await update.message.reply_text("❌ သုံးစွဲသူကို ပိတ်ပင်၍မရပါ။ သုံးစွဲသူ မတွေ့ပါ။")
    
    except Exception as e:
        logger.error(f"Error in ban command: {e}")
        await update.message.reply_text("❌ Error occurred while banning user.")

async def unban_user_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Admin command to unban a user - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            f"❌ **အသုံးပြုပုံ:** `/unban <user_id>`\n\n"
            f"**ဥပမာ:** `/unban 123456789`"
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
                user_name = user_info.first_name or "သုံးစွဲသူ"
            except:
                user_name = "သုံးစွဲသူ"
            
            await update.message.reply_text(
                f"✅ **သုံးစွဲသူကို ပြန်လည်ခွင့်ပြုပြီးပါပြီ**\n\n"
                f"👤 **သုံးစွဲသူ:** {user_name} ({target_user_id})\n"
                f"👨‍💼 **ပြန်လည်ခွင့်ပြုသူ:** Admin {user_id}"
            )
            
            logger.info(f"Admin {user_id} unbanned user {target_user_id}")
        else:
            await update.message.reply_text("❌ သုံးစွဲသူကို ပြန်လည်ခွင့်ပြု၍မရပါ။")
    
    except Exception as e:
        logger.error(f"Error in unban command: {e}")
        await update.message.reply_text("❌ Error occurred while unbanning user.")

async def reset_spam_warnings(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Reset spam warnings for a user - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) != 1:
        await update.message.reply_text(
            f"❌ **အသုံးပြုပုံ:** `/resetspam <user_id>`\n\n"
            f"**ဥပမာ:** `/resetspam 123456789`"
        )
        return
    
    try:
        target_user = context.args[0]
        
        # Import spam tracking from message_handler
        from plugins.message_handler import user_warnings, user_last_message
        
        # Reset warnings and cooldowns
        old_warnings = user_warnings.get(target_user, 0)
        user_warnings[target_user] = 0
        
        if target_user in user_last_message:
            del user_last_message[target_user]
        
        # Try to get user name
        try:
            user_info = await context.bot.get_chat(target_user)
            user_name = user_info.first_name or "သုံးစွဲသူ"
        except:
            user_name = "သုံးစွဲသူ"
        
        await update.message.reply_text(
            f"✅ **Warning များ ရှင်းလင်းပြီးပါပြီ**\n\n"
            f"👤 **သုံးစွဲသူ:** {user_name} ({target_user})\n"
            f"📊 **ယခင် Warnings:** {old_warnings}\n"
            f"🔄 **လက်ရှိ:** 0 warnings\n"
            f"⏰ **Cooldown:** ဖယ်ရှားပြီး\n"
            f"👨‍💼 **ရှင်းလင်းသူ:** Admin {user_id}"
        )
        
        logger.info(f"Admin {user_id} reset spam warnings for user {target_user} (was {old_warnings} warnings)")
        
    except Exception as e:
        logger.error(f"Error in reset spam: {e}")
        await update.message.reply_text("❌ Error occurred while resetting spam data.")

async def ban_spammer(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Quick ban for spammers - reply to their message - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    # Check if replying to a message
    if not update.message.reply_to_message:
        await update.message.reply_text(
            f"❌ **အသုံးပြုပုံ:** စပမ်စာကို Reply လုပ်ပြီး `/banspam` ရိုက်ပါ\n\n"
            f"စပမ်လုပ်သူကို ချက်ချင်း ပိတ်ပင်မည်။"
        )
        return
    
    try:
        spammer_id = str(update.message.reply_to_message.from_user.id)
        spammer_name = update.message.reply_to_message.from_user.first_name or "သုံးစွဲသူ"
        spam_text = update.message.reply_to_message.text[:50] if update.message.reply_to_message.text else "စာမရှိ"
        
        # Ban in database
        await db.ban_user(spammer_id, "Admin မှ စပမ်အတွက် ချက်ချင်းပိတ်ပင်ခြင်း")
        
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
            f"🚫 **စပမ်လုပ်သူကို ပိတ်ပင်ပြီးပါပြီ!**\n\n"
            f"👤 **သုံးစွဲသူ:** {spammer_name} ({spammer_id})\n"
            f"💬 **စပမ်စာ:** {spam_text}...\n"
            f"👨‍💼 **ပိတ်ပင်သူ:** Admin {user_id}"
        )
        
        logger.info(f"Admin {user_id} banned spammer {spammer_id}: {spam_text}")
    
    except Exception as e:
        logger.error(f"Error in ban spammer: {e}")
        await update.message.reply_text("❌ Error occurred while banning spammer.")

async def view_spam_stats(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """View spam statistics - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    try:
        from plugins.message_handler import user_warnings, user_last_message
        
        # Count users with warnings
        total_warned_users = sum(1 for w in user_warnings.values() if w > 0)
        active_users = len([t for t in user_last_message.values() if time.time() - t < 300])
        users_in_cooldown = sum(1 for uid, warnings in user_warnings.items() 
                               if warnings >= 5 and uid in user_last_message 
                               and time.time() - user_last_message[uid] < 300)
        
        # Get users with most warnings
        top_warned = sorted(user_warnings.items(), key=lambda x: x[1], reverse=True)[:5]
        
        stats_text = (
            f"📊 **စပမ်ထိန်းချုပ်မှု စာရင်းအင်း**\n\n"
            f"⚠️ **Warning ရှိသော သုံးစွဲသူများ:** {total_warned_users}\n"
            f"💬 **လက်ရှི တက်ကြွသူများ:** {active_users}\n"
            f"🔕 **Cooldown ခံနေသူများ:** {users_in_cooldown}\n\n"
        )
        
        if top_warned and any(w[1] > 0 for w in top_warned):
            stats_text += "🥇 **Warning အများဆုံးရသူများ:**\n"
            count = 0
            for uid, warnings in top_warned:
                if warnings > 0 and count < 5:
                    try:
                        user_info = await context.bot.get_chat(uid)
                        name = user_info.first_name or "အမည်မသိ"
                    except:
                        name = "အမည်မသိ"
                    
                    cooldown_status = ""
                    if warnings >= 5 and uid in user_last_message:
                        if time.time() - user_last_message[uid] < 300:
                            cooldown_status = " (🔕)"
                    
                    stats_text += f"{count+1}. {name} - {warnings} warnings{cooldown_status}\n"
                    count += 1
            
            if count == 0:
                stats_text += "ယခုအချိန်တွင် Warning ရှိသူမရှိပါ။\n"
        else:
            stats_text += "🎉 **ယခုအချိန်တွင် Warning ရှိသူမရှိပါ!**\n"
        
        stats_text += f"\n🔧 **Admin Commands:**\n"
        stats_text += f"• `/banspam` - စပမ်စာကို Reply လုပ်ပြီး ပိတ်ပင်ရန်\n"
        stats_text += f"• `/resetspam <user_id>` - Warning များ ရှင်းလင်းရန်\n"
        stats_text += f"• `/spamstats` - စာရင်းအင်းများ ကြည့်ရန်\n"
        stats_text += f"• `/ban <user_id>` - သုံးစွဲသူကို ပိတ်ပင်ရန်\n"
        stats_text += f"• `/unban <user_id>` - သုံးစွဲသူကို ပြန်လည်ခွင့်ပြုရန်"
        
        await update.message.reply_text(stats_text)
    
    except Exception as e:
        logger.error(f"Error in spam stats: {e}")
        await update.message.reply_text("❌ စာရင်းအင်းများ ရယူ၍မရပါ။")

async def broadcast_message(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Broadcast message to all users - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    if len(context.args) < 1:
        await update.message.reply_text(
            f"❌ **အသုံးပြုပုံ:** `/broadcast <မက်ဆေ့ချ်>`\n\n"
            f"**ဥပမာ:** `/broadcast သုံးစွဲသူအားလုံးအတွက် အရေးကြီးသောအချက်အလက်!`"
        )
        return
    
    try:
        message = " ".join(context.args)
        
        # Get all users
        users = await db.get_all_users()
        
        sent_count = 0
        failed_count = 0
        
        await update.message.reply_text(f"📡 **{len(users)} သုံးစွဲသူများထံ ပို့နေပါသည်...**")
        
        for user in users:
            try:
                await context.bot.send_message(
                    chat_id=user["user_id"],
                    text=f"📢 **ကြေငြာချက်**\n\n{message}\n\n- Admin Team"
                )
                sent_count += 1
            except:
                failed_count += 1
        
        await update.message.reply_text(
            f"✅ **Broadcast ပြီးစီးပါပြီ**\n\n"
            f"📤 **ပို့အောင်မြင်:** {sent_count} သုံးစွဲသူ\n"
            f"❌ **ပို့မရ:** {failed_count} သုံးစွဲသူ\n"
            f"👨‍💼 **ပို့သူ:** Admin {user_id}"
        )
        
        logger.info(f"Admin {user_id} broadcasted to {sent_count} users")
    
    except Exception as e:
        logger.error(f"Error in broadcast: {e}")
        await update.message.reply_text("❌ Broadcast ပို့၍မရပါ။")

async def system_status(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Check system status - Myanmar language"""
    user_id = str(update.effective_user.id)
    
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("❌ ဤကွန်မန်းသည် Admin များအတွက်သာဖြစ်သည်။")
        return
    
    try:
        # Get system stats
        total_users = await db.get_total_users_count()
        total_earnings = await db.get_total_earnings()
        total_withdrawals = await db.get_total_withdrawals()
        
        # Get spam stats
        from plugins.message_handler import user_warnings
        warned_users = sum(1 for w in user_warnings.values() if w > 0)
        
        status_text = (
            f"🤖 **စနစ်အခြေအနေ**\n\n"
            f"👥 **စုစုပေါင်းသုံးစွဲသူ:** {total_users:,}\n"
            f"💰 **စုစုပေါင်းရရှိငွေ:** {int(total_earnings):,} {CURRENCY}\n"
            f"💸 **စုစုပေါင်းထုတ်ယူငွေ:** {int(total_withdrawals):,} {CURRENCY}\n"
            f"💳 **စနစ်ရှိငွေ:** {int(total_earnings - total_withdrawals):,} {CURRENCY}\n\n"
            f"⚠️ **Warning ရှိသူများ:** {warned_users}\n"
            f"🛡️ **Anti-spam:** အလုပ်လုပ်နေသည်\n"
            f"📊 **Database:** ချိတ်ဆက်ထားသည်\n\n"
            f"✅ **စနစ်အားလုံး ကောင်းမွန်စွာအလုပ်လုပ်နေပါသည်**"
        )
        
        await update.message.reply_text(status_text)
        
    except Exception as e:
        logger.error(f"Error in system status: {e}")
        await update.message.reply_text("❌ စနစ်အခြေအနေ စစ်ဆေး၍မရပါ။")

def register_handlers(application: Application):
    """Register admin command handlers - Myanmar language support"""
    logger.info("Registering admin handlers with Myanmar language support")
    
    # User management commands
    application.add_handler(CommandHandler("ban", ban_user_command))
    application.add_handler(CommandHandler("unban", unban_user_command))
    
    # Anti-spam commands
    application.add_handler(CommandHandler("resetspam", reset_spam_warnings))
    application.add_handler(CommandHandler("banspam", ban_spammer))
    application.add_handler(CommandHandler("spamstats", view_spam_stats))
    
    # System commands
    application.add_handler(CommandHandler("broadcast", broadcast_message))
    application.add_handler(CommandHandler("systemstatus", system_status))
    
    logger.info("✅ Admin handlers with Myanmar language registered successfully")
