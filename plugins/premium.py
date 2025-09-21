from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY, ADMIN_IDS

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def premium_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show premium information"""
    await show_premium_info(update, context)

async def show_premium_info(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Display premium features and benefits"""
    query = update.callback_query
    user_id = str(query.from_user.id if query else update.effective_user.id)
    
    if query:
        await query.answer()
    
    user = await db.get_user(user_id)
    if not user:
        await (query.edit_message_text if query else update.message.reply_text)("Please start with /start first.")
        return
    
    is_premium = user.get('is_premium', False)
    premium_expires = user.get('premium_expires')
    
    if is_premium and premium_expires and premium_expires > datetime.utcnow():
        # User has active premium
        days_left = (premium_expires - datetime.utcnow()).days
        
        premium_text = f"""
👑 **YOU ARE PREMIUM!** 👑

⭐ **Status:** Active Premium Member
📅 **Expires:** {premium_expires.strftime('%B %d, %Y')} ({days_left} days left)

🎁 **YOUR PREMIUM BENEFITS:**
• 🚀 **2x Earning Multiplier** (6 messages = 2 kyat)
• ⚡ **Instant Withdrawals** (No 24h wait)
• 🎯 **Exclusive Daily Challenges** (+500 kyat daily)
• 🏆 **VIP Leaderboard** (Separate premium rankings)
• 💎 **Premium Support** (Priority help)
• 🎁 **Weekly Bonus** (200 kyat every Monday)
• 🚫 **No Rate Limits** (Unlimited messaging)
• 🎪 **Exclusive Competitions** (Premium-only contests)

💰 **Premium Earnings Today:** +{user.get('premium_earnings_today', 0)} {CURRENCY}
        """
        
        keyboard = [
            [
                InlineKeyboardButton("🔄 Extend Premium", callback_data="extend_premium"),
                InlineKeyboardButton("📊 Premium Stats", callback_data="premium_stats")
            ],
            [
                InlineKeyboardButton("🎁 Claim Daily Bonus", callback_data="claim_premium_daily")
            ]
        ]
        
    else:
        # User doesn't have premium
        premium_text = f"""
👑 **BECOME PREMIUM MEMBER!** 👑

🚀 **UNLOCK INCREDIBLE BENEFITS:**

💰 **EARNING BOOSTS:**
• 🔥 **2x Earning Multiplier** (Double your income!)
• ⚡ **Instant Withdrawals** (Skip the 24h wait)
• 💎 **Daily Premium Bonus** (500 {CURRENCY} daily)
• 🎁 **Weekly Mega Bonus** (2000 {CURRENCY} weekly)

🎮 **EXCLUSIVE FEATURES:**
• 🏆 **VIP-Only Competitions** (Massive prizes!)
• 🎯 **Premium Challenges** (High-reward tasks)
• 👑 **VIP Leaderboard** (Premium member rankings)
• 🚫 **Remove All Limits** (No rate limiting)

💎 **PREMIUM SUPPORT:**
• 🎪 **Priority Customer Support**
• 🔮 **Early Access** to new features
• 🎨 **Custom Profile Badge**
• 🌟 **Premium Member Status**

💳 **PREMIUM PRICING:**
• 📅 **7 Days:** 1000 {CURRENCY}
• 📅 **30 Days:** 3500 {CURRENCY} (Save 500!)
• 📅 **90 Days:** 9000 {CURRENCY} (Save 1500!)

🎉 **ROI:** Premium pays for itself in just 3 days!
        """
        
        keyboard = [
            [
                InlineKeyboardButton("💎 Buy 7 Days (1000)", callback_data="buy_premium_7"),
                InlineKeyboardButton("🔥 Buy 30 Days (3500)", callback_data="buy_premium_30")
            ],
            [
                InlineKeyboardButton("👑 Buy 90 Days (9000)", callback_data="buy_premium_90")
            ],
            [
                InlineKeyboardButton("🎁 Free Premium Trial", callback_data="free_trial")
            ]
        ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(premium_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(premium_text, reply_markup=reply_markup)

async def handle_premium_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle premium callback queries"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    
    user = await db.get_user(user_id)
    if not user:
        await query.edit_message_text("Please start with /start first.")
        return
    
    current_balance = user.get('balance', 0)
    
    if data.startswith("buy_premium_"):
        days = int(data.split("_")[-1])
        prices = {7: 1000, 30: 3500, 90: 9000}
        price = prices[days]
        
        if current_balance < price:
            await query.edit_message_text(
                f"❌ **Insufficient Balance!**\n\n"
                f"💰 Your Balance: {int(current_balance)} {CURRENCY}\n"
                f"💎 Premium Cost: {price} {CURRENCY}\n"
                f"💸 Need: {price - int(current_balance)} more {CURRENCY}\n\n"
                f"🎯 Keep earning messages to unlock Premium!"
            )
            return
        
        # Process premium purchase
        new_balance = current_balance - price
        premium_expires = datetime.utcnow() + timedelta(days=days)
        
        await db.update_user(user_id, {
            'balance': new_balance,
            'is_premium': True,
            'premium_expires': premium_expires,
            'premium_purchased_at': datetime.utcnow()
        })
        
        success_text = f"""
🎉 **PREMIUM ACTIVATED!** 🎉

👑 **Welcome to Premium Membership!**

📅 **Duration:** {days} days
💰 **Cost:** {price} {CURRENCY}
💳 **New Balance:** {int(new_balance)} {CURRENCY}
⏰ **Expires:** {premium_expires.strftime('%B %d, %Y')}

🚀 **Your Premium Benefits Are Now Active:**
• 2x earning multiplier activated!
• Instant withdrawals enabled!
• Premium challenges unlocked!
• VIP support access granted!

💎 Start earning double rewards immediately!
        """
        
        await query.edit_message_text(success_text)
        
        # Notify admins of premium purchase
        try:
            await context.bot.send_message(
                chat_id=ADMIN_IDS[0],
                text=f"💎 Premium Purchase: User {user_id} bought {days} days premium for {price} {CURRENCY}"
            )
        except:
            pass
    
    elif data == "free_trial":
        # Check if user already used free trial
        if user.get('used_free_trial', False):
            await query.edit_message_text(
                "❌ **Free Trial Already Used!**\n\n"
                "You can only use the free trial once per account.\n"
                "Purchase premium to continue enjoying VIP benefits!"
            )
            return
        
        # Give 3-day free trial
        premium_expires = datetime.utcnow() + timedelta(days=3)
        await db.update_user(user_id, {
            'is_premium': True,
            'premium_expires': premium_expires,
            'used_free_trial': True
        })
        
        trial_text = f"""
🎁 **FREE TRIAL ACTIVATED!** 🎁

👑 **3-Day Premium Trial Started!**

⏰ **Expires:** {premium_expires.strftime('%B %d, %Y')}

🚀 **Trial Benefits:**
• 2x earning multiplier
• Premium daily challenges
• VIP support access
• Instant withdrawals

💎 **After trial, upgrade to keep benefits!**
        """
        
        await query.edit_message_text(trial_text)
    
    elif data == "claim_premium_daily":
        # Check if already claimed today
        last_claim = user.get('last_premium_daily_claim')
        today = datetime.utcnow().date()
        
        if last_claim and last_claim.date() == today:
            await query.edit_message_text(
                "✅ **Daily Bonus Already Claimed!**\n\n"
                "You've already claimed your premium daily bonus today.\n"
                "Come back tomorrow for another 500 {CURRENCY} bonus!"
            )
            return
        
        # Give daily premium bonus
        bonus = 500
        new_balance = user.get('balance', 0) + bonus
        
        await db.update_user(user_id, {
            'balance': new_balance,
            'last_premium_daily_claim': datetime.utcnow(),
            'premium_earnings_today': user.get('premium_earnings_today', 0) + bonus
        })
        
        await query.edit_message_text(
            f"🎁 **Premium Daily Bonus Claimed!**\n\n"
            f"💰 Bonus: +{bonus} {CURRENCY}\n"
            f"💳 New Balance: {int(new_balance)} {CURRENCY}\n\n"
            f"👑 Thanks for being a premium member!"
        )

def register_handlers(application: Application):
    application.add_handler(CommandHandler("premium", premium_command))
    application.add_handler(CallbackQueryHandler(handle_premium_callbacks, pattern="^(buy_premium_|free_trial|claim_premium_daily|extend_premium|premium_stats)"))
