from telegram.ext import Application, CommandHandler
import logging
logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s', level=logging.INFO)
logger = logging.getLogger(__name__)
async def start(update, context):
    await update.message.reply_text("Bot is running!")
def main():
    app = Application.builder().token("7784918819:AAHS_tdSRck51UlgW_RQZ1LMSsXrLzqD7Oo").build()
    app.add_handler(CommandHandler("start", start))
    app.run_polling()
if __name__ == "__main__":
    main()