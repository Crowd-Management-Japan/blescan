import asyncio
#from main import SERIAL_NUMBER
from datetime import datetime
import os
import csv


SERIAL_NUMBER = 45

class Storage:

    def __init__(self, base_dir):
        self.base_dir = base_dir
        self.setup()

    def setup(self):
        # trashbin, so store nothing
        if self.base_dir == "/dev/null":
            return
        # RSSI
        if not os.path.exists(self.base_dir):
            os.makedirs(self.base_dir)
        self.filename_base = f"{self.base_dir}/ACC{SERIAL_NUMBER}_{datetime.now().strftime('%Y%m%d')}"
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
        # append will create if the file does not exist, but set the courser to the end, so seek(0) to get to the start of the file
        with open(filename, "a+") as f:
            f.seek(0)
            if len(f.readlines()) < 1:
                print(f"{filename} not existing... creating file with headers")
                f.write(f"{headers}\n")

    def save_file(self, name, row_data):
        if name not in self.files.keys():
            setup = getattr(self, f"setup_{name}")
            setup()
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

    