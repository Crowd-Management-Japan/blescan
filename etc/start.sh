#!/bin/bash

# all paths should be from blescan as root
BLESCAN_CONFIG_PATH='etc/blescan.conf'
BLESCAN_FALLBACK_CONFIG='blescan/config.ini'
WRAPPER_CONFIG_PATH='etc/wrapper.conf'

# update git repository
git pull origin master

source .venv/bin/activate

# led0 = green, led1 = red
ledGreen='/sys/class/leds/led0'
ledRed='/sys/class/leds/led1'
leds=($ledGreen $ledRed)

for led in ${leds[@]}
do
    echo changing permission for $led
    sudo chmod 666 $led/trigger
    sudo chmod 666 $led/brightness

    echo default-on > $led/trigger
done

sleep 1

echo starting wrapper program...

echo heartbeat > $ledGreen/trigger
echo heartbeat > $ledRed/trigger

# -u for unbuffered output to see it in systemctl status
python -u wrapper/blescan-wrapper.py $WRAPPER_CONFIG_PATH $BLESCAN_CONFIG_PATH

echo input > $ledRed/trigger

if [ $? -eq 0 ]
then
    python -u blescan/main.py $BLESCAN_CONFIG_PATH
else
    echo wrapper returned error
    echo starting blescan with default config
    python -u blescan/main.py $BLESCAN_FALLBACK_CONFIG
fi

sleep 0.5

echo none > $ledGreen/trigger
echo default-on > $ledRed/trigger
echo 1 > $ledRed/brightness

exitcode=$?

echo blescan exit_code: $exitcode

if [ $exitcode -eq 100 ]
then
    sudo shutdown -h now
fi
