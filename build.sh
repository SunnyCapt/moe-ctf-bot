#!/usr/bin/env bash

# in ~/path/to/moe-ctf-bot
apt-get install git tor python3-virtualenv
virtualenv venv --no-site-packages --python=python3
source venv/bin/activate
pip install -r requirements.txt
