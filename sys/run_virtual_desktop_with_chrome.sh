#!/bin/bash

killall Xvfb
/usr/bin/Xvfb :100 -screen 0 1920x1024x24 -nolisten tcp > /tmp/xvfb.log 2>/tmp/xvfb.err &
export DISPLAY=:100

sleep 3

/opt/google/chrome/chrome --proxy-server="socks5://127.0.0.1:8888" https://www.youtube.com/ &

killall x11vnc
rm -f ~/vnc.log ~/vnc.err

echo Run x11vnc
/usr/bin/x11vnc -loop -noxfixes -noxdamage  -usepw -forever -rfbport 5910 -display :100

