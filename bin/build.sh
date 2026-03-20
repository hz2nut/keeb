#!/bin/bash

KEEB_PATH=$HOME/.keeb
UF2="$HOME/nice_view-corne_choc_pro_left-zmk.uf2"

if [ ! -f "$UF2" ]; then
  echo "Not found uf2"
  exit 1
fi

DEV="$(lsblk -o NAME,LABEL -nr | grep -E 'KEEBART' | awk '{print $1}' | head -n 1)"
if [ -z "$DEV" ]; then
  echo "Not found device"
  exit 1
fi

if ! sudo mount "/dev/$DEV" /mnt; then
  echo "Failed mount"
  exit 1
fi

sudo cp "$UF2" /mnt
sudo rm "$UF2"
sudo umount /mnt
echo "done"
