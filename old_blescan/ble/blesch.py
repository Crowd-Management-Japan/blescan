import bluepy
from datetime import datetime
import sys
import csv
import tag
from blescan import BleScan
import time
import signal
from os import path
import subprocess
import configparser

loop = True

def handler(signal,frame):
    global loop
    loop = False
    raise Exception('SIGTERM')

def main():
    global loop
    #識別番号
    serNum = "10"
    Distance = 5

    inifile=configparser.ConfigParser()
    inifile.read('/usr/local/etc/config.ini')

    serNum  =inifile.get('USER','devID')
    # Distance=int(inifile.get('USER','limitDis'))
    backupCopy = bool(int(inifile.get('SETTINGS','BackupCopy')))

    mountPt = '/media/usb0'

    # Ble = BleScan(serNum,Distance)
    Ble = BleScan(serNum,backup = backupCopy)


    signal.signal(signal.SIGTERM,handler)

    proc = subprocess.Popen(['python3','/usr/local/ble/watch.py','0'])

    try:
        while True:
            # 子プロセスの存在確認
            if not proc.poll() == None:
                print("dead")
                raise Exception('Child Process dead')

            # mount positionにusbメモリがmountされているか調べる。
            if not path.ismount(mountPt):
                # mountコマンドを別プロセスで実行する
                subprocess.run(["mount","-a"])
                print('Lost MountPoint',flush=True)

            now = datetime.now()
            if now.second % 10 == 0:
                Ble.Scan(now)
                # 監視用のファイルを更新
                with open ('/usr/local/file/mtimeFile','w'):
                    pass
            time.sleep(0.2)

    except bluepy.btle.BTLEInternalError as e:
        print("BTLEInternalError",flush=True)
        print(e)
        loop = False
    except bluepy.btle.BTLEManagementError as ex:
        print("BTLEManagementError",flush=True)
        print(ex)
        loop = False
    except KeyboardInterrupt as exx:
        print("KeyboardInterrupt: stopped by keyboard input (ctrl-C)",flush=True)
        # raise exx
    except OSError as e:
        print("OSError",flush=True)
    except Exception as exxx:
        print("Unknown-error",flush=True)
        print(exxx)
        # raise exxx
    finally:
        print('subkill',flush=True)
        proc.kill()
        print("End BleScan",flush=True)
        # 書き込みを必ず終えてからプロセスを終わらす
        if loop == False:
            # 抜けてきたらボード赤led trigger戻す。
            with open ("/sys/class/leds/led1/trigger","w") as trig:
                trig.write("input")
            sys.exit(1)
        sys.exit(0)
if __name__ == "__main__":
    print("Start BleScan",flush=True)
    main()
