#!/bin/bash

if [[ $EUID -eq 0 ]]; then
  echo "Error: This script must NOT be run as root. Exiting..."
  exit 1
fi

sudo apt update
sudo apt install libmariadb3 libmariadb-dev python3.11-venv build-essential python3.11-dev wget xvfb x11vnc psmisc ffmpeg 

python3 -m venv ~/.venv

if grep -q "~/.venv/bin/activate" ~/.bashrc; then
  echo 
else
  echo "Add activate to profile"
  echo "source ~/.venv/bin/activate" >> ~/.bashrc
fi

source ~/.venv/bin/activate

pip install -r requirements.txt

wget -O /tmp/google-chrome-stable_current_amd64.deb https://dl.google.com/linux/direct/google-chrome-stable_current_amd64.deb
sudo apt install /tmp/google-chrome-stable_current_amd64.deb