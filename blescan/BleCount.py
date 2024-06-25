from typing import List, Any, Union
from device import Device
from datetime import datetime
from collections import namedtuple, Counter
from storage import Storage

import config
import logging

logger = logging.getLogger('blescan.Counting')

class BleCount:
    """
    Class for analysing raw device data.
    Accumulates all devices from each scan until it is called to write the data. Then the list gets cleared.

    This is done, because in the original program, the scan duration was 8s, but this whole program lives with a 1s interval.
    Therefore we need to accumulate devices over several 1s scans, to somehow mimic a longer scan.
    When saving, this accumulation is cleared to mimic the next longer scan.
    """

    def __init__(self, rssi_threshold: int = -100, rssi_close_threshold = -75, delta:int=10, storage: Union[Storage,List[Storage]] = []):
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
        """
        if type(storage) is not list: storage = [storage]
        self.scanned_devices = {}
        self.rssi_threshold = rssi_threshold
        self.close_threshold = rssi_close_threshold
        self.delta = delta
        self.scan_info = {
            "scans": 0,
            "total_time": 0
        }
        #self.last_update = datetime.now()
        self.storages = storage
        self.static_list = []
        self.instantaneous_counts = {
            "all": [],
            "close": []
        }


    # Filter devices that are below the mininium RSSI defined for detection threshold
    def filter_devices(self, devices: List[Device]) -> List[Device]:
        """filter out devices below the minimum rssi threshold"""
        return [dev for dev in devices if dev.get_rssi() > self.rssi_threshold]

    # Filter devices above the specified RSSI threshold for "close"
    def filter_close(self, devices: List[Device]) -> List[Device]:
        """filter out devices below the close rssi threshold"""
        return [dev for dev in devices if dev.get_rssi() > self.close_threshold]
    
    def process_scan(self, devices: List[Device], scantime: float):
        """process one scan interval: accumulates devices."""
        self.scan_info["scans"] += 1
        self.scan_info["total_time"] += scantime

        filtered = self.filter_devices(devices)
        close = self.filter_close(filtered)
        self.instantaneous_counts["all"].append(len(filtered))
        self.instantaneous_counts["close"].append(len(close))
        
        # Assumes multiple detections in a single scan
        for device in filtered:
            mac = device.get_mac()
            self.static_list.append(device.get_mac())

            if mac not in self.scanned_devices.keys():
                self.scanned_devices[mac] = device
            else:
                old = self.scanned_devices[mac]
                if old.get_rssi() < device.get_rssi():
                    self.scanned_devices[mac] = device

        # check if storage should happen
        if self.scan_info["scans"] >= self.delta:
            self.store_devices()
        # note: last_update will always end on whole 10s intervals
        #diff = datetime.now() - self.last_update
        #if diff.total_seconds() >= self.delta:
        #    self.store_devices()

    def __str__(self) -> str:
        return self.name

    def get_rssi_list(self) -> List[int]:
        return [dev.get_rssi() for dev in self.scanned_devices.values()]

    def store_devices(self):
        """
        Call all registered storage instances to save RSSI and summary statistics.
        """
        logger.debug("storing devices")
        logger.info(f"devices found: {len(self.scanned_devices)}")

        #logger.debug(f"exact saving time: {datetime.now()}, exact delta: {datetime.now() - self.last_update}")

        # format for storing:
        now = datetime.now()
        time = now.replace(second=(now.second // 10)*10)
        
        id = config.Config.serial_number

        # Threshold of detections to label a MAC address as static
        static_ratio  = 7

        # Count the number of occurrences of MAC addresses
        mac_counter = Counter(self.static_list)

        # Filtering only MAC addresses whose number of occurrences exceeds a threshold
        filtered_macs = [mac for mac, count in mac_counter.items() if count >= static_ratio]

        # Get a list of devices based on filtered MAC addresses
        static_list = [dev for dev in self.scanned_devices.values() if dev.get_mac() in filtered_macs]

        for storage in self.storages:
            try:
                scantime = scantime = round(self.scan_info["total_time"],3)
                storage.save_count(id, time, scantime, self.close_threshold, self.get_rssi_list(), self.instantaneous_counts, static_list)
            except PermissionError as e:
                logger.debug(f"No writing permission for {storage}")
            except Exception as e:
                logger.debug(f"Unkwnow writing error: {e}")
        
        self.scanned_devices.clear()
        self.static_list.clear()
        self.instantaneous_counts["all"].clear()
        self.instantaneous_counts["close"].clear()
        self.scan_info["scans"] = 0
        self.scan_info["total_time"] = 0

        # if not using the cut time (whole 10 second steps) it might happen, that steps will be skipped
        self.last_update = time