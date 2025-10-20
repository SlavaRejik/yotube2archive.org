#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mariadb

import config
from my_lib import *

conn = mariadb.connect(** config.mariadb_connect)

log = create_logger('{}/{}.log'.format(config.log_dir, os.path.basename(__file__)))

# Get playlists
with conn.cursor(dictionary=True) as cursor:
    cursor.execute("SELECT * FROM `playlists` WHERE `channel_id` = ?",(config.channel_id,))
    playlists=cursor.fetchall()

# DELETE PLAYLIST MEMBERS FROM DB
# log.debug(f"Delete playlists for chanel {config.channel_id}")
# with conn.cursor(dictionary=True) as cursor:
#     cursor.execute("DELETE FROM `playlists` WHERE `channel_id` = ?", (config.channel_id,))
#     conn.commit()
#     log.debug('Changed {} rows'.format(cursor.rowcount))
# exit(0)


# todo = ['PLYUZcn2y_GPaOlwT5TuVj4QJDJv8fmJD7',
#         'PLYUZcn2y_GPZzk6Rhldkk3B7s4RfqRsq0']

# Cycle by playlists
cur_playlist=0
for playlist in playlists:
    cur_playlist+=1
    # if playlist['id'] not in ltodo:
    #     continue

    # DELETE PLAYLIST MEMBERS FROM DB
    # log.debug(f"Delete playlist members for {playlist['id']}")
    # with conn.cursor(dictionary=True) as cursor:
    #     cursor.execute("DELETE FROM `playlists_members` WHERE `playlist_id` = ?", (playlist['id'],))
    #     conn.commit()
    #     log.debug('Changed {} rows'.format(cursor.rowcount))
    # continue

    # Get playlist members
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM `playlists_members` WHERE `playlist_id` = ? and status is NULL", (playlist['id'],))
        playlist_members = cursor.fetchall()
    cur_video=0


    # Cycle by video
    for video in playlist_members:
        cur_video += 1
        ret = None
        log.debug('Video:{}/{} Playlist:{}/{} "{}"'.format( cur_video, len(playlist_members),
                                                            cur_playlist, len(playlists), playlist['title']))

        # DELETE VIDEOS FROM DB
        # log.debug(f"Delete {video['video_id']}")
        # with conn.cursor(dictionary=True) as cursor:
        #     cursor.execute("DELETE FROM `videos` WHERE `id` = ?", (video['video_id'],))
        #     conn.commit()
        #     log.debug('Changed {} rows'.format(cursor.rowcount))
        # continue

        # Check YouTube video exist in db
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM `videos` WHERE id = ? AND `place` = 'yotube'",(video['video_id'],))
            if cursor.rowcount == 1:
                video_in_db = cursor.fetchall()[0]
            elif cursor.rowcount == 0:
                video_in_db = []
            else:
                log.error('Foud {} rows in db for yotube video {}'.format(cursor.rowcount, video['video_id']))
                exit(-1)


        if video_in_db:
            log.debug('Youtube video already in db with oyid: {}'.format(video_in_db['oyid']))

            # Check files
            status,files = find_dlp_files(video['video_id'],log)
            if status == 0:
                # Files found, don't download again
                log.debug('Mark as checked')
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute("UPDATE `playlists_members` SET `status`='ok' WHERE `video_id` = ?",
                                   (video['video_id'],))
                    conn.commit()
                    log.debug('Changed {} rows'.format(cursor.rowcount))
                continue

        # Download video
        y_video = download_yotube_video(video['video_id'], log)
        if 'error' in y_video:
            log.error(f"Error on download video, skip: {video['video_id']}")
            log.debug('Mark as error')
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("UPDATE `playlists_members` SET `status`='error' WHERE `video_id` = ?",
                               (video['video_id'],))
                conn.commit()
                log.debug('Changed {} rows'.format(cursor.rowcount))
            continue


        if video_in_db:
            log.info('Update re-downlodad video info in db')
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("UPDATE `videos` SET `title`=?, `description`=?, `video_md5`=?, `lang`=?, `license`=?,"
                               "`storage`=?, ctime=current_timestamp() WHERE `id` = ? AND `place` = 'yotube'",
                               (y_video['title'], y_video['description'], y_video['video_md5'],y_video['language'],
                                y_video['license'] if 'license' in y_video else None, config.storage, video['video_id']))
                conn.commit()
                log.debug('Changed {} rows'.format(cursor.rowcount))
        else:
            log.info("Add new YouTube video to db {}".format(video['video_id']))
            oyid = take_new_oyid(conn, log)
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("INSERT INTO `videos` (`id`, `oyid`, `place`, `title`, `description`, `video_md5`, `lang`,"
                           "`license`, `storage`, `ctime`) VALUES (?, ?, 'yotube', ?, ?, ?, ?, ?, ?, current_timestamp())",
                           (y_video['id'], oyid, y_video['title'],  y_video['description'], y_video['video_md5'],
                            y_video['language'], y_video['license'] if 'license' in y_video else None, config.storage))

            conn.commit()
    # exit(0)
cursor.close()
conn.close()




