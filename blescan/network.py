
from storage import prepare_row_data_summary
from datetime import datetime
from queue import Queue
from typing import List, Dict, Union
import requests
from threading import Thread
from time import sleep
import logging
import datetime
import util
import traceback
import config

import json

logger = logging.getLogger('blescan.Network')

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

class Upstream:

    def __init__(self, communicator):
        self.com = communicator

    def check_connection(self):
        pass

    async def save_from_count(self, id: int, timestamp: datetime.datetime, rssi_list: List, close_threshold: int):


        time_format = util.format_datetime_network(timestamp)
        old_format = util.format_datetime_old(timestamp)

        # return value is "DeviceID,Time,Close count,Total count,Avg RSSI,Std RSSI,Min RSSI,Max RSSI"
        summary = prepare_row_data_summary(id, time_format, rssi_list, close_threshold)

        # {'device_id': '45', 'date': '20231020', 'time': '104000', 'count': '26', 'total': '26', 'rssi_avg': '-93.615', 'rssi_std': '3.329', 'rssi_min': '-99', 'rssi_max': '-85'}
        
        # %Y%m%d,%H%M%S
        date = datetime.datetime.now().strftime("%Y%m%d")

        

        params = {'id':id,'timestamp': time_format,'date':date,'time':old_format.replace(':', ''),'close':summary[2],'count':summary[3],
                                    'rssi_avg':summary[4],'rssi_std':summary[5],'rssi_min':summary[6],'rssi_max':summary[7],
                                    'latitude': config.Config.latitude, 'longitude': config.Config.longitude}

        logger.debug("sending message to %s: %s", self.com.url, params)

        self.com.enqueue_send_message(params)


class InternetCommunicator:

    def __init__(self, url):
        self.url = url
        self.send_queue = Queue()
        self._max_queue_size = 100
        self.running = False

    def enqueue_send_message(self, data: Dict):
        if self.send_queue.unfinished_tasks >= self._max_queue_size:
            self.send_queue.get()
            self.send_queue.task_done()
        self.send_queue.put(data)
        logger.debug("enqueued message, size %d", self.send_queue.unfinished_tasks)

    def _send_message(self, data: Dict) -> bool:
        logger.debug("sending message")
        code = 0
        success = False
        while code != 200 and self.running:
            try:
                response = requests.post(self.url, json=data, timeout=5)
                code = response.status_code
                if response.status_code == 200:
                    success = True
                else:
                    logger.error(f"Error sending message to upstream url -- {response}")
                    sleep(2)
            except Exception as e:
                logger.error("No internet. try reconnecting")
                logger.error("Exception catched: %s", e)
                self._wait_for_internet()

        return success

    def _wait_for_internet(self):
        code = 0
        while code != 200 and self.running:
            try:
                response = requests.get(self.url, timeout=5)
                code = response.status_code
                logger.info(f"response code of {self.url}: {code}")
            except Exception as e:
                logger.info("no internet connection. Retry connecting in 5 seconds")
                logger.debug(f"returned exception: {e}")
            finally:
                sleep(5)
        if self.running:
            logger.info("internet connection succeeded")

    def _sending_thread(self):
        while self.running or self.send_queue.unfinished_tasks > 0:
            try: 
                if self.send_queue.unfinished_tasks > 0:
                    task = self.send_queue.get()

                    success = self._send_message(task)

                    if success or not self.running:
                        self.send_queue.task_done()

                    if success:
                        logger.debug(f"message sent to upstream. Remaining in queue: {self.send_queue.unfinished_tasks}")
                    else:
                        logger.warn("Could not send request before exiting due to connection error")
                    
                else:
                    sleep(1)
            except Exception as e:
                logger.error("Exception in Internet thread")
                logger.error(traceback.format_exc(e))

        logger.info("Internet thread finished")

    def start_thread(self):

        if self.running == True:
            logger.error(f"Internet thread already running")

        logger.info("--- Starting Internet Communication Thread ---")

        self.running = True
        self.thread = Thread(target=self._sending_thread, daemon=True)
        self.thread.start()

    def stop(self):
        logger.info("--- shutting down Network thread ---")
        if self.running == False:
            return
        self.running = False
        self.send_queue.join()
        self.thread.join()
        logger.info("--- Network thread shut down ---")
