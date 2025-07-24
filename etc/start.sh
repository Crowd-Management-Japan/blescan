#!/bin/bash

# all paths should be from blescan as root
BLESCAN_CONFIG_PATH='etc/blescan.conf'
BLESCAN_LOCAL_CONFIG='blescan/config.ini'
WRAPPER_CONFIG_PATH='etc/wrapper.conf'
LED_CONFIG_PATH='etc/led.txt'

# update git repository
git pull origin master

source .venv/bin/activate

# read LED control flag (1 = enable, 0 = disable)
LED_ENABLED=1
if [[ -f $LED_CONFIG_PATH ]]; then
    LED_ENABLED=$(cat $LED_CONFIG_PATH | tr -d '\r\n ')
fi

# led0 = green, led1 = red
ledGreen='/sys/class/leds/led0'
ledRed='/sys/class/leds/led1'
leds=($ledGreen $ledRed)

if [[ "$LED_ENABLED" -eq 1 ]]; then
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
fi

# -u for unbuffered output to see it in systemctl status
python3 -u wrapper/blescan-wrapper.py $WRAPPER_CONFIG_PATH $BLESCAN_CONFIG_PATH

wrapper_code=$?
echo exit code $wrapper_code

if [[ "$LED_ENABLED" -eq 1 ]]; then
    echo input > $ledRed/trigger
fi


if [[ "$wrapper_code" -eq 0 ]]
then
    sudo python3 -u blescan/main.py $BLESCAN_CONFIG_PATH
elif [[ "$wrapper_code" -eq 50 ]]
then
    echo starting blescan with default config
    sudo python3 -u blescan/main.py $BLESCAN_LOCAL_CONFIG
else
    echo wrapper returnet error \(exit code $wrapper_code \)
    sudo python3 -u blescan/main.py $BLESCAN_LOCAL_CONFIG
fi

exitcode=$?

sleep 0.5

if [[ "$LED_ENABLED" -eq 1 ]]; then
    echo none > $ledGreen/trigger
    echo default-on > $ledRed/trigger
    echo 1 > $ledRed/brightness
fi

echo blescan exit_code: $exitcode

if [[ $exitcode -eq 100 ]]
then
    sudo shutdown -h now
fi
