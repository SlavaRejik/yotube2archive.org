#!/usr/bin/env python
# -*- coding: utf-8 -*-
from pprint import pprint
import mariadb
import iso639


import config
from my_lib import *

conn = mariadb.connect(** config.mariadb_connect)

log = create_logger('{}/{}.log'.format(config.log_dir, os.path.basename(__file__)))
logging.getLogger("ia").setLevel(logging.WARNING)

need_another_round = 0

# Get playlists
with conn.cursor(dictionary=True) as cursor:
    cursor.execute("SELECT * FROM `playlists` WHERE `channel_id` = ? and (status != 'checked' or status IS null)"
                   ,(config.channel_id,))
    playlists=cursor.fetchall()

#
# ltodo = [
#     'PL111H',
#         ]


# Cycle by playlists
cur_playlist=0

for playlist in playlists:
    playlist_status = 'checked'
    cur_playlist+=1

    # if playlist['id'] not in ltodo:
    #    continue

    # Get playlist members
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("SELECT `video_id`, `oyid` FROM `playlists_members` p "
                       "LEFT JOIN videos v ON p.`video_id` = v.`id` WHERE playlist_id = ? and oyid is not NULL",
                       (playlist['id'],))
        playlist_members = cursor.fetchall()

    # Cycle by video
    cur_video = 0
    for video in playlist_members:
        cur_video += 1
        changed_on_archive = False
        log.debug('Video:{}/{} Playlist:{}/{} {} "{}"'.format( cur_video, len(playlist_members),
                                                               cur_playlist, len(playlists), video['oyid'],
                                                               playlist['title']))

        # Check values
        if video['video_id'] is None or video['oyid'] is None:
            log.error('None in playlist member')
            log.error(video)
            exit(-1)

        # if video['video_id'] == '1111':
        #     continue
# -----------------------------------------------------------------------------------------------



        channel = ia_user()

        # Get archive video from db
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM `videos` WHERE oyid = ? AND `place` = 'archive' and channel = ?",
                           (video['oyid'],channel))
            if cursor.rowcount > 1:
                log.error(f'>1 video {video["oyid"]} on archive channel {channel} in db')
                exit(-1)
            if cursor.rowcount == 1:
                ar_video = (cursor.fetchall())[0]
            else:
                ar_video ={}

        # if archive video checked
        if ar_video.get('status') == 'checked':
            log.debug('Already checked')
            continue

        playlist_status = 'Not checked'

        # Read yotube video
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM `videos` WHERE oyid = ? AND `place` = 'yotube'",(video['oyid'],))
            if cursor.rowcount == 1:
                y_video = cursor.fetchall()[0]
            else:
                log.error('Foud {} rows in db for yotube video {}'.format(cursor.rowcount, video['oyid']))
                exit(-1)

        # Find yotube playlists for video and make subjects
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT p.`title`, m.`playlist_id` FROM `playlists_members` m "
                           "LEFT JOIN `playlists` p "
                           "ON p.id = m.playlist_id "
                           "WHERE `video_id` = ?  and p.channel_id = ? "
                           "GROUP BY p.title", (y_video['id'],config.channel_id))
            if cursor.rowcount < 1:
                log.error('Foud {} playlist for yotube video {}'.format(cursor.rowcount, y_video['id']))
                exit(-1)

            log.debug('Yotube id: {}'.format(y_video['id']))

            # Make subjects
            subjects = ['OpenYoga', 'Yoga']

            for ret in cursor.fetchall():
                subjects.insert(0,ret['title'])
            # log.debug(subjects)

        # Set md
        md = {'collection': 'opensource_movies',
              'title': y_video['title'],
              'language': iso639.Language.from_part1(y_video['lang']).part3,
              'licenseurl': 'https://creativecommons.org/publicdomain/zero/1.0/',
              'subject': subjects,
              'description': y_video['description'],
              'external-identifier': ['urn:youtube:{}'.format(y_video['id']), 'urn:oyid:{}'.format(y_video['oyid'])],
              'mediatype': 'movies'}

        # Files on disk
        files_on_disk = {}
        status, dpl_files = find_dlp_files(y_video['id'],log)
        if status != 0:
            log.error('Not zero status({}) from files_to_upload for id "{}"'.format(status, y_video['id']))
            exit(-1)
        for f in dpl_files:
            if f not in ['.info.json', '.description']:
                files_on_disk[dpl_files[f]] = md5_checksum(dpl_files[f])


        ## Already in archive
        if ar_video.get('id'):
            item = internetarchive.get_item(ar_video['id'])

            # Go to next if tasks
            if check_active_tasks(ar_video['id'],log, wait=False) !=0:
                log.info(f'Found active tasks, skip')
                need_another_round = 1
                continue

            # Get archive files
            ar_files={}
            for file in item.files:
                # print(file)
                if file['source'] == 'original' and not file['name'].endswith(('_files.xml', '_meta.sqlite',
                                                                               '_meta.xml', '__ia_thumb.jpg')):
                    ar_files[file['name']] = file['md5']

            # Compare files
            ar_files_to_delete = []
            files_to_upload = []
            for file_path in files_on_disk:
                file_name = os.path.basename(file_path)
                if file_name in ar_files:
                    if ar_files[file_name] == files_on_disk[file_path]:
                        log.debug('Identical files {}'.format(file_name))
                        del ar_files[file_name]
                        continue
                    else:
                        log.debug('File exist but md5 different {}'.format(file_name))
                        files_to_upload.append(file_path)
                        del ar_files[file_name]

                else:
                    files_to_upload.append(file_path)

            # Original and derivative files to delete
            for n in ar_files.keys():
                ar_files_to_delete.append(n)
                for i in item.files:
                    if 'original' in i and i['original'] == n:
                        ar_files_to_delete.append(i['name'])

            # Delete files
            if len(ar_files_to_delete):
                log.info('Files to delete in {}'.format(ar_video['id']))
                log.debug(ar_files_to_delete)
                delete_files_from_archive(ar_video['id'], ar_files_to_delete,log)
                need_another_round = 1
                changed_on_archive = True

            # Upload files
            if len(files_to_upload):
                log.info('Files to upload to {}'.format(ar_video['id']))
                log.debug(files_to_upload)
                upload_files_to_archive(ar_video['id'],files_to_upload, {},log)
                need_another_round = 1
                changed_on_archive = True

            # Compare md
            change_md = compare_md(item.item_metadata['metadata'], md)

            # Update md on archive
            if change_md != {}:
                log.info("Change md on {}".format(ar_video['id']))
                log.debug(change_md)
                need_another_round = 1
                r = internetarchive.modify_metadata(ar_video['id'], metadata=change_md)
                if not r.ok:
                    log.error('Can\'t change metadata for {}, code: {}. Exit.'.format(ar_video['id'], r.status_code))
                    exit(-1)
                changed_on_archive = True
            else:
                log.debug('Identical md')

                if changed_on_archive:
                    continue

                # Check if nothing changed
                # Compare db with current data
                my_map = { 'title': 'title',
                           'description': 'description',
                           'lang': 'language',
                           'license': 'licenseurl',
                         }
                for k,v in my_map.items():
                    if str(ar_video[k]).replace('"', "'") != str(md[v]).replace('"', "'"):
                        changed_on_archive = True
                        log.debug(' db  {}: "{}"'.format(format(k), ar_video[k]))
                        log.debug(' cur {}: "{}"'.format(format(k), md[v]))

                if ar_video['video_md5'] != files_on_disk[dpl_files['.mp4']]:
                    changed_on_archive = True
                    log.debug(' db  md5: "{}"'.format(format(ar_video['video_md5'])))
                    log.debug(' cur md5: "{}"'.format(format(files_on_disk[dpl_files['.mp4']])))

                # Mark checked if nothing changing
                if not changed_on_archive:
                    log.debug('Mark checked {}'.format(ar_video['id']))
                    with conn.cursor(dictionary=True) as cursor:
                        cursor.execute("UPDATE `videos` SET `status` = 'checked',`channel`= ? WHERE id = ? and place = 'archive'",
                                       (item.item_metadata['metadata']['uploader'], ar_video['id'],))
                        conn.commit()
                        log.debug('Changed {} rows'.format(cursor.rowcount))
                    continue


                # Update video in db
                log.info('Update video in db {}'.format(ar_video['id']))
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute("UPDATE `videos` SET `oyid` = ?, `channel`= ?, `title` = ?, `description` = ?, "
                                   "`video_md5` = ?, `lang` = ?, `license` = ?, `storage` = ?, `status` = 'downloaded'"
                                   "WHERE `videos`.`id` = ? AND `videos`.`place` = 'archive'",
                                   (y_video['oyid'], channel, md['title'], md['description'], files_on_disk[dpl_files['.mp4']],
                                    md['language'], md['licenseurl'], config.storage,
                                   ar_video['id']))
                    conn.commit()
                    log.debug('Changed {} rows'.format(cursor.rowcount))
        else:
            # Not found in archive for current channel

            new_oyid = y_video['oyid']
            # Find oyid video
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("SELECT * FROM `videos` WHERE oyid = ? AND `place` = 'archive'",
                               (video['oyid'],))
                if cursor.rowcount > 0:
                    log.warning('OYID {} already exists, need sub oyid'.format(video['oyid']))
                    new_oyid = take_new_oyid(conn, log, y_video['oyid'])

            log.info("Upload new video to archive {}".format(new_oyid))

            # Add video to db
            log.info('Add new video to db {}'.format(new_oyid))
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("INSERT INTO `videos`(`id`, `oyid`, `place`, `channel`, `title`, `description`, "
                               "`video_md5`, `lang`, `license`, `storage`) "
                               "VALUES (?, ?, 'archive', ?, ?, ?, ?, ?, ?, ?)",
                                       (new_oyid, y_video['oyid'], channel, md['title'], md['description'],
                                        files_on_disk[dpl_files['.mp4']], md['language'], md['licenseurl'],
                                        config.storage))
                conn.commit()


            upload_files_to_archive(new_oyid, list(files_on_disk.keys()), md, log)
            need_another_round = 1

            # Mark downloaded
            log.info('Update video in db {}'.format(new_oyid))
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("UPDATE `videos` SET `status` = 'downloaded'"
                               "WHERE `videos`.`id` = ? AND `videos`.`place` = 'archive'",
                               (new_oyid,))
                conn.commit()
                log.debug('Changed {} rows'.format(cursor.rowcount))

    # Mark playlist if all video good
    if playlist_status == 'checked':
        log.debug(f'Mark playlist "{playlist["title"]}" as checked')
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("UPDATE `playlists` SET `status`='checked' WHERE `id`=?",
                           (playlist['id'],))
            conn.commit()
            log.debug('Changed {} rows'.format(cursor.rowcount))
#
        # exit(0)
cursor.close()
conn.close()

if need_another_round:
    log.warning('Need another round')
    exit(100)
