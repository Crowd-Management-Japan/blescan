#!/bin/bash

# all paths should be from blescan as root
BLESCAN_CONFIG_PATH='etc/blescan.conf'
BLESCAN_LOCAL_CONFIG='blescan/config.ini'
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
python3 -u wrapper/blescan-wrapper.py $WRAPPER_CONFIG_PATH $BLESCAN_CONFIG_PATH

wrapper_code=$?
echo exit code $wrapper_code

echo input > $ledRed/trigger



if [[ "$wrapper_code" -eq 0 ]]
then
    sudo .venv/bin/python3 -u blescan/main.py $BLESCAN_CONFIG_PATH
elif [[ "$wrapper_code" -eq 50 ]]
then
    echo starting blescan with default config
    sudo .venv/bin/python3 -u blescan/main.py $BLESCAN_LOCAL_CONFIG
else
    echo wrapper returnet error \(exit code $wrapper_code \)
    sudo .venv/bin/python3 -u blescan/main.py $BLESCAN_LOCAL_CONFIG
fi

exitcode=$?

sleep 0.5

echo none > $ledGreen/trigger
echo default-on > $ledRed/trigger
echo 1 > $ledRed/brightness


echo blescan exit_code: $exitcode

if [[ $exitcode -eq 100 ]]
then
    #sudo shutdown -h now
fi
