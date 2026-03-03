#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# from tqdm import tqdm
import mariadb
from pprint import pprint
from pathlib import Path
import time
import config
from my_lib import *
from my_lib import seconds_to_dhm

conn = mariadb.connect(** config.mariadb_connect)
log = create_logger('{}/{}.log'.format(config.log_dir, os.path.basename(__file__)))

find_dir='/space1/mirror/old.openyogaclass.com/av_yoga'
prefix = Path('/space1/mirror/old.openyogaclass.com')
# find_dir='/mnt/10/mirror/old.openyogaclass.com/av_yoga/lek'
# prefix = Path('/mnt/10/mirror/old.openyogaclass.com/')

ignore_filenames=['Thumbs.db','Bob_Marley_-_Dont_worry,_be_happy.mp3','Upload.lnk','Gagarinskiy_start.flv','Indiyskie_yoga_kto_oni.flv','Moi_Muz_GeniY_2008.avi','shtirlits_1-2.flv']
ignore_dirs=['/av_yoga/Pesnya_ti_mne_verish_ili_net/','/av_yoga/books_statiy/','/av_yoga/mantry/','/av_yoga/music_for_kriya_All_wma/','/av_yoga/veda audio/','/av_yoga/work/','/av_yoga/youtube/']

need_another_round = 0

def psize(l_num):
    return f'{int(l_num/(1024**2)):,}Mb'.replace(',',".")

def mbit(l_num):
    return f'{l_num*8/(1024**2):.2f}Mbit'

## Get files list
def find_all_files_pathlib(l_dir, l_log):
    ret=[]
    root_path = Path(l_dir)
    for p in root_path.rglob('*'):

        if not p.is_file():
            continue
        if str(p.name) in ignore_filenames:
            l_log.debug(f'Ignore {p}')
            continue
        # if str(p.parent.relative_to(prefix)) in ignore_dirs:
        matches = [sub for sub in ignore_dirs if sub in str(p)]
        if matches:
            l_log.debug(f'Ignore {p}')
            continue
        ret.append(p)
    return ret

## Set video attributes
def video_attributes(l_pfile, l_oyid, l_youtube_file_name):
    l_rel_path = str(pfile.relative_to(prefix))
    l_md5 = md5_checksum(l_pfile)
    l_title = f'old.openyogaclass.com/{l_rel_path}'
    l_description = f'File {rel_path}\nfrom old.openyogaclass.com'

    # Set md
    subjects = ['OpenYoga', 'Yoga', 'old.openyogaclass.com']
    ext_id = [f'urn:oyid:{l_oyid}']
    if l_youtube_file_name:
        for y_name in l_youtube_file_name:
            ext_id.append(f"urn:youtube:{y_name['id']}")
            ext_id.append(f"urn:oyid:{y_name['oyid']}")
    l_md = ({'collection': 'opensource_movies',
          'title': l_title,
          'licenseurl': 'https://creativecommons.org/publicdomain/zero/1.0/',
          'subject': subjects,
          'description': l_description,
          'external-identifier': ext_id})
    return l_md5, l_title, l_description, l_md


## MAIN ##
channel = ia_user()
log.debug('Get lists')

## Get filename to oyid dict
youtube_files_name={}
with conn.cursor(dictionary=True) as cursor:
    cursor.execute("SELECT up.file_name, v.id, v.oyid FROM youtube_files_name up "
                   "LEFT JOIN videos v ON up.video_id=v.id "
                   "WHERE v.oyid is not null AND up.file_name is NOT null")
    y_files_name = cursor.fetchall()

for i in y_files_name:
    if i['file_name'] not in youtube_files_name:
        youtube_files_name[i['file_name']]=[{'id': i['id'], 'oyid': i['oyid']}]
    else:
        youtube_files_name[i['file_name']].append({'id': i['id'], 'oyid': i['oyid']})

log.debug(f'Read {len(youtube_files_name)} YouTube files name')

# Get uploaded files
with conn.cursor(dictionary=True) as cursor:
    cursor.execute("SELECT id,oyid,status FROM `videos` WHERE place = 'old.openyogaclass.com' and channel = ?",
                   (channel,))
    upload_files_name = cursor.fetchall()

video_in_db={}
for i in upload_files_name:
    video_in_db[i['id']]={'oyid': i['oyid'], 'status': i['status']}
log.debug(f'Found {len(video_in_db)} video in db')
# pprint(video_in_db)

files_on_disk = find_all_files_pathlib(find_dir,log)

log.debug(f'Found {len(files_on_disk)} files on disk')

# Sort files by existing in db
files_on_disk_sorted=[]
for pfile in files_on_disk:
    rel_path = str(pfile.relative_to(prefix))
    if rel_path in video_in_db:
        files_on_disk_sorted.insert(0, pfile)
    else:
        files_on_disk_sorted.append(pfile)


# exit(0)
# pprint(files_on_disk)
# exit(0)

## Main cycle
####################################
index=0
sum_size=sum(p.stat().st_size for p in files_on_disk)
done_size=0

start_time=0
remain_index=0
remain_items=0
remain_size=0
remain_size_todo=0

log.debug(f'Sum size of files: {int(sum_size/(1024*1024))}M')

for pfile in files_on_disk_sorted:
    rel_path = str(pfile.relative_to(prefix))
    file_name = pfile.name
    index +=1
    d_time=int(time.time()-start_time)
    if remain_items!=0:
        remain_txt=(f'{remain_index}/{remain_items} {psize(remain_size)}/{psize(remain_size_todo)} '
                    f'{seconds_to_dhm(d_time)} TODO: {seconds_to_dhm(int(d_time*remain_size_todo/remain_size))} '
                    f'{mbit(remain_size/d_time)}/s' )
        remain_index+=1
        remain_size+= pfile.stat().st_size
    # else:
    #     remain_txt=f''
        log.debug(f'{index}/{len(files_on_disk)} {psize(done_size)}/{psize(sum_size)} {remain_txt}')

    done_size += pfile.stat().st_size


    if len(rel_path)>255:
        log.error(f'Path too long: {len(rel_path)} {rel_path}')
        exit(-1)

    if rel_path in video_in_db:

        if video_in_db[rel_path]['status'] == 'checked':
            # log.debug(f'Skip {rel_path} as checked')
            continue

        # Check archive file
        oyid = video_in_db[rel_path]['oyid']
        log.debug(f'Check {oyid} {rel_path}')

        md5, title, description, md = video_attributes(pfile, oyid, youtube_files_name.get(file_name))

        # Go to next if tasks
        if check_active_tasks(oyid, log, wait=False) != 0:
            log.info(f'Found active tasks, skip')
            need_another_round = 1
            continue

        # Get item
        item = internetarchive.get_item(oyid)

        # Get files info
        ar_files = {}
        for file in item.files:
            # print(file)
            if file['source'] == 'original' and not file['name'].endswith(('_files.xml', '_meta.sqlite',
                                                                           '_meta.xml', '__ia_thumb.jpg')):
                ar_files[file['name']] = file['md5']

        # Compare files
        if file_name in ar_files:
            # md5
            if ar_files[file_name] != md5:
                log.debug(f'File {file_name} has different md5, redownload')
                # log.debug(md)
                upload_files_to_archive(oyid, str(pfile), md, log)
                need_another_round = 1
                continue
            else:
                log.debug(f'File {file_name} checked md5 {ar_files[file_name]}.')
                del ar_files[file_name]
                if len(ar_files) != 0:
                    log.error(f'Found unknow files in archive item: {ar_files})')
                    exit(-1)
        else:
            log.debug(f'File {file_name} not found, download')
            upload_files_to_archive(oyid, str(pfile), md, log)
            need_another_round = 1
            continue

        # Compare md
        change_md = compare_md(item.item_metadata['metadata'], md)

        # Update md on archive
        if change_md != {}:
            log.info(f'Change md on {oyid}')
            log.debug(change_md)
            need_another_round = 1
            # pprint(item.item_metadata['metadata'])
            r = internetarchive.modify_metadata(oyid, metadata=change_md)
            if not r.ok:
                log.error(f'Can\'t change metadata for {oyid}, code: {r.status_code}. Exit.')
                exit(-1)
            need_another_round = 1
            continue
        else:
            log.debug('Identical md')

        # Set status to checked
        with conn.cursor(dictionary=True) as cursor:
            cursor.execute("UPDATE `videos` SET status=? WHERE id=? and place=?",
                           ('checked', rel_path, 'old.openyogaclass.com'))
            conn.commit()
        log.info(f'Mark {oyid} as checked in db')
        continue

    else:
      log.debug(f'New file {rel_path}')
      old_oyid = None
      if file_name in youtube_files_name:
          old_oyid = youtube_files_name[file_name][0]['oyid']
          log.debug(f'Found old oyid {old_oyid}')
          oyid = take_new_oyid(conn,log,old_oyid)
      else:
          oyid = take_new_oyid(conn,log)

    md5, title, description, md = video_attributes(pfile, oyid, youtube_files_name.get(file_name))


    # Start of real work
    if remain_items == 0:
        log.debug('Start of downloading new files')
        remain_items=len(files_on_disk)-index
        remain_size_todo = sum_size-done_size
        remain_index+=1
        remain_size+= pfile.stat().st_size
        start_time=time.time()


    # Store oyid
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("INSERT INTO videos (id, oyid, place, channel, title, description, video_md5, ctime) "
                       "VALUES (?,?,'old.openyogaclass.com',?,?,?,?,current_timestamp())",
                       (rel_path, oyid, channel, title, description, md5))
        conn.commit()

    # Upload
    upload_files_to_archive(oyid, str(pfile), md, log, sleep_time=60)

    # Set status to uploaded
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("UPDATE `videos` SET status=? WHERE id=? and place=?",
                       ('uploaded', rel_path, 'old.openyogaclass.com'))
        conn.commit()


if need_another_round:
    log.warning('Need another round')
    exit(100)




## Generate html
####################################
html = ('<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN">'
        '<html><head><meta http-equiv="content-type" content="text/html; charset=utf-8"></HEAD><body>')

for pfile in files_on_disk:
    rel_dir = str(pfile.parent.relative_to(prefix))
    rel_path = str(pfile.relative_to(prefix))
    file_name = pfile.name
    html += f'<p><b>{rel_dir}/{file_name}</b><br>'
    html += f'<a target="_blank" href="https://old.openyogaclass.com/{rel_path}">old.openyogaclass.com/{rel_path}</a><br><br>'
    html += f'<a target="_blank" href="https://archive.org/details/{video_in_db[rel_path]["oyid"]}">archive.org/details/{video_in_db[rel_path]["oyid"]}</a> '
    # html+=f'<p>{rel_dir}/<a target="_blank" href="https://archive.org/details/{video_in_db[rel_path]["oyid"]}"><b>{file_name}</b></a>'
    html+=f'(<a target="_blank" href="https://archive.org/download/{video_in_db[rel_path]["oyid"]}/{file_name}">Download</a>) '
    if file_name in youtube_files_name:
        for i in youtube_files_name[file_name]:
            if 'id' in i:
                html+=f'<br><br>Related to: <a target="_blank" href="https://youtu.be/{i["id"]}">youtu.be/{i["id"]}</a>'
            # if 'oyid' in i:
                html+=f'<br>Related to: <a target="_blank" href="https://archive.org/details/{i["oyid"]}">archive.org/details/{i["oyid"]}</a>'
    html+=f'</p>\n'
html+='</body></html>'

with open(f'{config.log_dir}/disk-files.html', 'w', newline='', encoding='utf-8') as file:
    file.write(html)


