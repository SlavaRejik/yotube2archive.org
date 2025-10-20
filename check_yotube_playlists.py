# #!/usr/bin/env python
# # -*- coding: utf-8 -*-
#
# import mariadb
#
# import config
# from my_lib import *
#
# conn = mariadb.connect(** config.mariadb_connect)
#
# log = create_logger('{}/{}.log'.format(config.log_dir, os.path.basename(__file__)))
# logging.getLogger("ia").setLevel(logging.WARNING)
#
# # Get playlists
# with conn.cursor(dictionary=True) as cursor:
#     cursor.execute("SELECT p.title, p.id, m.video_id, v.place, v.video_md5 FROM `playlists` p "
#                    "LEFT JOIN playlists_members m "
#                    "ON p.id = m.playlist_id "
#                    "LEFT JOIN videos v "
#                    "ON m.video_id = v.id "
#                    "WHERE p.channel_id = ?",(config.channel_id,))
#     db_playlists=cursor.fetchall()
#
# # Cycle by playlists
# playlists ={}
# for p in db_playlists:
#     if p['id'] not in playlists:
#         if p['place'] != 'yotube' and p['place'] != None:
#             log.error('Video not from yotube')
#             log.error(p)
#             exit(-1)
#         playlists[p['id']] = {'title': p['title'],
#                               'id': p['id'],
#                               'downloaded': 0,
#                               'not_downloaded': 0}
#
#     if p['place'] is None or p['video_md5'] is None:
#         playlists[p['id']]['not_downloaded'] += 1
#     else:
#         playlists[p['id']]['downloaded'] += 1
#
# todo = []
# for k in playlists:
#     msg=f"{k} {playlists[k]['title']} {playlists[k]['downloaded']} {playlists[k]['not_downloaded']}"
#     if playlists[k]['not_downloaded'] == 0 and playlists[k]['title'][0].isdigit():
#         todo.append(k)
#         log.info(msg)
#     else:
#         log.warning(msg)
#
# pprint(todo)