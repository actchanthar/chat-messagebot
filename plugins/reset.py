from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes
from database.database import db
from config import ADMIN_IDS, LOG_CHANNEL_ID
import logging

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)

async def reset(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = str(update.effective_user.id)
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("You are not authorized to use this command.")
        logger.warning(f"Unauthorized /reset attempt by user {user_id}")
        return

    try:
        args = context.args
        if not args:
            await update.message.reply_text(
                "Usage: /reset all | /reset balance | /reset balance <user_id>"
            )
            logger.info(f"Invalid /reset syntax by user {user_id}: {args}")
            return

        command = args[0].lower()
        if command == "all":
            # Reset everything
            await db.users.update_many(
                {},
                {
                    "$set": {
                        "balance": 0,
                        "messages": 0,
                        "group_messages": {"-1002061898677": 0},
                        "invite_count": 0,
                        "invites": [],
                        "notified_10kyat": False
                    }
                }
            )
            message = "All user data (balances, messages, invites) reset successfully."
            await update.message.reply_text(message)
            await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Admin {user_id} reset all user data.")
            logger.info(f"User {user_id} reset all user data")

        elif command == "balance":
            if len(args) == 1:
                # Reset all balances and messages
                await db.users.update_many(
                    {},
                    {
                        "$set": {
                            "balance": 0,
                            "messages": 0,
                            "group_messages": {"-1002061898677": 0}
                        }
                    }
                )
                message = "All user balances and messages reset to 0."
                await update.message.reply_text(message)
                await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Admin {user_id} reset all user balances and messages.")
                logger.info(f"User {user_id} reset all user balances and messages")
            elif len(args) == 2:
                # Reset specific user's balance and messages
                target_user_id = args[1]
                user = await db.get_user(target_user_id)
                if not user:
                    await update.message.reply_text(f"User {target_user_id} not found.")
                    logger.info(f"User {target_user_id} not found for /reset balance by user {user_id}")
                    return

                await db.update_user(target_user_id, {
                    "balance": 0,
                    "messages": 0,
                    "group_messages": {"-1002061898677": 0}
                })
                message = f"Balance and messages for user {target_user_id} reset to 0."
                await update.message.reply_text(message)
                await context.bot.send_message(chat_id=LOG_CHANNEL_ID, text=f"Admin {user_id} reset balance and messages for user {target_user_id}.")
                logger.info(f"User {user_id} reset balance and messages for user {target_user_id}")
            else:
                await update.message.reply_text("Usage: /reset balance | /reset balance <user_id>")
                logger.info(f"Invalid /reset balance syntax by user {user_id}: {args}")

        else:
            await update.message.reply_text("Invalid option. Use: /reset all | /reset balance | /reset balance <user_id>")
            logger.info(f"Invalid /reset option by user {user_id}: {command}")

    except Exception as e:
        await update.message.reply_text("Error processing /reset. Try again later.")
        logger.error(f"Error in /reset for user {user_id}: {e}")

def register_handlers(application: Application):
    application.add_handler(CommandHandler("reset", reset))