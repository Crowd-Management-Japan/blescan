#!/bin/bash

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

python3 main.py