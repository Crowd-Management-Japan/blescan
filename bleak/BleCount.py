from typing import List, Any
from device import Device
from datetime import datetime
from collections import namedtuple
from storage import Storage
from numpy import std, mean

import config

class BleCount:
    """
    Class for analysing raw device data
    """

    def __init__(self, rssi_threshold: int = -100, delta:int=10, storage = Storage('/dev/null'), name: str = ''):
        self.scanned_devices = {}
        self.name = name
        self.rssi_threshold = rssi_threshold
        self.delta = delta #seconds
        self.last_update = datetime.now()
        self.storage = storage
        

    def filter_devices(self, devices: List[Device]) -> List[Device]:
        return [dev for dev in devices if dev.get_rssi() > self.rssi_threshold]

    def process_scan(self, devices: List[Device]):

        # filter devices above treshold
        filtered = self.filter_devices(devices)

        # write to local memory
        for device in filtered:
            mac = device.get_mac()
            if mac not in self.scanned_devices.keys():
                self.scanned_devices[mac] = device
            else:
                old = self.scanned_devices[mac]
                if old.get_rssi() < device.get_rssi():
                    self.scanned_devices[mac] = device

        # check if storage should happen
        diff = datetime.now() - self.last_update
        if diff.total_seconds() >= self.delta:
            self.store_devices()

    def __str__(self) -> str:
        return self.name

    def print(self, text: str):
        print(f"BleCount {self}: {text}")

    def get_rssi_list(self) -> List[int]:
        return [dev.get_rssi() for dev in self.scanned_devices.values()]

    def prepare_for_storing_rssi(self, id, time) -> List[Any]:
        rssi_list = self.get_rssi_list()
        return [id, time, rssi_list]

    def prepare_for_storing_summary(self, id, time, close_threshold=-50) -> List[Any]:
        """
        formats scanned_devices for saving into summary file.
        The format is a tuple like "DeviceID,Time,Close count,Total count,Avg RSSI,Std RSSI,Min RSSI,Max RSSI"
        """
        # use floats to make math work
        rssi = self.get_rssi_list()#[float(_) for _ in self.get_rssi_list()]
        count = len(rssi)
        close = len([_ for _ in rssi if _ > close_threshold])
        st = std(rssi)
        avg = mean(rssi)
        mini = min(rssi)
        maxi = max(rssi)

        return [id, time, close, count, avg, st, mini, maxi]



    def store_devices(self):
        print(f"BleCount {self}: storing devices")
        print(f"BleCount {self}: devices found: {len(self.scanned_devices)}")

        self.print(f"exact saving time: {datetime.now()}, exact delta: {datetime.now() - self.last_update}")

        # format for storing:
        now = datetime.now()
        time = now.replace(second=(now.second // 10)*10)
        timestr = time.strftime("%H:%M:%S")
        
        serial = config.SERIAL_NUMBER

        rssi_data = self.prepare_for_storing_rssi(serial, timestr)
        self.storage.save_rssi(rssi_data)

        summary_data = self.prepare_for_storing_summary(serial, timestr)
        self.print(summary_data)
        self.storage.save_summary(summary_data)

        self.scanned_devices.clear()

        # if not using the cut time (whole 10 second steps) it might happen, that steps will be skipped
        self.last_update = time