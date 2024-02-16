import datetime
import os
import csv
import config
from statistics import pstdev, mean
import logging 
from typing import List
import util

logger = logging.getLogger('blescan.Storage')

class Storage:
    """
    This class encapsulates the storage interface to make it easily reusable for different locations

    The files are stored in BASE_DIR/ACC{SERIAL_NUMBER}_{CURRENT_DATE(YYMMDD)}_{rssi/summary/beacon}.csv
    Where base_dir can be given in the constructor to choose between e.g. usb or sdcard.

    This class does not check if the data is formatted correctly to the corresponding headers.
    """

    def __init__(self, base_dir):
        """
        construct a storage instance.

        Keyword arguments:
        base_dir -- the base folder to store the files
        """
        self.base_dir = base_dir
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        self.date = datetime.datetime.today()
        self.filename_base = f"{self.base_dir}/ACC{config.Config.serial_number}_{self.date.strftime('%Y%m%d')}"

        # keep track of what files are already registered
        self.files = {}
        

    def setup_rssi(self):
        filename_rssi = f"{self.filename_base}_rssi.csv"
        self.setup_file(filename_rssi, "DeviceID,Time,RSSI list")
        self.files['rssi'] = filename_rssi

    def setup_beacon(self):
        filename = f"{self.filename_base}_beacon.csv"
        self.setup_file(filename, "Time,Tag Name,Staying time, Average RSSI, Latitude, Longitude")
        self.files['beacon'] = filename

    def setup_summary(self):
        filename = f"{self.filename_base}_summary.csv"
        self.setup_file(filename, "DeviceID,Time,Close count,Total count,Avg RSSI,Std RSSI,Min RSSI,Max RSSI, Latitude, Longitude")
        self.files['summary'] = filename


    def setup_file(self, filename, headers):
        """ reusable function. Will check and create file with headers if not already present"""

        # append will create if the file does not exist, but set the courser to the end, so seek(0) to get to the start of the file
        with open(filename, "a+") as f:
            f.seek(0)
            if len(f.readlines()) < 1:
                logger.info(f"{filename} not existing... creating file with headers")
                f.write(f"{headers}\n")

    def check_date_update_files(self):
        now = datetime.datetime.now()
        if now != self.date:
            self.__init__(self.base_dir)


    def save_file(self, name, row_data):
        """
        Save data to a file. The name is used to get the file from the files attribute.
        If it is not present there, it will try to call the similarly named setup function, which should create and register this file.
        """
        self.check_date_update_files()
        if name not in self.files.keys():
            setup_name = getattr(self, f"setup_{name}")
            setup_name()
        filename = self.files[name]
        with open(filename, "a") as f:
            csvwriter = csv.writer(f)
            csvwriter.writerow(row_data)

    def _save_rssi(self, row_data):
        self.save_file('rssi', row_data)

    def _save_beacon(self, row_data):
        self.save_file('beacon', row_data)

    def _save_summary(self, row_data):
        self.save_file('summary', row_data)


    def save_count(self, id: int, timestamp: datetime.datetime, rssi_list: List, close_threshold:int):
        """
        Saves devices given by BleCount.
        This includes RSSI and summary
        """

        time_format = util.format_datetime_old(timestamp)

        rssi_row = prepare_row_data_rssi(id, time_format, rssi_list)
        summary_row = prepare_row_data_summary(id, time_format, rssi_list, close_threshold)

        self._save_rssi(rssi_row)
        self._save_summary(summary_row)


    def save_beacon(self, time, rssi_list, manufacturer_data):

        # saves devices given by BleBeacon
        # this includes the beacon file

        beacon_row = prepare_row_data_beacon(time, rssi_list, manufacturer_data)
        self._save_beacon(beacon_row)

    def __str__(self):
        return f"Storage({self.base_dir})"
    
    def __repr__(self):
        return self.__str__()

    

def prepare_row_data_rssi(id, time, rssi_list):
    return [id, time, f"\"{','.join([str(_) for _ in rssi_list])}\""]

def prepare_row_data_summary(id: int, time: str, rssi: List, close_threshold: int):
    count = len(rssi)
    close = len([_ for _ in rssi if _ > close_threshold])
    st = None
    avg = None
    mini = None
    maxi = None
    
    if count > 0:
        st = pstdev(rssi)
        avg = mean(rssi)
        mini = min(rssi)
        maxi = max(rssi)

    return [id, time, close, count, avg, st, mini, maxi, config.Config.latitude, config.Config.longitude]

def prepare_row_data_beacon(timestr, rssi_list, manufacturer_data):
    average_rssi = mean(rssi_list)
    time = len(rssi_list)

    tagname = ''.join([manufacturer_data['major'], manufacturer_data['minor']])

    return [timestr, tagname, time, average_rssi, config.Config.latitude, config.Config.longitude]
