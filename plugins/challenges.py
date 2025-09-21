from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes
import logging
import sys
import os
from datetime import datetime, timedelta
import random

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db
from config import CURRENCY

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def challenges_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show daily challenges"""
    await show_daily_challenge(update, context)

async def show_daily_challenge(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Show today's challenges"""
    query = update.callback_query
    user_id = str(query.from_user.id if query else update.effective_user.id)
    
    if query:
        await query.answer()
    
    user = await db.get_user(user_id)
    if not user:
        await (query.edit_message_text if query else update.message.reply_text)("Please start with /start first.")
        return
    
    # Get today's challenges
    today = datetime.utcnow().date()
    daily_challenges = await db.get_daily_challenges(user_id, today)
    
    if not daily_challenges:
        # Create new daily challenges
        daily_challenges = await create_daily_challenges(user_id, today)
    
    challenge_text = f"""
🎯 **TODAY'S CHALLENGES** - {today.strftime('%B %d, %Y')}

"""
    
    total_rewards = 0
    completed_count = 0
    
    for i, challenge in enumerate(daily_challenges, 1):
        status = "✅ Completed" if challenge['completed'] else "⏳ In Progress"
        progress = f"({challenge['progress']}/{challenge['target']})"
        reward = challenge['reward']
        total_rewards += reward if challenge['completed'] else 0
        if challenge['completed']:
            completed_count += 1
        
        challenge_text += f"""
🎮 **Challenge {i}: {challenge['title']}**
📝 {challenge['description']}
📊 Progress: {progress} {status}
🎁 Reward: {reward} {CURRENCY}

"""
    
    # Bonus for completing all challenges
    all_completed = completed_count == len(daily_challenges)
    bonus_reward = 200 if all_completed else 0
    
    challenge_text += f"""
📊 **TODAY'S PROGRESS**
✅ Completed: {completed_count}/{len(daily_challenges)} challenges
💰 Earned Today: {total_rewards} {CURRENCY}
"""
    
    if all_completed:
        challenge_text += f"🎉 **ALL COMPLETED!** Bonus: +{bonus_reward} {CURRENCY}"
    else:
        challenge_text += f"🎁 Complete all for bonus: {bonus_reward} {CURRENCY}"
    
    keyboard = [
        [
            InlineKeyboardButton("🔄 Refresh Progress", callback_data="refresh_challenges"),
            InlineKeyboardButton("🏆 Challenge History", callback_data="challenge_history")
        ],
        [
            InlineKeyboardButton("🎮 Weekly Challenges", callback_data="weekly_challenges")
        ]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    if query:
        await query.edit_message_text(challenge_text, reply_markup=reply_markup)
    else:
        await update.message.reply_text(challenge_text, reply_markup=reply_markup)

async def create_daily_challenges(user_id: str, date) -> list:
    """Create new daily challenges for user"""
    user = await db.get_user(user_id)
    user_level = user.get('user_level', 1) if user else 1
    
    # Challenge templates with dynamic difficulty
    challenge_templates = [
        {
            'title': 'Message Master',
            'description': f'Send {30 + user_level * 10} messages in approved groups',
            'type': 'messages',
            'target': 30 + user_level * 10,
            'reward': 50 + user_level * 10
        },
        {
            'title': 'Earning Streak', 
            'description': f'Earn {10 + user_level * 5} {CURRENCY} today',
            'type': 'earnings',
            'target': 10 + user_level * 5,
            'reward': 30 + user_level * 5
        },
        {
            'title': 'Social Butterfly',
            'description': 'Refer 1 new user to the bot',
            'type': 'referrals',
            'target': 1,
            'reward': 100
        },
        {
            'title': 'Time Warrior',
            'description': 'Be active for 3 hours (send messages every hour)',
            'type': 'activity_time',
            'target': 3,
            'reward': 75
        },
        {
            'title': 'Lucky Spinner',
            'description': 'Send exactly 77 messages (lucky number!)',
            'type': 'exact_messages',
            'target': 77,
            'reward': 150
        }
    ]
    
    # Select 3-4 random challenges
    selected_challenges = random.sample(challenge_templates, min(4, len(challenge_templates)))
    
    daily_challenges = []
    for challenge in selected_challenges:
        daily_challenge = {
            'user_id': user_id,
            'date': date,
            'title': challenge['title'],
            'description': challenge['description'],
            'type': challenge['type'],
            'target': challenge['target'],
            'reward': challenge['reward'],
            'progress': 0,
            'completed': False,
            'created_at': datetime.utcnow()
        }
        daily_challenges.append(daily_challenge)
    
    # Save to database
    await db.save_daily_challenges(user_id, date, daily_challenges)
    
    return daily_challenges

async def handle_challenge_callbacks(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle challenge callback queries"""
    query = update.callback_query
    user_id = str(query.from_user.id)
    data = query.data
    
    await query.answer()
    
    if data == "refresh_challenges":
        await show_daily_challenge(update, context)
    
    elif data == "challenge_history":
        history = await db.get_challenge_history(user_id, limit=10)
        
        history_text = """
🏆 **CHALLENGE HISTORY**

"""
        total_completed = 0
        total_earned = 0
        
        for record in history:
            date = record['date'].strftime('%m/%d')
            completed = record['completed_challenges']
            total_challenges = record['total_challenges'] 
            earned = record['total_rewards']
            
            total_completed += completed
            total_earned += earned
            
            history_text += f"📅 {date}: {completed}/{total_challenges} (+{earned} {CURRENCY})\n"
        
        history_text += f"""

📊 **OVERALL STATS**
✅ Total Completed: {total_completed} challenges
💰 Total Earned: {total_earned} {CURRENCY}
🏆 Success Rate: {(total_completed/len(history)/4*100):.1f}%
        """
        
        await query.edit_message_text(history_text)
    
    elif data == "weekly_challenges":
        weekly_text = """
🎮 **WEEKLY MEGA CHALLENGES**

🏆 **This Week's Special Challenges:**

👑 **Elite Earner** (Week-long)
💰 Earn 1000 {CURRENCY} this week
🎁 Reward: 500 {CURRENCY} bonus + VIP status

📈 **Message Marathon** (Week-long) 
📝 Send 1000 messages this week
🎁 Reward: 300 {CURRENCY} + 2x multiplier for 3 days

👥 **Referral Champion** (Week-long)
🔗 Refer 5 new active users
🎁 Reward: 1000 {CURRENCY} + Premium features

⭐ **Perfect Week**
✅ Complete daily challenges 7 days straight
🎁 Reward: 1500 {CURRENCY} + Special achievement

🔥 Weekly challenges reset every Monday!
        """
        await query.edit_message_text(weekly_text)

def register_handlers(application: Application):
    application.add_handler(CommandHandler("challenges", challenges_command))
    application.add_handler(CommandHandler("daily", show_daily_challenge))
    application.add_handler(CallbackQueryHandler(handle_challenge_callbacks, pattern="^(refresh_challenges|challenge_history|weekly_challenges)$"))
