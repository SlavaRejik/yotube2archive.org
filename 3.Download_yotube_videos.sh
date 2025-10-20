#!/bin/bash


./3.Download_yotube_videos.py

./_send_to_telegram.py $? 3.Download_yotube_videos.py.log

