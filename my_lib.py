import os
import subprocess
from time import sleep
from tqdm import tqdm
import sys
import glob
from pydub import AudioSegment
import logging
import random
import html
import string
import time
import shutil
import internetarchive
from pathlib import Path
from typing import Generator
import webvtt
import json
import copy
from datetime import datetime
from collections import deque
# import requests
import config
# from pprint import pprint

## Calculate md5 sum of file
import hashlib
def md5_checksum(filename):
    md5 = hashlib.md5()
    with open(filename, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            md5.update(chunk)
    return md5.hexdigest()

def create_logger(log_file: str):
    os.makedirs(os.path.dirname(log_file), exist_ok=True)

    class MaxLevelFilter(logging.Filter):
        def __init__(self, level):
            super().__init__()
            self.level = level
        def filter(self, record):
            # Allow only messages with level <= self.level
            return record.levelno <= self.level

    class CustomFormatter(logging.Formatter):
        # Define ANSI color codes
        grey = "\x1b[37m"
        blue = "\x1b[34m"
        yellow = "\x1b[33m"
        red = "\x1b[31m"
        cyan = "\x1b[36m"
        reset = "\x1b[0m"

        # Format for log messages
        format = "%(asctime)s %(levelname)s %(message)s"

        # Mapping log level to color
        FORMATS = {
            logging.DEBUG: grey + format + reset,
            logging.INFO: cyan + format + reset,
            logging.WARNING: yellow + format + reset,
            logging.ERROR: red + format + reset,
            logging.CRITICAL: red + format + reset
        }

        def format(self, record):
            log_fmt = self.FORMATS.get(record.levelno)
            l_formatter = logging.Formatter(log_fmt)
            return l_formatter.format(record)

    # Create logger
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    formatter = logging.Formatter('%(asctime)s %(levelname)s %(message)s')

    # File handler for logging to a file
    file_handler = logging.FileHandler(log_file)
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    # Handler for stdout (DEBUG and INFO)
    stdout_handler = logging.StreamHandler(sys.stdout)
    stdout_handler.setLevel(logging.DEBUG)
    stdout_handler.addFilter(MaxLevelFilter(logging.INFO))

    # Handler for stderr (WARNING and above)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setLevel(logging.WARNING)

    # Optional: add formatter
    stdout_handler.setFormatter(CustomFormatter())
    stderr_handler.setFormatter(CustomFormatter())

    # Add handlers to logger
    logger.addHandler(stdout_handler)
    logger.addHandler(stderr_handler)

    return logger

## Gen oyid
def gen_oyid():
    characters = string.ascii_letters + string.digits
    random_id = ''.join(random.choices(characters, k=10)) # 62^10 = 8,39 × 10^17
    t = 'oyid_{}'.format(random_id)
    return t

## Take new id with check in db
def take_new_oyid(l_conn, l_log):
    with  l_conn.cursor() as l_cursor:
        while True:
            n = gen_oyid()
            l_cursor.execute("SELECT `oyid` FROM `oyids` WHERE oyid = ?", (n,))
            if l_cursor.rowcount == 0:
                l_cursor.execute("INSERT INTO `oyids`(`oyid`, `ctime`) VALUES(?, current_timestamp())",(n,))
                l_conn.commit()
                l_cursor.close()
                l_log.debug('Take new oyid: {}'.format(n))
                return n
            else:
                l_log.warning("Gen double oyid: {}".format(n))


# VTT
def vtt_lines(src) -> Generator[str, None, None]:
    vtt = webvtt.read(src)

    for caption in vtt:  # type: webvtt.structures.Caption
        for line in caption.text.strip().splitlines():  # type: str
            yield line

# VTT
def deduplicated_lines(lines) -> Generator[str, None, None]:
    last_line = ""
    for line in lines:
        if line == last_line:
            continue

        last_line = line
        yield line

# VTT to text
def vtt_to_linear_text(src, savefile: Path, line_end="\n"):
    with savefile.open("w") as writer:
        for line in deduplicated_lines(vtt_lines(src)):
            writer.write(line.replace("&nbsp;", " ").strip() + line_end)


# def ar_lang(lang,l_log):
#     convert_lang = {'ru': 'rus',
#                     'en': 'eng',
#                     'uk': 'ukr',
#                     'es': 'spa',
#                     'nl': 'nld'}

    # if lang not in convert_lang:
    #     l_log.error("Can't convert language {}".format(lang))
    #     exit(-1)
    # return  convert_lang[lang]



def compare_md(old_md, new_md):
    # Compare md
    change_md = {}
    for k in new_md:
        if k not in old_md or new_md[k] != old_md[k]:
            if k not in old_md and new_md[k] == '':
                continue
            change_md[k] = new_md[k]

    # mediatype and collection can't be changed
    if 'mediatype' in change_md :
        del change_md['mediatype']

    if 'collection' in change_md:
        del change_md['collection']

    return change_md


def upload_files_to_archive(l_oyid, l_files, l_md, l_log, sleep_time=120):

    item = internetarchive.get_item(l_oyid)
    if item.item_metadata != {}:
        c_md = compare_md(item.item_metadata['metadata'], l_md)
    else:
        c_md = copy.deepcopy(l_md)

    description = ''
    if 'description' in c_md:
        description = c_md['description']
        del c_md['description']

    l_log.debug('Upload without description')
    l_log.debug(c_md)
    r1 = internetarchive.upload(identifier=l_oyid,
                                files=l_files,
                                verbose=True,
                                verify=True,
                                retries=10,
                                retries_sleep=60,
                                metadata=c_md)

    if not r1[0].ok:
        l_log.error('Can\'t upload without description video {}, code: {}. Exit.'.format(l_oyid, r1[0].status_code))
        return -1

    # Sleep
    for _ in tqdm(range(sleep_time), desc=f"Sleep {sleep_time} sec"):
        sleep(1)

    if description != '' :
        l_log.debug('Add description')
        r = internetarchive.modify_metadata(l_oyid, metadata={'description': description})
        if not r.ok:
            l_log.error('Can\'t change metadata for {}, code: {}. Exit.'.format(l_oyid, r.status_code))
            exit(-1)
    return 0


def delete_files_from_archive(l_oyid, l_files, l_log):

    r = internetarchive.delete(identifier=l_oyid,
                               files=l_files,
                               verbose=True,
                               cascade_delete=True)
    l_log.debug(r[0])
    if not r[0].ok:
        l_log.error('Can\'t delete video {}, code: {}. Exit.'.format(l_oyid, r[0].status_code))
        return -1

    return 0

# Check active tasks on id and wait if you need
def check_active_tasks(ar_id,l_log, wait=True, wait_time=60):
    while True:
        active = 0
        for task in internetarchive.get_tasks(ar_id):
            if task.color:
                active +=1
        if active > 0:
            l_log.debug('Found {} active tasks for {}'.format(active, ar_id))
            if not wait:
                return active
            time.sleep(wait_time)
        else:
            return active

# Convert id to path
def path_by_id(l_id):
    return '{}/{}/{}/{}/{}'.format(config.yotube_dir, config.channel_id, l_id[0:2], l_id[2:4], l_id)


# Run cmd and return {code: x, stdout: x, stderr: x}
def run_cmd(l_log, cmd):
    output = {}
    l_log.debug('Run cmd: {}'.format(cmd))
    try:
        proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        output['stdout'], output['stderr'] = proc.communicate()
        output = {k: v.decode('utf-8').rstrip() for k, v in output.items()}
        output['code'] = proc.returncode
    except subprocess.CalledProcessError as e:
        sys.stderr.write('common::run_command() : [ERROR]: output = {}, error code = {}\n'.format(e.output, e.returncode))
        sys.exit(3)

    return output

# Find files by yotube id
def find_dlp_files(l_yotube_id,l_log):
    ret = {}
    status = 0
    mandatory = ['.info.json', '.description', '.mp4','.jpg']
    optional = ['.vtt', '.mp3', '.txt']

    for ext in mandatory + optional:
        l_file = glob.glob('{}/*{}'.format(path_by_id(l_yotube_id),ext))
        if len(l_file) != 1:
            if ext in optional:
                continue
            l_log.debug('Found {} {} files for video {}. But expected one. '.format(len(l_file), ext, l_yotube_id))
            status = -1
            continue
        ret[ext] = l_file[0]
    return status,ret


# Download yotube video
def download_yotube_video(l_yid, l_log, l_lang = 'ru', disable_subs=False):
    l_log.debug(f"Download {l_yid} {l_lang}")
    now = datetime.now()
    sub_args = f"--write-sub --sub-lang {l_lang} --write-auto-sub"
    if disable_subs:
        sub_args = ''
    r = run_cmd(l_log, f"{config.yt_dlp} -f 'bestvideo[ext=mp4]+bestaudio[ext=m4a]/mp4' --no-progress "
                       f"--write-description --write-info-json --clean-info-json --write-thumbnail "
                       f"--convert-thumbnails jpg {sub_args} --retries 20 -o '{path_by_id(l_yid)}/%(title)s' "
                       f"'https://www.youtube.com/watch?v={l_yid}'")

    if r['code'] != 0:
        l_log.error('Can\'t download video')
        l_log.error('Return code: {}'.format(r['code']))
        l_log.error('Stdout: {}'.format(r['stdout']))
        l_log.error('Stderr: {}'.format(r['stderr']))

        # Check subtitles error
        if r['stderr'] == "ERROR: Unable to download video subtitles for 'ru': HTTP Error 429: Too Many Requests":
            l_log.warning(f"Detected RU subtitles error")
            return download_yotube_video(l_yid, l_log, l_lang = 'en')

        elif r['stderr'] == "ERROR: Unable to download video subtitles for 'en': HTTP Error 429: Too Many Requests":
            l_log.warning(f"Detected EN subtitles error")
            return download_yotube_video(l_yid, l_log, disable_subs=True)

        else:
            if os.path.exists(path_by_id(l_yid)):
                l_log.info('Remove dir: {} '.format(path_by_id(l_yid)))
                shutil.rmtree(path_by_id(l_yid))
            return {'error':True}

    # Write logs
    if len(r['stdout']):
        with open('{}/yt-dlp.log'.format(path_by_id(l_yid)), 'a') as y_log:
            y_log.write('- {} ----------------\n'.format(now.strftime("%Y-%m-%d %H:%M:%S")))
            y_log.write(r['stdout'])
            y_log.write('\n\n')

    if len(r['stderr']):
        with open('{}/yt-dlp.err'.format(path_by_id(l_yid)), 'a') as y_log:
            y_log.write('- {} ----------------\n'.format(now.strftime("%Y-%m-%d %H:%M:%S")))
            y_log.write(r['stderr'])
            y_log.write('\n\n')

    # Get downloaded files
    status,dlp_files = find_dlp_files(l_yid, l_log)
    if status != 0:
        l_log.error('Error finding files of video {}'.format(l_yid))
        exit(-1)

    # Read json
    with open(dlp_files['.info.json']) as f:
        data = json.load(f)

        l_y_video = {'id': data['id'],
                   'title': data['title'],
                   'language': data['language'] if 'language' in data else 'ru'
                     }
        if 'license' in data:
            l_y_video['license'] = data['license']

    # Read description
    with  open(dlp_files['.description']) as f:
        l_y_video['description'] = f.read()

    # Video
    l_y_video['video'] = dlp_files['.mp4']
    l_y_video['video_md5'] = md5_checksum(l_y_video['video'])

    # mp3
    if '.mp3' not in dlp_files:
        l_log.debug("Gen mp3 for {}".format(l_yid))
        audio = AudioSegment.from_file(l_y_video['video'])
        audio.export(l_y_video['video'][:-1] + '3', format="mp3")

    # Subtitles
    if '.vtt' in dlp_files:
        l_log.debug('Generate txt')
        vtt_to_linear_text(dlp_files['.vtt'], Path(l_y_video['video'][:-3] + 'txt'))

    l_log.debug(l_y_video)
    return l_y_video




def tail_log_for_telegram(filename, n=10):
    l_log = ''
    with open(filename) as f:
        for line in deque(f, n):
            line = html.escape(line, quote=True)
            if len(line.split(' ')) < 3 or line.split(' ')[2] == 'ERROR':
                l_log += '<b>{}</b>'.format(line)
            else:
                l_log += line
    return l_log
