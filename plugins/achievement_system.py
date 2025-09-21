import logging
import sys
import os

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db

logger = logging.getLogger(__name__)

class AchievementSystem:
    def __init__(self):
        self.achievements = {
            "first_start": {"name": "Welcome!", "reward": 50, "description": "Started the bot"},
            "first_message": {"name": "First Steps", "reward": 10, "description": "Sent first message"},
            "hundred_messages": {"name": "Chatter", "reward": 100, "description": "Sent 100 messages"},
            "first_referral": {"name": "Recruiter", "reward": 50, "description": "Referred first friend"}
        }
    
    async def check_achievements(self, user_id: str, achievement_type: str):
        try:
            if achievement_type in self.achievements:
                user = await db.get_user(user_id)
                if user and achievement_type not in user.get("achievements", []):
                    # Award achievement
                    reward = self.achievements[achievement_type]["reward"]
                    await db.add_bonus(user_id, reward)
                    
                    achievements = user.get("achievements", [])
                    achievements.append(achievement_type)
                    await db.update_user(user_id, {"achievements": achievements})
                    
                    return True
            return False
        except Exception as e:
            logger.error(f"Achievement system error: {e}")
            return False

achievement_system = AchievementSystem()
