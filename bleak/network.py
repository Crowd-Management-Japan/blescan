
from storage import Storage, prepare_row_data_summary

class Upstream:

    def __init__(self, url):
        self.url = url

    def check_connection(self):
        pass


    def save_from_count(self, id, timestamp, rssi_list, close_threshold):
        param={'device_id':device_id,'date':year_mon_day,'time':hour_min_sec,'count':count_close,'total':count_total,
                                    'rssi_avg':rssi_avg,'rssi_std':rssi_std,'rssi_min':rssi_min,'rssi_max':rssi_max}

        summary_row = prepare_row_data_summary(id, timestamp, rssi_list, close_threshold)


        pass