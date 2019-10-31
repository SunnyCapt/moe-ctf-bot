#!/usr/bin/env bash

apt-get install git tor python3-virtualenv
git clone https://github.com/SunnyCapt/moe-ctf-bot.git
cd moe-ctf-bot
virtualenv venv --no-site-packages --python=python3
source venv/bin/activate
pip install -r requirements.txt
echo "enter bot token (like `14881488:jejrhrfuuh3493498r3iuh3iur`):\n"
read bot_token
python bot.py ${bot_token}