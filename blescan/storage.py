from datetime import datetime
from statistics import pstdev, mean
from typing import List
from config import Config
import csv
import logging 
import os
import shutil
import util

logger = logging.getLogger('blescan.Storage')

FILE_TYPE = ['beacon', 'rssi', 'stay_time', 'summary','transit']
FILE_HEADER = {'rssi': 'ID,Time,RSSI list',
                'stay_time': 'ID,Time,Tag Name,Staying time,Average RSSI,Latitude,Longitude',
                'beacon': 'ID,Time,Beacon list,RSSI list',
                'summary': 'ID,Time,Scans,Scantime,Tot.all,Tot.close,Inst.all,Inst.close,Stat.all,Stat.close,'
                            'Avg RSSI,Std RSSI,Min RSSI,Max RSSI,RSSI thresh,Stat.ratio,Lat,Lon',
                'transit': 'ID,Time,Close list'}

class Storage:
    """
    This class encapsulates the storage interface to make it easily reusable for different locations

    The files are temporarily stored in BASE_DIR/ACC{SERIAL_NUMBER}_{CURRENT_DATE(YYMMDD)}/{CURRENT_TIME(HHMM)}_{rssi/summary/beacon/stay_time}.csv
    Files are later combined and finally saved into this format BASE_DIR/ACC{SERIAL_NUMBER}_{CURRENT_DATE(YYMMDD)}_{rssi/summary/beacon/stay_time}.csv
    Where base_dir can be given in the constructor to choose between e.g. usb or sdcard.

    This class does not check if the data is formatted correctly to the corresponding headers.
    """

    def __init__(self, base_dir):
        """
        construct a storage instance.

        Keyword arguments:
        base_dir -- the base folder to store the files
        today_dir -- the folder to store todays files
        """
        self.base_dir = base_dir
        self.date = datetime.today().date()
        self.today_dir = f"{base_dir}/ACC{str(Config.serial_number).zfill(2)}_{self.date.strftime('%Y%m%d')}"
        if not os.path.exists(self.today_dir):
            os.makedirs(self.today_dir)

    @staticmethod
    def reconstruct_files(base_dir: str):
        today = datetime.today().strftime('%Y%m%d')

        # look for all subfolders and list them
        all_subfolders = []
        for item in os.listdir(base_dir):
            item_path = os.path.join(base_dir, item)
            if os.path.isdir(item_path):
                all_subfolders.append(item)

        # loop all subfolder and filetypes and reconstruct them
        for current_dir in all_subfolders:
            if today not in current_dir:
                for type in FILE_TYPE:
                    all_lines = [FILE_HEADER[type], "\n"]
                    complete_file = f"{base_dir}/{current_dir}_{type}.csv"
                    for hour in range(24):
                        for minute in range(0, 60, 10):
                            piece_file = f"{base_dir}/{current_dir}/{hour:02d}{minute:02d}_{type}.csv"
                            if os.path.exists(piece_file):
                                with open(piece_file, "r") as f:
                                    lines = f.readlines()
                                    all_lines.extend(lines)

                    with open(complete_file, "w") as f:
                        f.writelines(all_lines)

                # delete the subfolder only when
                shutil.rmtree(f"{base_dir}/{current_dir}")

    def check_date_update_files(self):
        today = datetime.today().date()
        if today != self.date:
            self.__init__(self.base_dir)

    def get_rounded_time(self):
        # round down to the nearest 10 minutes
        now = datetime.now()
        rounded_minute = (now.minute // 10) * 10
        rounded_time = now.replace(minute=rounded_minute, second=0, microsecond=0)
        return rounded_time.strftime('%H%M')


    def save_file(self, name, row_data):
        """
        Save data to a file. New files are created every 10 minutes to avoid a slow down for large files.
        Single files are combined on startup by looking for folders of the previous days.
        """
        self.check_date_update_files()
        rounded_time = self.get_rounded_time()
        filename = f"{self.today_dir}/{rounded_time}_{name}.csv"
        with open(filename, "a") as f:
            csvwriter = csv.writer(f)
            csvwriter.writerow(row_data)

    def _save_rssi(self, row_data):
        self.save_file('rssi', row_data)

    def _save_beacon_stay(self, row_data):
        self.save_file('stay_time', row_data)

    def _save_beacon_scan(self, row_data):
        self.save_file('beacon', row_data)

    def _save_summary(self, row_data):
        self.save_file('summary', row_data)

    def _save_transit(self, row_data):
        self.save_file('transit', row_data)

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

    def save_transit(self, id, time, transit_list):

        transit_list.sort()
        transit_row = prepare_row_data_transit(id, time.split('T')[1], transit_list)

        self._save_transit(transit_row)

    def __str__(self):
        return f"Storage: {self.base_dir}"
    
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

def prepare_row_data_transit(id, time, close_ble_list):
    # surround the list by ""
    return [id, time, f"\"{','.join([str(_) for _ in close_ble_list])}\""]

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
    tagname = ''.join([manufacturer_data['major'], manufacturer_data['minor']])
    return [id, timestr, tagname, staying_time, "{:.3f}".format(average_rssi), Config.latitude, Config.longitude]
