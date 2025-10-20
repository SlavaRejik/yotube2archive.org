#!/usr/bin/env python
# -*- coding: utf-8 -*-

import asyncio
from telegram import Bot, LinkPreviewOptions
from telegram.constants import ParseMode
import sys
import os
import config
import lib_telegram



if len(sys.argv) != 3:
    print('Use {} int_status log_name'.format(os.path.basename(__file__)))
    exit(-1)

status = '<b>OK</b>'
if sys.argv[1] != '0':
    status = '<b>ERROR</b>'

text = '{}\n{}'.format(status, lib_telegram.truncate_text_utf8(lib_telegram.tail_log_for_telegram('{}/{}'.format(config.log_dir,sys.argv[2])), 4000))


print(len(text))
lib_telegram.send_by_telegram(text)