# ACT Chat Bot
A Telegram bot for earning money by sending messages, inviting users, and managing withdrawals.

## Features
- Earn 1 kyat for every 3 messages in the target group (-1002061898677).
- Referral system: 25 kyat per successful invite, 50 kyat for invited users who join channels.
- Withdrawals via KBZ Pay, Wave Pay, or Phone Bill (1000 kyat minimum for Phone Bill).
- Forced subscription to channels for withdrawals.
- Weekly rewards for top 3 users by messages and invites.
- Admin commands for managing groups, channels, and bonuses.

## Commands
- `/start` - Welcome message with referral link and top users.
- `/balance` - Check current balance.
- `/withdraw` - Request withdrawal (requires joining channels and meeting invite threshold).
- `/top` - Show top 10 users by messages and invites.
- `/help` - List available commands.
- `/rest` - Reset message counts (admin-only).
- `/addgroup <group_id>` - Add group for message counting (admin-only).
- `/checkgroup <group_id>` - Check group message count (admin-only).
- `/SetPhoneBill <reward_text>` - Set Phone Bill reward text (admin-only).
- `/broadcast <message>` - Send message to all users (admin-only).
- `/pbroadcast <message>` - Send pinned message to all users (admin-only).
- `/users` - Show total user count (admin-only).
- `/addchnl <channel_id> <name>` - Add channel for forced subscription (admin-only).
- `/delchnl <channel_id>` - Remove channel (admin-only).
- `/listchnl` - List all forced subscription channels (admin-only).
- `/checksubscription` - Check user's subscription status.
- `/setinvite <number>` - Set invite threshold for withdrawals (admin-only).
- `/Add_bonus <user_id> <amount>` - Add bonus to user (admin-only).
- `/setmessage <number>` - Set messages per kyat (admin-only).
- `/debug_message_count` - Debug message counts (admin-only).
- `/referral_users` - Show referral stats and link.
- `/couple` - Randomly match two users (10-minute cooldown).
- `/transfer <user_id> <amount>` - Transfer balance to another user.
- `/restwithdraw <user_id|ALL>` - Reset withdrawal records (admin-only).
- `/clone <mongodb_url>` - Clone database to new MongoDB URL (admin-only).
- `/on` - Enable message counting