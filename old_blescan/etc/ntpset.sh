#!/bin/sh

sudo ntpdate -v ntp.nict.jp

if [ $? -eq 0 ]; then
# 　システムタイムと同期するコマンド
sudo hwclock --systohc
fi

exit 0
