from typing import List, Any, Union
from device import Device
from datetime import datetime
from collections import namedtuple
from storage import Storage
from numpy import std, mean

import config

class BleCount:
    """
    Class for analysing raw device data.
    Accumulates all devices from each scan until it is called to write the data. Then the list gets cleared.

    This is done, because in the original program, the scan duration was 8s, but this whole program lives with a 1s interval.
    Therefore we need to accumulate devices over several 1s scans, to somehow mimic a longer scan.
    When saving, this accumulation is cleared to mimic the next longer scan.
    """

    def __init__(self, rssi_threshold: int = -100, rssi_close_treshold = -50, delta:int=10, storage: Union[Storage,List[Storage]] = [], name: str = ''):
        """
        Create an instance to keep track of the total amount of devices.

        Keyword arguments:
        rssi_threshold -- completely ignores devices below this threshold

        rssi_close_threshold -- devices with a greater rssi_value are considered close. 
                    Used for the summary statistic

        delta -- time interval (in seconds) to analyse and save data 
                    (currently only 10s make sense, because when storing the time is trimmed to full 10 seconds (00:00, 00:10, 00:20,..))
                    using a value below 10s would lead to writing multiple lines for the same timestamp (00:00, 00:10, 00:10, 00:20,...)

        storage -- a single or a list of storage instances to save the data to. 
                    Multiple storage instances could be used for saving to USB and to SDcard as backup.
                    This class uses the save_rssi and save_summary functions to save data.

        name -- used when printing messages for better identification
        """
        if type(storage) is not list: storage = [storage]
        self.scanned_devices = {}
        self.name = name
        self.rssi_threshold = rssi_threshold
        self.close_threshold = rssi_close_treshold
        self.delta = delta
        self.last_update = datetime.now()
        self.storages = storage
        

    def filter_devices(self, devices: List[Device]) -> List[Device]:
        """filter out devices below the minimum rssi threshold"""
        return [dev for dev in devices if dev.get_rssi() > self.rssi_threshold]

    def process_scan(self, devices: List[Device]):
        """process one scan interval: accumulates devices."""
        
        filtered = self.filter_devices(devices)

        
        for device in filtered:
            mac = device.get_mac()
            if mac not in self.scanned_devices.keys():
                self.scanned_devices[mac] = device
            else:
                old = self.scanned_devices[mac]
                if old.get_rssi() < device.get_rssi():
                    self.scanned_devices[mac] = device

        # check if storage should happen
        # note: last_update will always end on whole 10s intervals
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
        """
        Format data to match the header of the rssi.csv file.
        The format is the tuple (DeviceID, Time, RSSI list)
        """
        rssi_list = self.get_rssi_list()
        return [id, time, f"\"{','.join(rssi_list)}\""]

    def prepare_for_storing_summary(self, id, time, close_threshold=-50) -> List[Any]:
        """
        formats scanned_devices for saving into summary file.
        The format is the tuple (DeviceID,Time,Close count,Total count,Avg RSSI,Std RSSI,Min RSSI,Max RSSI)
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
        """
        Call all registered storage instances to save RSSI and summary statistics.
        """
        self.print("storing devices")
        self.print(f"devices found: {len(self.scanned_devices)}")

        self.print(f"exact saving time: {datetime.now()}, exact delta: {datetime.now() - self.last_update}")

        # format for storing:
        now = datetime.now()
        time = now.replace(second=(now.second // 10)*10)
        timestr = time.strftime("%H:%M:%S")
        
        serial = config.SERIAL_NUMBER

        for storage in self.storages:

            rssi_data = self.prepare_for_storing_rssi(serial, timestr)
            storage.save_rssi(rssi_data)

            summary_data = self.prepare_for_storing_summary(serial, timestr)
            self.print(summary_data)
            storage.save_summary(summary_data)

        self.scanned_devices.clear()

        # if not using the cut time (whole 10 second steps) it might happen, that steps will be skipped
        self.last_update = now#time