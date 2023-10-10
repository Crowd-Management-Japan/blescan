# Copyright 2017, Digi International Inc.
#
# Permission to use, copy, modify, and/or distribute this software for any
# purpose with or without fee is hereby granted, provided that the above
# copyright notice and this permission notice appear in all copies.
#
# THE SOFTWARE IS PROVIDED "AS IS" AND THE AUTHOR DISCLAIMS ALL WARRANTIES
# WITH REGARD TO THIS SOFTWARE INCLUDING ALL IMPLIED WARRANTIES OF
# MERCHANTABILITY AND FITNESS. IN NO EVENT SHALL THE AUTHOR BE LIABLE FOR
# ANY SPECIAL, DIRECT, INDIRECT, OR CONSEQUENTIAL DAMAGES OR ANY DAMAGES
# WHATSOEVER RESULTING FROM LOSS OF USE, DATA OR PROFITS, WHETHER IN AN
# ACTION OF CONTRACT, NEGLIGENCE OR OTHER TORTIOUS ACTION, ARISING OUT OF
# OR IN CONNECTION WITH THE USE OR PERFORMANCE OF THIS SOFTWARE.

from digi.xbee.devices import XBeeDevice
import threading
import time
import queue
import subprocess
import requests
import serial
from serial.tools import list_ports
from http.client import RemoteDisconnected
import gc
from recieve_wdt import Recieve_wdt
from datetime import datetime
import configparser
from blecount import BleCount

r_wdt = Recieve_wdt(60)
backupCopy:bool = False
macList:bool = False

def send_cloud_thd(que,url):
    global backupCopy
    global macList
    while True:
        try:
            item = que.get(False)
            que.task_done()
            r_wdt.tap()
        except queue.Empty:
            time.sleep(1)
            continue

        data_list = item.split(',')
        del item

        try:
            remote_NI      = data_list[0]
            device_id      = data_list[1]
            year_mon_day   = data_list[2]
            hour_min_sec   = data_list[3]
            count_close    = data_list[4]
            count_total    = data_list[5]
            rssi_avg       = data_list[6]
            rssi_std       = data_list[7]
            rssi_min       = data_list[8]
            rssi_max       = data_list[9]


        except IndexError as e: #変なデータが来た場合、送信実行しないようにする
            continue
        else:
            param={'device_id':device_id,'date':year_mon_day,'time':hour_min_sec,'count':count_close,'total':count_total,
                                    'rssi_avg':rssi_avg,'rssi_std':rssi_std,'rssi_min':rssi_min,'rssi_max':rssi_max}

            if BleCount.check_internet_connectivity(url):
                try:
                    print(remote_NI+','+device_id+','+year_mon_day+','+hour_min_sec + ',' + count_close,flush= True)
                    request = requests.session()
                    request.keep_alive = False
                    response = request.get(url,params=param)
                    response.raise_for_status()#200番台でなかった時に例外を発出してくれる関数
                except (RemoteDisconnected,requests.exceptions.RequestException)as err:
                    print("The server error " f'{err}',flush=True)
                    pass
                finally:
                    del data_list,remote_NI,device_id,year_mon_day,hour_min_sec,count_close,count_total,rssi_avg,rssi_std,rssi_min,rssi_max,response
                    gc.collect()

PORT = "/dev/ttyUSB0"
BAUD_RATE = 9600
SERVER_PORT = 22222
BUFFER_SIZE = 1024

def main(que,t1):
    print(" +-----------------------------------------+")
    print(" | XBee Python Library Receive Data Sample |")
    print(" +-----------------------------------------+\n")
    global backupCopy
    global macList
    inifile = configparser.ConfigParser()
    inifile.read('/usr/local/etc/config.ini')
    serNum = inifile.get('USER','devID')
    threshRSSI = inifile.get('SETTINGS','threshRSSI')               # New: added RSSI threshold
    backupCopy = bool(int(inifile.get('SETTINGS','backupCopy')))    # New: added possibility of local backup
    macList = bool(int(inifile.get('SETTINGS','macList')))          # New: MAC address list
    deviceNI = "NON_ZIGBEE"

    proc = subprocess.Popen(['python3','/usr/local/ble/watch.py',"1"],stdout=subprocess.PIPE)
    #callback関数
    def data_receive_callback(xbee_message):
        decMes = xbee_message.data.decode()
        del xbee_message
        try:
            que.put(decMes,block=False)
        except queue.Full:
            pass
        del decMes
        gc.collect()

    device = XBeeDevice(PORT, BAUD_RATE)
    try:
        device.open()
        deviceNI = device.get_parameter("NI").decode()
        router = device.get_parameter("CE")
        # b'\x00' = router
        # b'\x01' = coordinator
        if router == b'\x00':
            print("The zigbee module is router",flush=True)
        else:
            device.add_data_received_callback(data_receive_callback)
            print("Waiting for data...\n",flush=True)
    except serial.SerialException:
        print("Non connection Zigbee",flush=True)  

    try:
        while True:
            if not proc.poll() == None:
                print("dead")
                raise Exception('Child Process dead')

            if not t1.is_alive():
                print('Thread dead.')
                raise Exception('Thread dead')

            if device.is_open():
                ret:bool = False
                ports = list_ports.comports()
                for port in ports:
                    if PORT in port:
                        ret = True
                        break
                if not ret:
                    device.close()
                    print("Zigbee is open",flush=True)
            else:
                try:

                    device.open()
                    deviceNI = device.get_parameter("NI").decode()
                    router = device.get_parameter("CE")
                    # b'\x00' = router
                    # b'\x01' = coordinator
                    if router == b'\x00':
                        print("The zigbee module is router",flush=True)
                    else:
                        #以前のコールバックを削除しないと前回のと合わせてデータ取得することになるからコールバックを削除する。
                        device.del_data_received_callback(data_receive_callback)
                        device.add_data_received_callback(data_receive_callback)
                        #Start message
                        print("Waiting for data...\n",flush=True)
                except serial.SerialException:
                    #open()関数が使用できないときの例外
                    #zigbeeが本体に接続されていないときは毎度出るためスルーする。
                    pass
                
            r_wdt.check()

            with open ('/usr/local/file/mtimeFile','w'):
                pass

            now = datetime.now()
            if now.second % 10 == 0:
                # scanを実行
                devices,now,countClose,countTotal,avgRSSI,stdRSSI,minRSSI,maxRSSI = BleCount.static_scan(now, threshRSSI)
                todayStr = now.strftime('%Y%m%d,%H%M%S')
                try:                
                    que.put(deviceNI+','+str(int(serNum))+','+todayStr+','+ \
                        str(countClose) + ',' + str(countTotal) + ',' + \
                        str(avgRSSI)+ ',' + str(avgRSSI)+ ',' + str(minRSSI) + ',' + str(maxRSSI))
                    #常になにかしらデータが残る仕様
                    BleCount.saveStorage(todayStr.split(',')[0],todayStr.split(',')[1],serNum,devices,str(countClose),str(countTotal),
                                str(avgRSSI),str(stdRSSI),str(minRSSI),str(maxRSSI),macList,backupCopy)
                except queue.Full:
                    pass

    except OSError as ose:
        print(ose)
        subprocess.call('reboot')
    except Exception as e:
        print("main error")
        print(e)

    finally:
        if device is not None and device.is_open():
            device.del_data_received_callback(data_receive_callback)
            device.close()

if __name__ == '__main__':
    url = "http://www.claudiofeliciani.online/ble_system/get_count.php"
    que = queue.Queue(30)
    t1 = threading.Thread(name='send_cloud_thd', target=send_cloud_thd,args=(que,url,),daemon=True)
    t1.start()
    main(que,t1)
