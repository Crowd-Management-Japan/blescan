import asyncio
#from main import SERIAL_NUMBER
from datetime import datetime
import os
import csv
import config


SERIAL_NUMBER = config.SERIAL_NUMBER

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
        self.filename_base = f"{self.base_dir}/ACC{SERIAL_NUMBER}_{datetime.now().strftime('%Y%m%d')}"

        # keep track of what files are already registered
        self.files = {}
        

    def setup_rssi(self):
        filename_rssi = f"{self.filename_base}_rssi.csv"
        self.setup_file(filename_rssi, "DeviceID,Time,RSSI list")
        self.files['rssi'] = filename_rssi

    def setup_beacon(self):
        filename = f"{self.filename_base}_beacon.csv"
        self.setup_file(filename, "Time,Tag Name,Staying time, Average RSSI")
        self.files['beacon'] = filename

    def setup_summary(self):
        filename = f"{self.filename_base}_summary.csv"
        self.setup_file(filename, "DeviceID,Time,Close count,Total count,Avg RSSI,Std RSSI,Min RSSI,Max RSSI")
        self.files['summary'] = filename


    def setup_file(self, filename, headers):
        """ reusable function. Will check and create file with headers if not already present"""

        # append will create if the file does not exist, but set the courser to the end, so seek(0) to get to the start of the file
        with open(filename, "a+") as f:
            f.seek(0)
            if len(f.readlines()) < 1:
                print(f"{filename} not existing... creating file with headers")
                f.write(f"{headers}\n")

    def save_file(self, name, row_data):
        """
        Save data to a file. The name is used to get the file from the files attribute.
        If it is not present there, it will try to call the similarly named setup function, which should create and register this file.
        """
        if name not in self.files.keys():
            setup_name = getattr(self, f"setup_{name}")
            setup_name()
        filename = self.files[name]
        with open(filename, "a") as f:
            csvwriter = csv.writer(f)
            csvwriter.writerow(row_data)

    def save_rssi(self, row_data):
        self.save_file('rssi', row_data)

    def save_beacon(self, row_data):
        self.save_file('beacon', row_data)

    def save_summary(self, row_data):
        self.save_file('summary', row_data)

    