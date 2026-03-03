#!/usr/bin/env python
# -*- coding: utf-8 -*-


import mariadb
from my_lib import *
from pprint import pprint

conn = mariadb.connect(** config.mariadb_connect)
videos = {}
doubles = {}

# Get all video list
with conn.cursor(dictionary=True) as cursor:
    cursor.execute("SELECT m.`video_id`,m.playlist_id,p.channel_id, p.title FROM `playlists_members` m "
                   "LEFT JOIN playlists p ON m.playlist_id = p.id")
    for row in cursor:
        line={'channel_id': row['channel_id'], 'playlist_id': row['playlist_id'], 'playlist_title': row['title']}
        if row['video_id'] not in videos:
            videos[row['video_id']]=[line]
        else:
            videos[row['video_id']].append(line)

for k,v in videos.items():
    if len(v)>1:
        # print(k,v,'\n')
        old = ''
        for i in v:
            if old=='':
                old=i['channel_id']
                continue
            if old!=i['channel_id']:
                doubles[k]=v
                break

pprint(doubles)
print(len(doubles))