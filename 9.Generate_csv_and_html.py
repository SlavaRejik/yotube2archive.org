#!/usr/bin/env python
# -*- coding: utf-8 -*-

import mariadb
import csv
from pprint import pprint

import config
from my_lib import *

tree={}
conn = mariadb.connect(** config.mariadb_connect)

log = create_logger('{}/{}.log'.format(config.log_dir, os.path.basename(__file__)))
logging.getLogger("ia").setLevel(logging.WARNING)

# Get extra oyid
with conn.cursor(dictionary=True) as cursor:
    cursor.execute("SELECT oyid,id FROM videos WHERE place = 'archive' AND id != oyid")
    extra = cursor.fetchall()

eid = {}
for e in extra:
    if e['oyid'] in extra:
        eid[e['oyid']].append(e['id'])
    else:
        eid[e['oyid']] = [e['id']]

# Get yotube channels
with conn.cursor(dictionary=True) as cursor:
    cursor.execute("SELECT channel_id FROM `playlists` GROUP BY `channel_id`")
    y_channels=cursor.fetchall()

## Update channels info
for y_channel in y_channels:
    channel_id=y_channel['channel_id']
    if channel_id == '111' or channel_id == '222':
        continue
    log.debug(f'Channel id: {channel_id}')

    # Get video id from the most common channel id
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT v.id FROM `playlists` p "
                       "LEFT JOIN playlists_members pm ON p.id = pm.playlist_id "
                       " LEFT JOIN videos v ON pm.video_id = v.id WHERE p.channel_id= ? "
                       "GROUP BY v.channel ORDER BY count(v.channel) DESC LIMIT 1 ",
                       (channel_id,))
        yid=cursor.fetchall()[0]['id']

    log.debug(f'Video id: {yid}')
    status,files =find_dlp_files(yid,log)
    if status != 0:
        log.error("Files not found")
        exit(-1)

    # Read json
    with open(files['.info.json']) as f:
        data = json.load(f)
        url = data['uploader_url']
        title = data['channel']
        if title == "null":
            title = data['uploader_id']
        log.info(f'Url: {url}')
        log.info(f'Title: {title}')
    tree[channel_id] = {'title': title, 'url': url, 'playlists': {}}

    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT * FROM `channels` WHERE `id` = ?", (channel_id,))
        channel = cursor.fetchone()

    if channel is None:
        log.warning('Channel not found in the database, add')
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("INSERT INTO `channels`(`id`, `title`, `url`) VALUES (?,?,?)",
                           (channel_id, title, url))
            conn.commit()
        continue

    # Check existing channel
    need_update=False

    if channel['title'] != title:
        need_update=True
        log.warning(f'Update title: "{channel["title"]}" > "{title}"')

    if channel['url'] != url:
        need_update = True
        log.warning(f'Update url: {channel["url"]} > {url}')

    if need_update:
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("UPDATE channels SET title=?, url=? WHERE id=?",
                           (title, url, channel_id))
            conn.commit()
            log.debug('Changed {} rows'.format(cursor.rowcount))

    # Get yotube playlists
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT id, title FROM `playlists` WHERE channel_id = ? ORDER BY title", (channel_id,))
        playlists=cursor.fetchall()

    # Get playlists members
    for playlist in playlists:
        tree[channel_id]['playlists'][playlist['id']] = {'title': playlist['title']}

        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT pm.video_id, pm.position, v.oyid, v.title FROM `playlists_members` pm "
                           "LEFT JOIN videos v ON pm.video_id = v.id "
                           "WHERE pm.playlist_id=? AND v.place = 'yotube' ", (playlist['id'],))
            members=cursor.fetchall()

        tree[channel_id]['playlists'][playlist['id']]['members'] = {}
        for m in members:
            tree[channel_id]['playlists'][playlist['id']]['members'][m['position']] = {'id': m['video_id'],
                                                                       'title': m['title'], 'oyid': m['oyid']}


# Make html table
with open('/tmp/video-archive-table.html', 'w', newline='', encoding='utf-8') as file:
    file.write("<table><tr><th>Yotube</th><th>Archive</th><th>Title</th></tr>\n")
    for row in tree:
        file.write (f"<tr><th style='background-color: yellow;'><a target=\"_blank\" href=\"{tree[row]['url']}\"> "
                    f"{tree[row]['url']}</a></th><th colspan=2 style='background-color: yellow;'> "
                    f"{tree[row]['title']}</th></tr>")

        # Playlists
        for playlist in tree[row]['playlists']:
            file.write(f"<tr><th style='background-color: Ivory;'><a target=\"_blank\" "
                       f"href=\"https://www.youtube.com/playlist?list={playlist}\"> {playlist}</a></th>"
                       f"<th colspan=2 style='background-color: Ivory;'>"
                       f"{tree[row]['playlists'][playlist]['title']}</th></tr>")

            # Videos
            for member in dict(sorted(tree[row]['playlists'][playlist]['members'].items())):
                m = tree[row]['playlists'][playlist]['members'][member]
                ar = f"<a target=\"_blank\" href=\"https://archive.org/details/{m['oyid']}\">{m['oyid']}</a>"
                if m['oyid'] in eid:
                    for e in eid[m['oyid']]:
                        ar = f"{ar} <a target=\"_blank\" href=\"https://archive.org/details/{e}\">{e}</a>"

                file.write(f"<tr><td><a target=\"_blank\" href=\"https://youtu.be/{m['id']}\">{m['id']}</a></td>"
                           f"<td>{ar}</td><td>{m['title']}</td></tr>\n")
    file.write("</table>")

# # Make html text
with open('/tmp/video-archive.html', 'w', newline='', encoding='utf-8') as file:
    n=1
    for row in tree:
        file.write(f"<h1 style='background-color: yellow;'><a target=\"_blank\" href=\"{tree[row]['url']}\"> "
               f"{tree[row]['url']}</a><br>{tree[row]['title']}</h1>")

        # Playlists
        for playlist in tree[row]['playlists']:
            file.write(f"<h2 'background-color: Ivory;'><a target=\"_blank\" "
                       f"href=\"https://www.youtube.com/playlist?list={playlist}\">{playlist}</a><br>"
                       f"{tree[row]['playlists'][playlist]['title']}</h2>")

            # Videos
            for member in dict(sorted(tree[row]['playlists'][playlist]['members'].items())):
                m = tree[row]['playlists'][playlist]['members'][member]
                ar = f"<a target=\"_blank\" href=\"https://archive.org/details/{m['oyid']}\">{m['oyid']}</a>"
                if m['oyid'] in eid:
                    for e in eid[m['oyid']]:
                        ar = f"{ar} <a target=\"_blank\" href=\"https://archive.org/details/{e}\">{e}</a>"

                file.write(f"<p>№{n}<br><a target=\"_blank\" href=\"https://youtu.be/{m['id']}\">{m['id']}</a><br>"
                           f"{ar}<br>{m['title']}</p>\n")
                n+=1


# Make csv
with open('/tmp/video-archive.csv', 'w', newline='', encoding='utf-8') as file:
    fieldnames = ['Yotube', 'Archive', 'Title']
    writer = csv.DictWriter(file,
                            fieldnames=fieldnames,
                            delimiter=';',
                            quotechar='"',
                            quoting=csv.QUOTE_NONNUMERIC,
                            extrasaction='ignore')  # Ignore extra fields
    writer.writeheader()
    for row in tree:

        # Channels
        writer.writerow({})
        writer.writerow ({'Yotube': tree[row]['url'], 'Title': tree[row]['title']})
        writer.writerow({})

        # Playlists
        for playlist in tree[row]['playlists']:
            writer.writerow({})
            writer.writerow(({'Yotube': f'https://www.youtube.com/playlist?list={playlist}', 'Title': tree[row]['playlists'][playlist]['title']}))

            # Yotube videos
            for member in dict(sorted(tree[row]['playlists'][playlist]['members'].items())):
                m = tree[row]['playlists'][playlist]['members'][member]
                ar = f"https://archive.org/details/{m['oyid']}"
                if m['oyid'] in eid:
                    for e in eid[m['oyid']]:
                        ar = f"{ar} https://archive.org/details/{e}"

                writer.writerow({'Yotube': f"https://youtu.be/{m['id']}", 'Archive': f"{ar}", 'Title': m['title']})


        # ar='https://archive.org/details/{m['oyid']}'
