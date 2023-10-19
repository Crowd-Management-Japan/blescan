import bluepy
from datetime import datetime,timedelta
import sys
import csv
import os.path
import time
import queue
import threading
import subprocess
import urllib.request
import requests
from http.client import RemoteDisconnected
import gc
from serial import SerialException
from serial.tools import list_ports
import shutil
import math

sys.path.append(os.path.join(os.path.dirname(__file__), '..'))
from ble.lightThd import LightThd

from digi.xbee.devices import XBeeDevice,RemoteXBeeDevice
from digi.xbee.models.address import XBee16BitAddress
from digi.xbee.exception import TransmitException,XBeeException,TimeoutException

class BleCount:
    initFiles = []
    def __init__(self,serNum,PORT,BAUD_RATE,threshRSSI,macList,backupCopy): # New: added threshRSSI, macList and backupCopy
        #定数を定める
        __FAIL_CNT = 3
        self.serNum = str(serNum)
        self.que = queue.Queue(3)   # queueのマックスサイズを指定。0以下で無限となる。
        self.thd = None
        self.deviceNI = ""
        
         # New: RSSI threshold #############################
        self.threshRSSI = float(threshRSSI)
        self.backupCopy = bool(backupCopy)
        self.macList = bool(macList)
        self.url = "http://www.claudiofeliciani.online/ble_system/get_count.php"
        ###################################################
        
        #親機への送信。ネット接続時は直接サーバーへ送信
        def send_to_parent():
            while True:
                data_list:list
                try:
                    # block=Falseのとき、キューが空なら例外Emptyが送出。
                    items=self.que.get(block=False)
                    data_list = items.split(',')
                    self.que.task_done()

                    if "LED_ON" in items:
                        subprocess.call('ledOn.sh')
                        continue
                    elif "reboot" in items:
                        subprocess.call('reboot')

                except queue.Empty as emp:
                    time.sleep(1)
                    continue

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
                    break
                else:
                    fail_cnt = 0
                    while True:

                        if self.check_internet_connectivity(self.url):#ネット接続良好
                            param={'device_id':device_id,'date':year_mon_day,'time':hour_min_sec,'count':count_close,'total':count_total,
                                    'rssi_avg':rssi_avg,'rssi_std':rssi_std,'rssi_min':rssi_min,'rssi_max':rssi_max}
                            try:
                                request = requests.session()
                                request.keep_alive = False
                                response = request.get(self.url,params=param)
                                response.raise_for_status()
                            except RemoteDisconnected:
                                print("RemoteDisconnected",flush=True)
                            except requests.exceptions.RequestException as e:
                                print(e,flush=True)
                                raise Exception(e)
                            except Exception as e:
                                print("Send other Error")
                                print(e)
                                raise e
                            finally:
                                del data_list,remote_NI,device_id,year_mon_day,hour_min_sec,count_close,count_total,rssi_avg,rssi_std,rssi_min,rssi_max,response
                                gc.collect()
                                break
                        else: #ネットへ接続できないとき
                            print("Internet not connected",flush=True)
                            try:
                                self.device = XBeeDevice(PORT, BAUD_RATE)
                                self.device.open()
                                # タイムアウト時間がデフォルトで4秒、明示的に4秒と設定する
                                self.device.set_sync_ops_timeout(4)
                                router = self.device.get_parameter("CE")
                                # b'\x00' = router
                                # b'\x01' = coordinator
                                ziguse = True
                                if router == b'\x01':
                                    ziguse = False
                                    
                                self.deviceNI = self.device.get_parameter("NI").decode()


                                if ziguse and self._port_check(PORT):#zigbeeを使用することができる状態
                                    remote = RemoteXBeeDevice(self.device, x16bit_addr=XBee16BitAddress.COORDINATOR_ADDRESS)
                                    self.device.send_data_async(remote, items)
                                    break
                                else:
                                    fail_cnt  += 1
                                    break
                            except SerialException: #device.openの例外取得
                                fail_cnt  += 1
                                print("SerialException")
                            except TransmitException as e: #親機と接続されていない時、ここに入る。送信は続けたい
                                fail_cnt  += 1
                                print("Not transmit response (status not ok)")
                            except TimeoutException as e:
                                fail_cnt  += 1
                            except XBeeException as e:
                                fail_cnt  += 1

                            finally:
                                #まだデバイスファイルを開いている状態である時、閉じる
                                if self.device is not None and self.device.is_open():
                                    self.device.close()

                                if __FAIL_CNT <= fail_cnt:
                                    break
                                # 適当時間。
                                # 要注意
                                time.sleep(1)

        try:
            self.device = XBeeDevice(PORT, BAUD_RATE)
            self.device.open()
            # タイムアウト時間がデフォルトで4秒、明示的に4秒と設定する
            self.device.set_sync_ops_timeout(4)
            router = self.device.get_parameter("CE")
            # b'\x00' = router
            # b'\x01' = coordinator
            
            if router == b'\x01':
                pass
                
            self.deviceNI = self.device.get_parameter("NI").decode()

            if self.device is not None and self.device.is_open():
                self.device.close()

        except SerialException: #device.openの例外取得
            # zigbeeの認識がされなかった。
            pass
        except XBeeException :
            #zigbee関連の例外
            pass

        self.thd = threading.Thread(target=send_to_parent, daemon=True)
        self.thd.start()

    def que_add(self,now,devices,countClose,countTotal,avgRSSI,stdRSSI,minRSSI,maxRSSI):
        today = now
        todayStr = today.strftime('%Y%m%d,%H%M%S')
        try:
            self.saveStorage(todayStr.split(',')[0],todayStr.split(',')[1],self.serNum,devices,str(countClose),str(countTotal),
                                str(avgRSSI),str(stdRSSI),str(minRSSI),str(maxRSSI),self.macList,self.backupCopy)

            self.que.put(self.deviceNI+','+str(int(self.serNum))+','+todayStr+','+ \
                        str(countClose) + ',' + str(countTotal) + ',' + \
                        str(avgRSSI)+','+str(stdRSSI)+','+str(minRSSI)+','+str(maxRSSI))
        except:
            #queueがなんらかでフルの可能性
            print("queue full",flush=True)
            pass

    def Scan(self,now):

        # 時刻の成型
        now = now + timedelta(seconds=10)
        now = now.replace(microsecond=0)

        scanner = bluepy.btle.Scanner(0)

        # 8sスキャン実行
        devices = scanner.scan(8)
        print(devices)
        countClose,countTotal,avgRSSI,stdRSSI,minRSSI,maxRSSI = _calcRSSI(devices,self.threshRSSI)

        try:
            self.que_add(now,devices,countClose,countTotal,avgRSSI,stdRSSI,minRSSI,maxRSSI)
        except queue.Full:
            pass

    @staticmethod
    def static_scan(now,threshRSSI):
        # 時刻の成型
        now = now + timedelta(seconds=10)
        now = now.replace(microsecond=0)

        scanner = bluepy.btle.Scanner(0)

        # 8sスキャン実行
        devices = scanner.scan(8)
        countClose,countTotal,avgRSSI,stdRSSI,minRSSI,maxRSSI = _calcRSSI(devices,int(threshRSSI))
        return devices,now,countClose,countTotal,avgRSSI,stdRSSI,minRSSI,maxRSSI

    #ネットの接続確認。どこからでも使用することができるようにstaticとする。
    #ただし、使う用途がこのクラスのみとなるときはprivateのようにする予定。使用してみての判断
    @staticmethod
    def check_internet_connectivity(url):
        try:
            urllib.request.urlopen(url, timeout=1)
            return True
        except:
            return False

    #ポート確認関数
    def _port_check(self,PORT):
        ret = False
        ports = list_ports.comports()
        for port in ports:
            if PORT in port:
                ret = True
                break
        return ret

    #マウントポイントを確認関数
    def _check_mount(self):
        mountPt = '/media/usb0'
        subprocess.run(["mount","-a"])
        return os.path.ismount(mountPt)
    
    #クラス関数を使用するためにclassmethod関数とする。かつ、インスタンスを作成しないでこの関数を使用する必要があった。
    @classmethod
    def saveStorage(cls,ymdstr,hmsstr,serNum,devices,countClose,countTotal,avgRSSI,stdRSSI,minRSSI,maxRSSI,macList,backupCopy):
        summaryFile = 'ACC'+serNum.rstrip('\n')+'_'+ymdstr+'_summary.csv'
        rssiListFile = 'ACC'+serNum.rstrip('\n')+'_'+ymdstr+'_rssi.csv'
        if macList:
            macListFile = 'ACC'+serNum.rstrip('\n')+'_'+ymdstr+'_mac.csv'
        #RAMへ書き込む
        ramdir = '/dev/shm/data/ACC'+str(serNum)
        sddir = '/home/blescan/data/ACC'+str(serNum)
        usbdir= '/media/usb0/ACC'+str(serNum)

        summaryFields=['DeviceID','Time','Close count','Total count','Avg RSSI','Std RSSI','Min RSSI','Max RSSI']
        rssiFields = ['DeviceID','Time','RSSI list']
        macFields = ['DeviceID','Time','MAC address list']

        # %H%M%S左の時刻表記で来るため、%H:%M:%Sに再変換する
        retime = datetime.strptime(hmsstr,'%H%M%S')
        movefile = False
        #5分間隔で10秒以内時のみ処理を実行する
        if (retime.minute % 5 == 0 and retime.second < 10) or (retime.hour == 23 and retime.minute == 59 and retime.second > 40):
            # tmpからコピーしている時の赤LEDを点灯するスレッド。スレッドにしたのは書き込み中のみとすると点灯が目で見てわかりづらい。
            # そのためスリープをいれることになるがその間処理が停滞するのを避ける目的。ほかによい方法があれば変更したいところ
            thd = threading.Thread(target=LightThd.writeAppeal, daemon=True)
            thd.start()
            movefile = True
            
        #通信時のデータをローカルに残す仕様
        rowdata=[serNum,retime.strftime('%H:%M:%S'),countClose,countTotal,avgRSSI,stdRSSI,minRSSI,maxRSSI]

        #RSSIリストをすべて取得するリストのベース
        rowRssiData = [serNum,retime.strftime('%H:%M:%S')]
        #MACアドレスをすべて取得するリストのベース
        if macList:
            rowAddressData = [serNum,retime.strftime('%H:%M:%S')]

        #書き込み列にBlueTooth Device Addressを順不同で追加する。
        for dev in devices:
            rowRssiData.append(dev.rssi)
            if macList:
                rowAddressData.append(dev.addr)

        if not os.path.isdir(ramdir):
            os.makedirs(ramdir)

        #リストに内包されたものは、初回の引継ぎを終えている
        if (not summaryFile in cls.initFiles):
            cls.initFiles.append(summaryFile)
            if os.path.exists(usbdir+'/'+ summaryFile):
                shutil.copy(usbdir + '/' + summaryFile,ramdir + '/')
            elif os.path.exists(sddir + '/' + summaryFile):
                shutil.copy(sddir + '/' + summaryFile,ramdir + '/')
                
        # RSSIデータが保存されているファイルの引継ぎ確認
        if (not rssiListFile in cls.initFiles):
            cls.initFiles.append(rssiListFile)
            if os.path.exists(usbdir+'/'+ rssiListFile):
                shutil.copy(usbdir + '/' + rssiListFile,ramdir + '/')
            elif os.path.exists(sddir + '/' + rssiListFile):
                shutil.copy(sddir + '/' + rssiListFile,ramdir + '/')
        
        # MACアドレスデータが保存されているファイルの引継ぎ確認
        if macList:
            if (not macListFile in cls.initFiles):
                cls.initFiles.append(macListFile)
                if os.path.exists(usbdir+'/'+ macListFile):
                    shutil.copy(usbdir + '/' + macListFile,ramdir + '/')
                elif os.path.exists(sddir + '/' + macListFile):
                    shutil.copy(sddir + '/' + macListFile,ramdir + '/')
        

                
        # New: backup copy ################################
        csvPath = ramdir+'/'+summaryFile
        rssilistPath = ramdir + '/' + rssiListFile
        if macList:
            listPath = ramdir + '/' + macListFile
        
        try:
            if not os.path.isfile(csvPath):
                with open(csvPath,'w') as f:
                    writer = csv.DictWriter(f,fieldnames=summaryFields)
                    writer.writeheader()
            with open(csvPath,'a') as f:
                writer = csv.writer(f)
                writer.writerow(rowdata)
            
            #RSSIリスト書き込み
            if not os.path.isfile(rssilistPath):
                with open(rssilistPath,'w') as f:
                    writer = csv.DictWriter(f,fieldnames=rssiFields)
                    writer.writeheader()
            with open(rssilistPath,'a') as f:
                writer = csv.writer(f)
                writer.writerow(rowRssiData)
                
            #アドレスリスト書き込み
            if macList:
                if not os.path.isfile(listPath):
                    with open(listPath,'w') as f:
                        writer = csv.DictWriter(f,fieldnames=macFields)
                        writer.writeheader()
                with open(listPath,'a') as f:
                    writer = csv.writer(f)
                    writer.writerow(rowAddressData)
            
            if movefile:
                if cls._check_mount(cls):
                    if not os.path.isdir(usbdir):
                        os.makedirs(usbdir)

                    #usbへファイルをコピーする
                    shutil.copy(csvPath,usbdir+'/')
                    shutil.copy(rssilistPath,usbdir+'/')
                    if macList:
                        shutil.copy(listPath,usbdir+'/')

                    subprocess.run(["umount","/media/usb0"])

                if backupCopy:
                    if not os.path.isdir(sddir):
                        os.makedirs(sddir)
                    #sdカードへファイルをコピーする。
                    shutil.copy(csvPath,sddir + '/')
                    shutil.copy(rssilistPath,sddir + '/')
                    if macList:
                        shutil.copy(listPath,sddir + '/')
        except Exception as e:
            print(f' mount NG : {e}',flush=True)

# 共通の計算関数
def _calcRSSI(devices,threshRSSI):
    """
    RSSI平均、基準偏差RSSI、最低RSSI、最高RSSIを求める。
    
    Parameters
    ----------
    devices : list
        scanにより取得したデバイスデータ
    threshRSSI : int
        RSSI閾値
        
    Returns
    -------
    countClose : int
        threshRSSIより大きいRSSI値を持つデバイス数
    avgRSSI       : int
        平均RSSI値
    stdRSSI      : float
        基準偏差RSSI
    minRSSI      : int
        最低RSSI
    maxRSSI      : int
        最高RSSI
        
    """

    # New: RSSI threshold #############################
    countTotal = 0
    countClose = 0
    totalRSSI: int = 0
    minRSSI:int = 0
    maxRSSI:int = -100

    #分散計算用
    stdRSSI:float = 0.0
    dispTotal:int = 0

    # 最低・最高RSSIをともに一番最初のデバイスデータで初期化する。
    # 補足：devicesは、dict_values型
    if 0<len(devices):
        dev = list(devices)[0]
        minRSSI = dev.rssi
        maxRSSI = dev.rssi

    for device in devices:
        #平均を求めるためのRSSI値の合計
        totalRSSI += device.rssi
        #最低RSSI値を求める
        if device.rssi < minRSSI:
            minRSSI = device.rssi
        #最高RSSI値を求める
        if maxRSSI < device.rssi:
            maxRSSI = device.rssi
        #threshRSSI値より大きい範囲でのデバイス数
        if device.rssi>threshRSSI:
            countClose += 1
    countTotal = len(devices)
    avgRSSI = totalRSSI/countTotal

    for device in devices:
        #分散を求める
        dispTotal += pow((avgRSSI - device.rssi),2)
    #基準偏差を求める
    stdRSSI = round(math.sqrt(dispTotal/len(devices)),3)
    avgRSSI = round(avgRSSI,3)

    return countClose,countTotal,avgRSSI,stdRSSI,minRSSI,maxRSSI