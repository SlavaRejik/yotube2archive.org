#!/usr/bin/env python
# -*- coding: utf-8 -*-

import shutil
import mariadb
from my_lib import *
from pprint import pprint
log = create_logger('{}/{}.log'.format(config.log_dir, os.path.basename(__file__)))
conn = mariadb.connect(** config.mariadb_connect)

# Get all video list
with conn.cursor(dictionary=True) as cursor:
    cursor.execute("SELECT p.title,m.video_id,v.video_md5 FROM `playlists` p "
                   "LEFT JOIN playlists_members m on p.id = m.playlist_id "
                   "LEFT JOIN videos v on m.video_id = v.id "
                   " WHERE p.channel_id = 'UC6EuQtUtQpYKI8SBXnUy5og' and (v.storage != 'rejik-2026' OR v.storage is null)")
    videos = cursor.fetchall()
    size = len(videos)
    log.info(f'Found {size} videos')

    c=0
    moved = []
    for video in videos:
        c += 1
        vid = video['video_id']
        if vid in moved:
            log.warning(f'{vid} already moved')
            continue

        log.info(f"{c}/{size} {vid} {video['video_md5']} {video['title']}")

        # Get downloaded files
        status, dlp_files = find_dlp_files(vid, log)
        if status != 0:
            log.warning('Error finding files of video {}'.format(vid))
            exit(-1)

        fmd5 = md5_checksum(dlp_files['.mp4'])
        if fmd5 != video['video_md5']:
            log.warning(f'{fmd5} != {video["video_md5"]}')
            continue

        log.debug(f"{path_by_id(vid)} > {path_by_id_new(vid)}")
        shutil.move(path_by_id(vid), path_by_id_new(vid))

        with conn.cursor(dictionary=True) as cursor:
            cursor.execute( "UPDATE `videos` SET `storage`= ?, video_md5 = ? WHERE id = ? AND place = 'yotube'",
                            (config.storage, fmd5, vid ))
            conn.commit()
            if cursor.rowcount != 1:
                log.error(f"Change {cursor.rowcount} rows")
                exit(-1)
        moved.append(vid)
        if c >1:
            exit(0)


# pprint(videos)