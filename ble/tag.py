class Tag:
    def __init__(self,startTime,scanCnt,rssi):
        self.startTime=startTime
        self.endTime=startTime
        self.saveCnt = scanCnt
        self.saveRssi = rssi
        self.upFlg = True

    def update(self,endTime,scanCnt,rssi):
        self.endTime = endTime
        self.saveCnt = self.saveCnt + scanCnt
        self.saveRssi = self.saveRssi + rssi
        self.upFlg = True

    def getStrTime(self):
        return self.startTime

    def getEndTime(self):
        return self.endTime

    def check_Update(self):
        if self.upFlg:
            self.upFlg = False
            return True
        else:
            return False

    def diffTime(self):
        return self.endTime-self.startTime

    def aveRssi(self):
        ret = self.saveRssi / self.saveCnt
        return int(ret + 0.5)
