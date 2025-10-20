#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mariadb
import csv
from pprint import pprint
import config
from my_lib import *

conn = mariadb.connect(** config.mariadb_connect)

log = create_logger('{}/{}.log'.format(config.log_dir, os.path.basename(__file__)))
logging.getLogger("ia").setLevel(logging.WARNING)

# Get yotube videos
with conn.cursor(dictionary=True) as cursor:
    cursor.execute("SELECT distinct videos.id, videos.oyid, videos.title FROM `playlists` "
                   "LEFT JOIN playlists_members "
                   "on playlists.id = playlists_members.playlist_id "
                   "LEFT JOIN videos "
                   "ON playlists_members.video_id = videos.id "
                   "WHERE playlists.channel_id = ? AND videos.place = ? order by videos.title", (config.channel_id,'yotube'))
    y_videos=cursor.fetchall()

# Get archive videos
a_videos={}
with conn.cursor(dictionary=True) as cursor:
    cursor.execute("SELECT id FROM `videos` WHERE place = 'archive' AND status = 'checked'")
    for row in cursor:
        a_videos[row['id']] = True

# # Make csv
with open('/tmp/video-archive.csv', 'w', newline='', encoding='utf-8') as file:
    fieldnames = ['Yotube', 'Archive', 'Title']
    writer = csv.DictWriter(file,
                            fieldnames=fieldnames,
                            delimiter=';',
                            quotechar='"',
                            quoting=csv.QUOTE_NONNUMERIC,
                            extrasaction='ignore')  # Ignore extra fields
    writer.writeheader()

    for y in y_videos:
        if y['oyid'] in a_videos:
            writer.writerow ({'Yotube': f"https://youtu.be/{y['id']}", 'Archive': f"https://archive.org/details/{y['oyid']}", 'Title': y['title']})
            # print(f"{y['id']}")
        else:
            log.error(f"Youtbe video not found in archive checked video: {y['oyid']}")

# Make html table
with open('/tmp/video-archive.html', 'w', newline='', encoding='utf-8') as file:
    file.write("<table><tr><th>Yotube</th><th>Archive</th><th>Title</th></tr>\n")

    for y in y_videos:
        if y['oyid'] in a_videos:
            file.write (f"<tr><td><a target=\"_blank\" href=\"https://youtu.be/{y['id']}\">{y['id']}</a></td><td><a  target=\"_blank\" href=\"https://archive.org/details/{y['oyid']}\">{y['oyid']}</a></td><td>{y['title']}</td></tr>\n")
        else:
            log.error(f"Youtbe video not found in archive checked video: {y['oyid']}")
    file.write("</table>")

# Make html text
with open('/tmp/video-archive.html', 'w', newline='', encoding='utf-8') as file:
    num = 1
    for y in y_videos:
        if y['oyid'] in a_videos:
            file.write (f"<p>№{num}<br><a target=\"_blank\" href=\"https://youtu.be/{y['id']}\">https://youtu.be/{y['id']}</a><br><a target=\"_blank\" href=\"https://archive.org/details/{y['oyid']}\">https://archive.org/details/{y['oyid']}</a><br>{y['title']}</p>\n")
        else:
            log.error(f"Youtbe video not found in archive checked video: {y['oyid']}")
        num+=1
    file.write("</table>")