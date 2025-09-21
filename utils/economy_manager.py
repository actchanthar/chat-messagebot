import logging
import sys
import os
from datetime import datetime, timedelta

# Add project root to path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

from database.database import db

logger = logging.getLogger(__name__)

class EconomyManager:
    async def process_daily_login(self, user_id: str):
        try:
            user = await db.get_user(user_id)
            if not user:
                return 0
            
            last_login = user.get("last_daily_login")
            today = datetime.utcnow().date()
            
            if not last_login or last_login.date() < today:
                # Give daily login bonus
                bonus = 10
                current_balance = user.get("balance", 0)
                await db.update_user(user_id, {
                    "balance": current_balance + bonus,
                    "last_daily_login": datetime.utcnow()
                })
                return bonus
            return 0
        except Exception as e:
            logger.error(f"Economy manager error: {e}")
            return 0

economy_manager = EconomyManager()
