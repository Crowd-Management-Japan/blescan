#!/bin/bash

# all paths should be from blescan as root
BLESCAN_CONFIG_PATH='etc/blescan.conf'
BLESCAN_FALLBACK_CONFIG='blescan/config.ini'
WRAPPER_CONFIG_PATH='etc/wrapper.conf'

# update git repository
git pull origin master

source .venv/bin/activate

leds=(led0 led1)

for led in ${leds[@]}
do
    echo changing permission for "/sys/class/leds/$led/"
    sudo chgrp led "/sys/class/leds/$led/trigger"
    sudo chgrp led "/sys/class/leds/$led/brightness"
    sudo chmod g+w /sys/class/leds/$led/trigger
    sudo chmod g+w /sys/class/leds/$led/brightness
    sudo echo 1 > /sys/class/leds/$led/brightness
done


echo starting wrapper program...

# -u for unbuffered output to see it in systemctl status
python -u wrapper/blescan-wrapper.py $WRAPPER_CONFIG_PATH $BLESCAN_CONFIG_PATH

if [ $? -eq 0 ]
then
    python -u blescan/main.py $BLESCAN_CONFIG_PATH
else
    echo wrapper returned error
    echo starting blescan with default config
    python -u blescan/main.py $BLESCAN_FALLBACK_CONFIG
fi
