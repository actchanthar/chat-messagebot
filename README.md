# Telegram Chat Bot

A Telegram bot that rewards users with kyat for sending messages in a specific group, with features for withdrawals, referrals, and leaderboards.

## Features
- Earn 1 kyat for every 3 messages in group -1002061898677
- Withdraw earnings via KBZ Pay, Wave Pay, or Phone Bill
- Referral system: 25 kyat per invite, 50 kyat for invited users who join required channels
- Force-subscription to channels for invite counting
- Weekly rewards for top 3 users by messages or invites
- Admin commands for managing channels, bonuses, and settings
- Random couple matching every 10 minutes
- Balance transfer between users

## Setup
1. Clone the repository.
2. Install dependencies: `pip install -r requirements.txt`
3. Set up MongoDB Atlas and update `MONGODB_URL` in `config.py`.
4. Update `BOT_TOKEN`, `GROUP_CHAT_IDS`, `LOG_CHANNEL_ID`, `REQUIRED_CHANNELS`, and `ADMIN_IDS` in `config.py`.
5. Deploy to Heroku: `heroku create`, `git push heroku main`, `heroku ps:scale worker=1`

## Commands
See the command list below.

## Requirements
- Python 3.10.12
- See `requirements.txt` for dependencies.