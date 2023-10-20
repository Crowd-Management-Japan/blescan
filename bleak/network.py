
from storage import Storage, prepare_row_data_summary
import aiohttp
from datetime import datetime

class Upstream:

    def __init__(self, url):
        self.url = url

    def check_connection(self):
        pass


    async def save_from_count(self, id, timestamp, rssi_list, close_threshold):

        # return value is "DeviceID,Time,Close count,Total count,Avg RSSI,Std RSSI,Min RSSI,Max RSSI"
        summary = prepare_row_data_summary(id, timestamp, rssi_list, close_threshold)

        # {'device_id': '45', 'date': '20231020', 'time': '104000', 'count': '26', 'total': '26', 'rssi_avg': '-93.615', 'rssi_std': '3.329', 'rssi_min': '-99', 'rssi_max': '-85'}
        
        # %Y%m%d,%H%M%S
        date = datetime.now().strftime("%Y%m%d")

        params = {'device_id':id,'date':date,'time':timestamp.replace(':', ''),'count':summary[2],'total':summary[3],
                                    'rssi_avg':summary[4],'rssi_std':summary[5],'rssi_min':summary[6],'rssi_max':summary[7]}

        #print(f"sending request with params: {params}")

        async with aiohttp.ClientSession() as session:
            async with session.get(self.url, params=params) as resp:
                print(f"request status: {resp.status}")

        pass