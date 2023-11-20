
from storage import prepare_row_data_summary
from datetime import datetime
from queue import Queue
from typing import List, Dict, Union
import requests
from threading import Thread
from time import sleep
import logging

import json

logger = logging.getLogger('blescan.Network')


class Upstream:

    def __init__(self, communicator):
        self.com = communicator

    def check_connection(self):
        pass

    async def save_from_count(self, id, timestamp, rssi_list, close_threshold):

        # return value is "DeviceID,Time,Close count,Total count,Avg RSSI,Std RSSI,Min RSSI,Max RSSI"
        summary = prepare_row_data_summary(id, timestamp, rssi_list, close_threshold)

        # {'device_id': '45', 'date': '20231020', 'time': '104000', 'count': '26', 'total': '26', 'rssi_avg': '-93.615', 'rssi_std': '3.329', 'rssi_min': '-99', 'rssi_max': '-85'}
        
        # %Y%m%d,%H%M%S
        date = datetime.now().strftime("%Y%m%d")

        params = {'id':id,'date':date,'time':timestamp.replace(':', ''),'count':summary[2],'total':summary[3],
                                    'rssi_avg':summary[4],'rssi_std':summary[5],'rssi_min':summary[6],'rssi_max':summary[7]}

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

    def _send_message(self, data: Dict):
        logger.debug("sending message")
        code = 0
        while code != 200:
            try:
                response = requests.post(self.url, json=data, timeout=5)
                code = response.status_code
                if response.status_code != 200:
                    logger.error(f"Error sending message to upstream url -- {response}")
            except:
                logger.error("No internet. try reconnecting")
                self._wait_for_internet()

    def _wait_for_internet(self):
        code = 0
        while code != 200:
            try:
                response = requests.get(self.url, timeout=5)
                code = response.status_code
            except:
                logger.info("no internet connection. Retry connecting in 5 seconds")
            finally:
                sleep(5)
        logger.info("internet connection succeeded")

    def _sending_thread(self):
        while self.running:
            if self.send_queue.unfinished_tasks > 0:
                task = self.send_queue.get()

                self._send_message(task)

                self.send_queue.task_done()

                logger.debug(f"message sent to upstream. Remaining in queue: {self.send_queue.unfinished_tasks}")
            else:
                sleep(1)

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
        self.send_queue.join()
        self.running = False
        self.thread.join()
        logger.info("done")
