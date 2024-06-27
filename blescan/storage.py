from datetime import datetime
import os
import csv
from statistics import pstdev, mean
import logging 
from typing import List
import util
from config import Config

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
        self.date = datetime.today()
        self.filename_base = f"{self.base_dir}/ACC{str(Config.serial_number).zfill(2)}_{self.date.strftime('%Y%m%d')}"

        # keep track of what files are already registered
        self.files = {}
        

    def setup_rssi(self):
        filename_rssi = f"{self.filename_base}_rssi.csv"
        self.setup_file(filename_rssi, "ID,Time,RSSI list")
        self.files['rssi'] = filename_rssi

    def setup_beacon_stay(self):
        filename = f"{self.filename_base}_stay_time.csv"
        self.setup_file(filename, "ID,Time,Tag Name,Staying time,Average RSSI,Latitude,Longitude")
        self.files['beacon_stay'] = filename

    def setup_beacon_scan(self):
        filename = f"{self.filename_base}_beacon.csv"
        self.setup_file(filename, "ID,Time,Beacon list,RSSI list")
        self.files['beacon_scan'] = filename

    def setup_summary(self):
        filename = f"{self.filename_base}_summary.csv"
        self.setup_file(filename, "ID,Time,Scans,Scantime,Tot.all,Tot.close,Inst.all,Inst.close,Stat.all,Stat.close," \
                        "Avg RSSI,Std RSSI,Min RSSI,Max RSSI,RSSI thresh,Stat.ratio,Lat,Lon")
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
        now = datetime.now()
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

    def _save_beacon_stay(self, row_data):
        self.save_file('beacon_stay', row_data)

    def _save_beacon_scan(self, row_data):
        self.save_file('beacon_scan', row_data)

    def _save_summary(self, row_data):
        self.save_file('summary', row_data)

    def save_count(self, id: int, timestamp: datetime, scans: int, scantime: float, rssi_list: List, instantaneous_counts: List, static_list: List):
        """
        Saves devices given by BleCount.
        This includes RSSI and summary
        """

        time_format = util.format_datetime_old(timestamp)

        rssi_row = prepare_row_data_rssi(id, time_format, rssi_list)
        summary_row = prepare_row_data_summary(id, time_format, scans, scantime, rssi_list, instantaneous_counts, static_list)

        self._save_rssi(rssi_row)
        self._save_summary(summary_row)


    def save_beacon_scan(self, id, time, beacons):

        tags_rssi = [(beacon.get_major() + beacon.get_minor(), beacon.get_rssi()) for beacon in beacons]

        tags_rssi.sort()
        beacon_scan_row = prepare_row_data_beacon_scan(id, time, tags_rssi)

        self._save_beacon_scan(beacon_scan_row)

    def save_beacon_stay(self, id, time, staying_time, rssi_list, manufacturer_data):

        # saves devices given by BleBeacon
        # this includes the beacon file

        beacon_row = prepare_row_data_beacon(id, time, staying_time, rssi_list, manufacturer_data)
        self._save_beacon_stay(beacon_row)

    def __str__(self):
        return f"Storage({self.base_dir})"
    
    def __repr__(self):
        return self.__str__()

    

def prepare_row_data_beacon_scan(id, time, tag_rssi_list: List[tuple]):
    # surround the list by ""
    tags = [tag for tag, rssi in tag_rssi_list]
    rssi_list = [rssi for tag, rssi in tag_rssi_list]
    return [id, time, f"\"{','.join(tags)}\"", f"\"{','.join(map(str, rssi_list))}\""]

def prepare_row_data_rssi(id, time, rssi_list):
    # surround the list by ""
    return [id, time, f"\"{','.join([str(_) for _ in rssi_list])}\""]

def prepare_row_data_summary(id: int, time: str, scans: int, scantime: float, rssi: List, instantaneous_counts: List, static_list: List):

    tot_all = len(rssi)
    tot_close = len([_ for _ in rssi if _ > Config.Counting.rssi_close_threshold])
    inst_all = round(mean(instantaneous_counts["all"]),3)
    inst_close = round(mean(instantaneous_counts["close"]),3)
    stat_all = len(static_list)
    stat_close = len([dev for dev in static_list if dev.get_rssi() > Config.Counting.rssi_close_threshold])

    std = None
    avg = None
    mini = None
    maxi = None
    
    if tot_all > 0:
        std = round(pstdev(rssi),3)
        avg = round(mean(rssi),3)
        mini = min(rssi)
        maxi = max(rssi)

    return [id, time, scans, scantime, tot_all, tot_close, inst_all, inst_close, stat_all, stat_close, avg, std, mini, maxi,
            Config.Counting.rssi_close_threshold, Config.Counting.static_ratio, Config.latitude, Config.longitude]

def prepare_row_data_beacon(id, timestr, staying_time, rssi_list, manufacturer_data):
    average_rssi = mean(rssi_list)
    #time = len(rssi_list)

    tagname = ''.join([manufacturer_data['major'], manufacturer_data['minor']])

    return [id, timestr, tagname, staying_time, "{:.3f}".format(average_rssi), Config.latitude, Config.longitude]
