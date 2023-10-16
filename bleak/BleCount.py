from typing import List
from device import Device
from datetime import datetime
from collections import namedtuple
from storage import Storage

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

    def store_devices(self):
        print(f"BleCount {self}: storing devices")
        print(f"BleCount {self}: devices found: {len(self.scanned_devices)}")

        self.print(f"exact saving time: {datetime.now()}, exact delta: {datetime.now() - self.last_update}")

        # format for storing:
        # TODO note that currently this sometimes skips a value, because delta might be slightly above 10s
        # solution? use asyncio and wait until 10s are filled?
        now = datetime.now()
        time = now.replace(second=(now.second // 10)*10)
        timestr = time.strftime("%H:%M:%S")
        
        rssi_list = [dev.get_rssi() for dev in self.scanned_devices.values()]
        rssi_data = [45, timestr, rssi_list]

        self.storage.save_rssi(rssi_data)

        self.scanned_devices.clear()
        self.last_update = datetime.now()