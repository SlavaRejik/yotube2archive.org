#!/usr/bin/env python3
# -*- coding: utf-8 -*-

from googleapiclient.discovery import build
import mariadb

import config
from my_lib import *

conn = mariadb.connect(** config.mariadb_connect)

log = create_logger('{}/{}.log'.format(config.log_dir, os.path.basename(__file__)))

youtube = build('youtube', 'v3', developerKey=config.YOUTUBE_API_KEY)

channels_response = youtube.channels().list(
    part='contentDetails',
    id=config.channel_id
).execute()

playlist_id = channels_response['items'][0]['contentDetails']['relatedPlaylists']['uploads']

# Шаг 2: Получить все видео с пагинацией
videos = []
next_page_token = None

while True:
    playlist_response = youtube.playlistItems().list(
        part='snippet',
        playlistId=playlist_id,
        maxResults=50,
        pageToken=next_page_token
    ).execute()

    videos += playlist_response['items']
    next_page_token = playlist_response.get('nextPageToken')

    if not next_page_token:
        break

log.info(f'Found {len(videos)} videos')
new_videos=0
with conn.cursor(dictionary=True) as cursor:
    for video in videos:
        video_id = video['snippet']['resourceId']['videoId']
        cursor.execute("INSERT ignore INTO `upload_files_name`(channel_id,video_id) VALUES (?,?)", (config.channel_id,video_id))
        conn.commit()
        new_videos += cursor.rowcount
    log.info('Insert {} new videos'.format(new_videos))
