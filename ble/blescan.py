import bluepy
from datetime import datetime,timedelta
import sys
import csv
from tag import Tag
import os.path
import os
import time

class BleScan:

    def __init__(self,serNum,distance=None,backup=False):
        self.persons = {}
        self.serNum = "ACC" + serNum
        self.distance = distance
        self.minCnt = 2
        self.major = '9055'
        # 特定のタグ共通部分
        self.targetTag = '1233aacc0dc140a78085303a6d64ddb5'
        # SDカードへ書き込みFlag
        self.backup = backup

        # 理想空間時の距離計算
    def Distance(self,RSSI):
        dis = 10**((-61-(RSSI))/(10*1.2))
        print(dis,flush=True)
        return dis

    def Scan(self,now):
        # now = datetime.today()
        csvDir  = self.serNum
        dirPath = "/media/usb0/"+csvDir
        sdPath  = "/home/blescan/data/"+csvDir
        try:
            os.makedirs(dirPath)
        except FileExistsError:
            pass
        csvFile = self.serNum.rstrip('\n')+'_'+now.strftime('%Y%m%d')+"_beacon.csv"
        Headers = ['Time','Tag Name','Staying time','Average RSSI']
        filename = dirPath+"/"+csvFile
        sdFilename = sdPath+"/"+csvFile

        # 時刻の成型
        now = now + timedelta(seconds=10)
        now = now.replace(microsecond = 0)

        scanner = bluepy.btle.Scanner(0)

        tmpDict = {}
        try:
            for i in range(9):
                # 1sスキャン実行
                devices = scanner.scan(1)
                for device in devices:
                    for (adTypeCode, description, valueText) in device.getScanData():
                        if self.targetTag in valueText:
                            # ex:6c19705509.......[-10:-2] → 90550791
                            tmpName = valueText.replace(self.targetTag,'')[-10:-2]
                            if self.major in tmpName:
                                # データとして保持していない時
                                if tmpName not in tmpDict :
                                    tmpDict[tmpName] = {'rssi':device.rssi,'scanCnt':1}
                                else:
                                    tmpDict[tmpName]['rssi'] += device.rssi
                                    tmpDict[tmpName]['scanCnt'] += 1

            for listName in list(tmpDict):
                if tmpDict[listName]['scanCnt'] >= self.minCnt:
                    if listName not in self.persons:
                        print(f'init:{listName}',flush=True)
                                        # Tag:__init__(self,startTime,scanCnt,rssi)
                        self.persons[listName] = Tag(now,tmpDict[listName]['scanCnt'],tmpDict[listName]['rssi'])
                    else:
                        # print(f'update:{listName}',flush=True)
                                        # Tag:update(self,endTime,scanCnt,rssi)
                        self.persons[listName].update(now,tmpDict[listName]['scanCnt'],tmpDict[listName]['rssi'])

            # 毎日　00:00:00秒にて保持しているデータをCSVに書き出す。
            if now.hour == 0 and now.minute == 0 and now.second == 0:
                for TagName in list(self.persons):
                    dt = self.persons[TagName].diffTime()
                    with open(filename,'a') as f:
                        writer = csv.writer(f)
                        writer.writerow([self.persons[TagName].getStrTime().strftime('%Y/%m/%d %H:%M:%S'),TagName,dt.seconds,self.persons[TagName].aveRssi()])

                    # SDカード側にも同じ処理をする。
                    if self.backup:
                        with open(sdFilename,'a') as sf:
                            writer = csv.writer(sf)
                            writer.writerow([self.persons[TagName].getStrTime().strftime('%Y/%m/%d %H:%M:%S'),TagName,dt.seconds,self.persons[TagName].aveRssi()])

                self.persons.clear()
                return
        finally:
            for TagName in list(self.persons):
                if not self.persons[TagName].check_Update():
                    print(f'write:{TagName}',flush=True)
                    dt = self.persons[TagName].diffTime()
                    with open(filename,'a') as f:
                        # ヘッダ情報書き込み
                        if os.stat(filename).st_size == 0:
                            writer = csv.DictWriter(f,fieldnames=Headers)
                            writer.writeheader()

                        writer = csv.writer(f)
                        # writer.writerow([self.persons[TagName].getStrTime().strftime('%Y/%m/%d %H:%M:%S'),TagName,now,dt.seconds,self.persons[TagName].aveRssi()])
                        writer.writerow([self.persons[TagName].getStrTime().strftime('%Y/%m/%d %H:%M:%S'),TagName,dt.seconds,self.persons[TagName].aveRssi()])
                    
                    if self.backup:
                        with open(sdFilename,'a') as sf:
                            # ヘッダ情報書き込み
                            if os.stat(sdFilename).st_size == 0:
                                writer = csv.DictWriter(sf,fieldnames=Headers)
                                writer.writeheader()
                            writer = csv.writer(sf)
                            writer.writerow([self.persons[TagName].getStrTime().strftime('%Y/%m/%d %H:%M:%S'),TagName,dt.seconds,self.persons[TagName].aveRssi()])

                    del self.persons[TagName]
