import bluepy
from datetime import datetime
import sys
from blecount import BleCount
import time
import signal
import os.path
import subprocess
import configparser

loop = True

def handler(signal,frame):
    global loop
    loop = False
    raise Exception('SIGTERM')

def main():
    global loop
    
    #zigbee用定数
    PORT = "/dev/ttyUSB0"
    BAUD_RATE = 9600

    #config.iniのカテゴリー定数
    CATEGORY_SETTING = "SETTINGS"

    inifile = configparser.ConfigParser()
    inifile.read('/usr/local/etc/config.ini')

    serNum = inifile.get('USER','devID')
    threshRSSI = inifile.get(CATEGORY_SETTING,'threshRSSI')               # New: added RSSI threshold
    macList = bool(int(inifile.get(CATEGORY_SETTING,'macList')))          # New: added macList to save MAC addresses
    backupCopy = bool(int(inifile.get(CATEGORY_SETTING,'backupCopy')))    # New: added possibility of local backup
    
    backupPath = '/home/blescan/data'
    if backupCopy:
        if not os.path.isdir(backupPath):
            os.mkdir(backupPath)
        if not os.path.isdir(backupPath+'/ACC'+serNum):
            os.mkdir(backupPath+'/ACC'+serNum)
    ###################################################
 
    Ble = BleCount(serNum,PORT,BAUD_RATE,threshRSSI,macList,backupCopy)# New: added threshRSSI, macList and backupCopy
    signal.signal(signal.SIGTERM,handler)
    proc = subprocess.Popen(['python3','/usr/local/ble/watch.py',"1"])

    try:
        while True:
            # 子プロセスの存在確認
            if not proc.poll() == None:
                print("dead")
                raise Exception('Child Process dead')

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
    except OSError as e:
        print("OSError",flush=True)
    except Exception as exxx:
        print("Unknown-error",flush=True)
        print(exxx)
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
