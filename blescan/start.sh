#!/bin/bash

cd /home/blescan/blescan/bleak

source /home/blescan/blescan/.venv/bin/activate

leds=(led0 led1)

for led in ${leds[@]}
do
    echo changing permission for "/sys/class/leds/$led/"
    sudo chgrp led "/sys/class/leds/$led/trigger"
    sudo chgrp led "/sys/class/leds/$led/brightness"
    sudo chmod g+w /sys/class/leds/$led/trigger
    sudo chmod g+w /sys/class/leds/$led/brightness
done


echo starting main program...
echo using python `which python`

python -u /home/blescan/blescan/bleak/main.py
