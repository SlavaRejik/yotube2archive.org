#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from tqdm import tqdm
import mariadb
from selenium import webdriver
from selenium import webdriver
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.by import By
from selenium.webdriver.support.expected_conditions import title_is
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support.ui import Select
from selenium.common.exceptions import NoSuchElementException

import config
from my_lib import *
from pprint import pprint

conn = mariadb.connect(** config.mariadb_connect)

log = create_logger('{}/{}.log'.format(config.log_dir, os.path.basename(__file__)))

# Get playlists
with conn.cursor() as cursor:
    cursor.execute("SELECT video_id FROM `upload_files_name` WHERE channel_id=? and file_name is null",
                   (config.channel_id,))
    vids=cursor.fetchall()



# Run browser
options = webdriver.ChromeOptions()


# For detach
# options.add_experimental_option("detach", True)
options.add_argument(r"--user-data-dir=data/chrome-yotube")
options.add_argument(r"--profile-directory=Default")
options.add_argument('--proxy-server=socks5://127.0.0.1:8888')

# For debug
options.add_experimental_option("debuggerAddress", "127.0.0.1:9222")

options.add_argument("--disable-blink-features=AutomationControlled")
driver = webdriver.Chrome(options=options)
wait = WebDriverWait(driver, 10)

# Check channel id
driver.get(f'https://studio.youtube.com/')
channel = wait.until(EC.element_to_be_clickable((By.ID, 'menu-item-0')))
log.debug(f'YOTUBE: Channel url: {channel.get_attribute("href")}')

if channel.get_attribute("href").startswith(f'https://studio.youtube.com/channel/{config.channel_id}'):
    channel_ok = True
    log.info("YOTUBE: Channel OK")
else:
    log.error("Change channel an run again")
    exit(-1)

c=0
for item in tqdm(vids, desc='YouTube videos'):
    yid = item[0]
    c+=1

    # log.debug(f'{c}/{len(vids)} {yid}')
    driver.get(f'https://studio.youtube.com/video/{yid}/edit')
    wait.until(EC.presence_of_element_located((By.ID, 'video')))

    elements = driver.find_elements(By.ID, "original-filename")

    filename='Not_found'
    if len(elements) >0:
        filename=elements[0].text
        # log.info(f"{yid} Filename: {filename}")
    # else:
    #     log.debug('Not_found')
    #
    # continue
    with conn.cursor(dictionary=True) as cursor:
        cursor.execute("UPDATE upload_files_name SET file_name=? WHERE video_id=?",
                       (filename, yid))
        conn.commit()
        changed=cursor.rowcount

    if changed !=1:
        log.error(f"Changed {changed} lines")
        exit(-1)

    # log.info(f'Update {changed} rows')
