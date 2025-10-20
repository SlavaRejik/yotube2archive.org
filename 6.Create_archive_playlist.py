# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
# from time import sleep
#
# import mariadb
# import internetarchive
# import json
# import glob
# import config
#
#
# from my_lib import *
#
# playlist_id = 'PLUvHw72mPih40-dvz9t4MWpVWxr0yuiFT'
#
# # internetarchive.configure()
#
# log = create_logger('{}/playlists_on_archive.log'.format(config.log_dir))
# logging.getLogger("ia").setLevel(logging.WARNING)
# conn = mariadb.connect(** config.mariadb_connect)
# cursor = conn.cursor(dictionary=True)
#
# channel_id = 'UCtXOsquZY9z8eb7ob3PM5Sg'
#
# ## Get playlist
# log.info('Get playlist by chanel {}'.format(channel_id))
# cursor.execute("SELECT * FROM `playlists` WHERE `channel_id` = ?",(channel_id,))
# playlists = cursor.fetchall()
#
# pprint(playlists)
# exit(0)
#
# # Read playlist info
# cursor.execute("SELECT `title`,`description`,`ctime` FROM `playlists` WHERE id = ?",(playlist_id,))
# playlist_info = cursor.fetchall()[0]
# log.debug(playlist_info)
#
# # Read playlist members
# playlist_members = {}
# cursor.execute("SELECT `position`, `video_id`, `oyid` FROM `playlists_members` p "
#                "LEFT JOIN videos v ON p.`video_id` = v.`id` WHERE playlist_id = ?",(playlist_id,))
#
# for c in cursor.fetchall():
#     if c['position'] is None or c['video_id'] is None or c['oyid'] is None:
#         log.error('None in playlist member')
#         log.error(c)
#         exit(-1)
#     playlist_members[c['position']] = { 'id': c['video_id'], 'oyid': c['oyid']}
#
# ## Playlist cycle
# for cur in playlist_members:
#     log.debug('Position {}/{} video {}'.format(cur, len(playlist_members), playlist_members[cur]))
#
# cursor.close()
# conn.close()