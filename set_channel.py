#!/usr/bin/env python
# -*- coding: utf-8 -*-

from tqdm import tqdm
import mariadb
from my_lib import *
from pprint import pprint
log = create_logger('{}/{}.log'.format(config.log_dir, os.path.basename(__file__)))

conn = mariadb.connect(** config.mariadb_connect)

# # Get archive video list
# with conn.cursor(dictionary=True) as cursor:
#     cursor.execute("SELECT id FROM `videos` WHERE `place` = 'archive' and channel is null")
#     videos = cursor.fetchall()
#
# for i,video in enumerate(tqdm(videos)):
#     vid = video['id']
#     item = internetarchive.get_item(vid)
#     uploader = item.item_metadata['metadata']['uploader']
#     with conn.cursor(dictionary=True) as cursor:
#         cursor.execute("UPDATE `videos` SET `channel`= ? WHERE id = ? AND place = 'archive'",
#                        (uploader, vid))
#         conn.commit()
#         if cursor.rowcount != 1:
#             log.error(f"Change {cursor.rowcount} rows")
#             exit(-1)

# Get yotube video list
with conn.cursor(dictionary=True) as cursor:
    cursor.execute("SELECT id FROM `videos` WHERE `place` = 'yotube' and channel is null")
    videos = cursor.fetchall()

c = 0
c_all = len(videos)
for video in videos:
    vid = video['id']
    c=c+1
    log.debug(f"{c}/{c_all} {vid}")

    # Get downloaded files
    status,dlp_files = find_dlp_files(vid, log)
    if status != 0:
        log.error('Error finding files of video {}'.format(vid))
        continue

    # Read json
    with open(dlp_files['.info.json']) as f:
        data = json.load(f)
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("UPDATE `videos` SET `channel`= ? WHERE id = ? AND place = 'yotube'",
                           (data['channel_id'], vid))

            conn.commit()
            if cursor.rowcount != 1:
                log.error(f"Change {cursor.rowcount} rows")
                exit(-1)
        log.info(f"For {vid} set channel {data['channel_id']}")
        exit(0)
