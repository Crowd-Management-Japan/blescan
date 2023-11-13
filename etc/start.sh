#!/bin/bash

source .venv/bin/activate

leds=(led0 led1)

for led in ${leds[@]}
do
    echo changing permission for "/sys/class/leds/$led/"
    sudo chgrp led "/sys/class/leds/$led/trigger"
    sudo chgrp led "/sys/class/leds/$led/brightness"
    sudo chmod g+w /sys/class/leds/$led/trigger
    sudo chmod g+w /sys/class/leds/$led/brightness
done


echo starting wrapper program...

# -u for unbuffered output to see it in systemctl status
python -u wrapper/blescan-wrapper.py

if [ $? -eq 0 ]
then
    python -u bleak/main.py
else
    echo wrapper returned error
fi
