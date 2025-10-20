#!/bin/bash

while true; do
  ./4.Upload_to_archive.py
  status=$?
  if [ "$status" -eq "0" ]; then
    break
  fi

#  ./_send_to_telegram.py $status 4.Upload_to_archive.py.log

  echo sleep 20 minutes
  sleep 1200 | pv -t -N "Sleeping"
done

./_send_to_telegram.py $? 4.Upload_to_archive.py.log

