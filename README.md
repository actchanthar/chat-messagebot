# Chat Bot
A Telegram bot for earning money by sending messages and inviting users. Deployed on Heroku.

## Setup
1. Clone the repository: `git clone https://github.com/actchanthar/chat-messagebot.git`
2. Install dependencies: `pip install -r requirements.txt`
3. Set environment variables in Heroku:
   - `BOT_TOKEN`: Your Telegram bot token
   - `MONGODB_URL`: MongoDB connection string
   - `MONGODB_NAME`: MongoDB database name
4. Deploy to Heroku: `git push heroku main`

## Features
- Earn 1 kyat per 3 messages (configurable with `/setmessage`).
- Withdraw earnings via KBZ Pay, Wave Pay, or Phone Bill (requires 15 invites and channel subscription).
- Referral system: 25 kyats per invited user who joins channels, 50 kyats for joiners.
- Force subscription to channels (e.g., `@tiktokcelemyanmar`) for bot usage.
- Weekly rewards for top 3 inviters.

## Commands
- `/start` - Welcome message, referral link, force-sub channel, and buttons.
- `/withdraw` - Initiate withdrawal (private chat only).
- `/balance` - Show current balance and invite status.
- `/top` - Show top 10 users by invites and messages.
- `/help` - List commands.
- `/rest` - Reset message counts (admin-only).
- `/addgroup` - Add group for message counting (admin-only).
- `/checkgroup` - Check group message counts (admin-only).
- `/SetPhoneBill` - Set Phone Bill reward text (admin-only).
- `/broadcast` - Send message to all users (admin-only).
- `/users` - Show total user count or list users (admin-only).
- `/setinvite` - Set invite requirement (admin-only).
- `/checksubscription` - Verify channel membership, award kyats.
- `/couple` - Pair two users randomly (10-min cooldown).
- `/transfer` - Transfer balance to another user.
- `/setmessage` - Set messages per kyat (admin-only).
- `/addchnl` - Add a channel to force subscription list (admin-only).

## Deployment Notes
- Ensure MongoDB is accessible.
- Check logs: `heroku logs --tail`
- Verify bot permissions in groups/channels.
- Use `/addchnl` to manage required channels.
- Run `db.fix_users()` after deployment to migrate user data.