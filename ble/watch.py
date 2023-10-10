import time
import os
from datetime import datetime
from lightThd import LightThd
import sys

def checkFileAt(filePath,dtnow):
    # 最終更新時間の差
    STOP_SEC = 40
    # ファイルの最終更新時間
    at = os.path.getmtime(filePath)
    dt = datetime.fromtimestamp(at)
    diffdt = abs(dtnow-dt)

    return diffdt.seconds < STOP_SEC

def main(mode):
    filePath = '/usr/local/file/mtimeFile'
    while True:
        led = LightThd()
        led.setMode(int(mode))
        led.setDaemon(True)
        led.isOn()
        while True:
            # 後で時間でタイミングを決める可能性があるため移行　now = datetime.now()
            now = datetime.now()
            if not checkFileAt(filePath,now):
                led.isOff()
                led.join()
                # 赤LED点灯
                with open ("/sys/class/leds/led1/brightness","w") as ledfile:
                    ledfile.write('1')
                break
            # sleep時間は適当なため修正が必要
            time.sleep(10)

        while True:
            now = datetime.now()
            if checkFileAt(filePath,now):
                with open ("/sys/class/leds/led1/brightness","w") as ledfile:
                    ledfile.write('0')
                break
            # sleep時間は適当なため修正が必要
            time.sleep(10)

if __name__ == "__main__":
    args = sys.argv
    main(args[1])
