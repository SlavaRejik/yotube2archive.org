#!/usr/bin/env python
# -*- coding: utf-8 -*-

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


# todo = [ 'PLYUZcn2y_GPayxEGLI-JMpckToTJukzUo',
#          'PLYUZcn2y_GPZKtZPWSdPJ24yh8fQMWrUx']

# Cycle by playlists
cur_playlist=0

for playlist in playlists:
    playlist_status = 'checked'
    cur_playlist+=1

#    if playlist['id'] not in todo:
#        continue

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

        #if video['video_id'] == 'VY2cG9iGWvg':
        #    continue;

        # Check already checked
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM `videos` WHERE oyid = ? AND `place` = 'archive' and status = 'checked'",
                           (video['oyid'],))
            if cursor.rowcount == 1:
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
        # pprint(y_video)

        # Find yotube playlists for video and make subjects
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT p.`title`, m.`playlist_id` FROM `playlists_members` m " 
                           "LEFT JOIN `playlists` p "
                           "ON p.id = m.playlist_id "
                           "WHERE `video_id` = ? "
                           "GROUP BY p.title", (y_video['id'],))
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

        # Find video on archive.org
        item = internetarchive.get_item(y_video['oyid'])

        ## Already in archive
        if item.item_metadata != {}:

            # Go to next if tasks
            if check_active_tasks(y_video['oyid'],log, wait=False) !=0:
                log.info('Found active tasks, skip')
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
                log.info('Files to delete in {}'.format(y_video['oyid']))
                log.debug(ar_files_to_delete)
                delete_files_from_archive(y_video['oyid'], ar_files_to_delete,log)
                need_another_round = 1
                # continue
                # check_active_tasks(y_video['oyid'],log, wait=True)
                changed_on_archive = True

            # Upload files
            if len(files_to_upload):
                log.info('Files to upload to {}'.format(y_video['oyid']))
                log.debug(files_to_upload)
                upload_files_to_archive(y_video['oyid'],files_to_upload, {},log)
                need_another_round = 1
                changed_on_archive = True

            # Compare md
            change_md = compare_md(item.item_metadata['metadata'], md)

            # Update md on archive
            if change_md != {}:
                log.info("Change md on {}".format(y_video['oyid']))
                log.debug(change_md)
                need_another_round = 1
                r = internetarchive.modify_metadata(y_video['oyid'], metadata=change_md)
                if not r.ok:
                    log.error('Can\'t change metadata for {}, code: {}. Exit.'.format(y_video['oyid'], r.status_code))
                    exit(-1)
                changed_on_archive = True
            else:
                log.debug('Identical md')
        else:
            # Not found in archive
            log.info("Upload new video to archive {}".format(y_video['oyid']))
            log.debug(list(files_on_disk.keys()))
            log.debug(md)
            upload_files_to_archive(y_video['oyid'], list(files_on_disk.keys()), md, log)
            need_another_round = 1


        # Find archive video in db
        db_archive_video = {}
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("SELECT * FROM `videos` WHERE oyid = ? AND place = 'archive'", (y_video['oyid'],))
            if cursor.rowcount == 1:
                log.debug('Found archive video for id {}'.format(y_video['oyid']))
                db_archive_video = cursor.fetchall()[0]

        if db_archive_video != {}:
            # Compare db with current data
            my_map = { 'title': 'title',
                       'description': 'description',
                       'lang': 'language',
                       'license': 'licenseurl',
                     }
            for k,v in my_map.items():
                if str(db_archive_video[k]).replace('"', "'") != str(md[v]).replace('"', "'"):
                    changed_on_archive = True
                    log.debug(' db  {}: "{}"'.format(format(k), db_archive_video[k]))
                    log.debug(' cur {}: "{}"'.format(format(k), md[v]))

            if db_archive_video['video_md5'] != files_on_disk[dpl_files['.mp4']]:
                changed_on_archive = True
                log.debug(' db  md5: "{}"'.format(format(db_archive_video['video_md5'])))
                log.debug(' cur md5: "{}"'.format(format(files_on_disk[dpl_files['.mp4']])))

            if not changed_on_archive:
                log.debug('Mark checked {}'.format(y_video['oyid']))
                with conn.cursor(dictionary=True) as cursor:
                    cursor.execute("UPDATE `videos` SET `status` = 'checked' WHERE oyid = ? and place = 'archive'",
                                   (y_video['oyid'],))
                    conn.commit()
                    log.debug('Changed {} rows'.format(cursor.rowcount))
                continue


            # Update video in db
            log.info('Update video in db {}'.format(y_video['oyid']))
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("UPDATE `videos` SET `oyid` = ?, `title` = ?, `description` = ?, "
                               "`video_md5` = ?, `lang` = ?, `license` = ?, `storage` = ?, `status` = 'downloaded'"
                               "WHERE `videos`.`id` = ? AND `videos`.`place` = 'archive'",
                               (y_video['oyid'], md['title'], md['description'], files_on_disk[dpl_files['.mp4']],
                                md['language'], md['licenseurl'], config.storage,
                               y_video['oyid']))
                conn.commit()
                log.debug('Changed {} rows'.format(cursor.rowcount))
        else:
            # Add new video to db
            log.info('Add new video to db {}'.format(y_video['oyid']))
            with conn.cursor(dictionary=True) as cursor:
                cursor.execute("INSERT INTO `videos`(`id`, `oyid`, `place`, `title`, `description`, `video_md5`, "
                               "`lang`, `license`, `storage`, `status`) "
                                       "VALUES (?, ?, 'archive', ?, ?, ?, ?, ?, ?, ?)",
                                       (y_video['oyid'], y_video['oyid'], md['title'], md['description'],
                                        files_on_disk[dpl_files['.mp4']], md['language'], md['licenseurl'],
                                        config.storage, 'downloaded'))
                conn.commit()

    # Mark playlist if all video good
    if playlist_status == 'checked':
        log.debug(f'Mark playlist "{playlist["title"]}" as checked')
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("UPDATE `playlists` SET `status`='checked' WHERE `id`=?",
                           (playlist['id'],))
            conn.commit()
            log.debug('Changed {} rows'.format(cursor.rowcount))

cursor.close()
conn.close()

if need_another_round:
    log.warning('Need another round')
    exit(100)
