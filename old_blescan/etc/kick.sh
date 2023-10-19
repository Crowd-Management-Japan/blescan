#!/bin/sh
MKDIR=/usr/local/file

writeCron() {
	echo "writeCron"
	targetFile=~/tmpfile
	new_cron_entry="5 5 \* \* \* sudo reboot"
	touch $targetFile
	crontab -l -u blescan > $targetFile
	grep "reboot" $targetFile
	# まだ書かれていない状態
	if [ $? -ne 0 ] ; then
	# modeが0(=BLE Scantime)以外であるとき、cronを書き込む
		if [ $1 -ne 0 ]; then
			echo $new_cron_entry >> $targetFile
			sudo sed -e 's/[\\]//g' $targetFile > ~/tmpF
			crontab -u blescan ~/tmpF
			rm -r $targetFile ~/tmpF
			sudo systemctl restart cron.service
		fi 
	else
		#cronに書かれている状態で、modeが0なら削除する。
		if [ $1 -eq 0 ]; then
			sed '/reboot/d' $targetFile > ~/tmpF
			crontab -u blescan ~/tmpF
			rm -r $targetFile ~/tmpF
			sudo systemctl restart cron.service
		fi
	fi
}

echo none > /sys/class/leds/led1/trigger
echo 0 > /sys/class/leds/led1/brightness
echo none > /sys/class/leds/led0/trigger
echo 0 > /sys/class/leds/led0/brightness

# 消えた事をわかりやすくするためにsleep追加
# 後で削除予定
sleep 1

# 赤緑LED同時3回点滅
for i in `seq 1 3`:
do
	echo 1 > /sys/class/leds/led0/brightness
	echo 1 > /sys/class/leds/led1/brightness
	sleep 0.5
	echo 0 > /sys/class/leds/led0/brightness
	echo 0 > /sys/class/leds/led1/brightness
	sleep 0.5
done

# 今は適当なところにファイルを作成している
# エラー処理を怠っている
# 要修正
# -e = exist FILE
if [ ! -e $MKDIR/mtimeFile ];then
	mkdir -p $MKDIR
fi

touch $MKDIR/mtimeFile

echo 1 > /sys/class/leds/led1/brightness
count=0
mode=0
# 読み込みデータでモードを判別することができる
/usr/bin/python3 /usr/local/etc/ini_read.py
mode=$?

if [ $mode -eq 0 ]; then
	mode=0
	echo "ble scan mode" 
elif [ $mode -eq 1 ]; then
	mode=1;
	echo "ble count mode(PARENT)" 
elif [ $mode -eq 2 ]; then
	mode=2;
	echo "ble count mode(ROUTER)"
elif [ $mode -eq 255 ];then
	echo "Not mode select" 
	exit 1
fi

writeCron $mode

while :
do 
	if [ $mode -eq 0 ]; then
		mount -a
		mountpoint /media/usb0
		if [ $? = '0' ]; then
			echo 0 > /sys/class/leds/led1/brightness
			# 起動PATHを記述予定
			/usr/bin/python3 /usr/local/ble/blesch.py
			#/usr/bin/python3 ble/blesch.py
			break
		fi
	elif [ $mode -eq 1 ]; then
		echo 0 > /sys/class/leds/led1/brightness
		# blecount親機を起動
		/usr/bin/python3 /usr/local/bleCount/ReceiveData.py
		break
	elif [ $mode -eq 2 ]; then
		mount -a
		mountpoint /media/usb0
		echo 0 > /sys/class/leds/led1/brightness
		# blecount子機を起動
		/usr/bin/python3 /usr/local/bleCount/blecountsch.py
		break
	fi
	count=`expr $count + 1`
	
	if [ $count -ge 10 ]; then
		break
	fi
	sleep 1
done

if [ $? = '0' ]; then
	hciconfig hci0 down && hciconfig hci0 up
	exit 0
else
	hciconfig hci0 down && hciconfig hci0 up
	exit 1
fi
