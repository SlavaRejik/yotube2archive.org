#!/bin/bash

while true; do

  sudo /usr/sbin/service redsocks restart

  ./Upload_file_tree_to_archive.py
  status=$?
  if [ "$status" -eq "0" ]; then
    break
  fi

#  ./_send_to_telegram.py $status 4.Upload_to_archive.py.log


  echo sleep 10 minutes
  sleep 600 | pv -t -N "Sleeping"
done

./_send_to_telegram.py $? Upload_file_tree_to_archive.py.log

