
from storage import prepare_row_data_summary
from datetime import datetime
from typing import List, Dict, Union
import requests
from time import sleep
import logging
import util
from config import Config
from led import LEDState, LEDCommunicator
import multiprocessing as mp

logger = logging.getLogger('blescan.Network')

DATE_FORMAT = "%Y-%m-%d %H:%M:%S"

INTERNET_STACKING_THRESHOLD = 3
INTERNET_QUEUE_SIZE = 1000

class InternetController:
    """
    The internet controller manages the internet connection.
    It can be started in a separated process by calling the `start()`-method.
    After doing this, messages can be enqueue by calling `enqueue_message(message)`.
    These messages will get sent to the specified `url` endpoint.
    When also given a LEDCommunicator, this instance will give information about its current state.

    Stop the process by calling `stop()`. This will terminate the loop safely, with trying to send all
    enqueued messages before exiting.
    """
    def __init__(self, count_url='', transit_url='', led_communicator:LEDCommunicator=None):
        self.led_communicator: LEDCommunicator = led_communicator

        # counting function
        self.count_url: str = count_url
        self.count_queue = mp.Queue()

        # transit function
        self.transit_url: str = transit_url
        self.transit_queue = mp.Queue()

        self.process: mp.Process
        self.ready: bool = False
        self.running: bool = False

    def set_count_url(self, url:str):
        self.count_url = url

    def set_transit_url(self, url:str):
        self.transit_url = url

    def set_led_communicator(self, communicator: LEDCommunicator):
        self.led_communicator = communicator

    def start(self):
        """
        Start a process as a daemon. Only has effect, if the instance is not running yet.
        """
        if self.running:
            logger.error("Internet process already running")
            return

        self.running = True
        logger.info("--- starting Internet process ---")

        self.process = mp.Process(target=self._run, daemon=True)
        self.process.start()
        logger.debug("internet process started")

    def stop(self):
        """
        Stop the process and terminate safely. Try to send remaining messages before exiting
        """
        if not self.running:
            return
        logger.debug("internet process stop call")
        self.running = False
        self.process.join()
        logger.info("--- Internet process shut down ---")

    def enqueue_count_message(self, message: str):
        self._enqueue_message(self.count_queue, message, 'count')

    def enqueue_transit_message(self, message: str):
        self._enqueue_message(self.transit_queue, message, 'transit')

    def _enqueue_message(self, queue: mp.Queue, message: str, queue_name: str):
        """
        Enqueue a message to be sent.
        If the Queue is already full, older data will be dropped to add this message
        """
        if queue.qsize() >= INTERNET_QUEUE_SIZE:
            logger.warn(f"internet {queue_name} queue full. Dropping old data")
            queue.get()
            queue.task_done()
        queue.put(message)

        logger.debug(f"adding message to internet {queue} queue. size: {queue.qsize()}")

    def _run(self):
        """
        Private method that is actually executed as a process.
        """
        count_message = None
        transit_message = None

        while self.running:
            if Config.led:
                state = self.count_queue.qsize() > INTERNET_STACKING_THRESHOLD or self.transit_queue.qsize() > INTERNET_STACKING_THRESHOLD
                self._set_state(LEDState.INTERNET_STACKING, state)

            count_message = self._process_queue(self.count_url, self.count_queue, count_message, "count")
            transit_message = self._process_queue(self.transit_url, self.transit_queue, transit_message, "transit")

            if count_message is None and transit_message is None:
                sleep(0.1)

        logger.debug("internet process stopping safely. Send remaining messages")
        self._send_remaining_message(self.count_url, self.count_queue, "count")
        self._send_remaining_message(self.transit_url, self.transit_queue, "transit")
        logger.debug("internet process finished")

    def _process_queue(self, url: str, queue: mp.Queue, message: Union[Dict, None], queue_name: str) -> Union[Dict, None]:
        if message is not None:
            success = self._send_message(message, url)
            logger.debug(f"internet sending success for {queue_name}: {success} ")
            if success:
                if Config.led:
                    self._set_state(LEDState.NO_INTERNET_CONNECTION, False)
                return None
            else:
                if Config.led:
                    self._set_state(LEDState.NO_INTERNET_CONNECTION, True)
                sleep(2)
                return message

        elif queue.qsize() > 0:
            logger.debug(f"retrieving next internet message from {queue_name} queue")
            return queue.get()
        return None


    def _send_message(self, message: Dict, url: str, timeout=5) -> bool:
        """
        Try to send a single message to the upstream.
        Return true if sending process was successfull.
        """
        logger.debug(f"sending internet message to {url} ...")
        try:
            response = requests.post(url, json=message, timeout=timeout)
            return response.status_code == 200
        except Exception as e:
            logger.error(f"Error while sending message to internet: {e}")
            return False

    def _send_remaining_message(self, url: str, queue: mp.Queue, queue_name: str):
        while queue.qsize() > 0:
            logger.debug(f"internet remaining in {queue_name} queue: {queue.qsize()}")
            message = queue.get()
            self._send_message(message, url, timeout=0.5)

    def _set_state(self, state: LEDState, value: bool):
        if self.led_communicator is not None:
            self.led_communicator.set_state(state, value)


class InternetStorage:
    """
    Storage adapter for internet connection.

    Implements the method `save_from_count` to be seen as storage from the count functionality.

    It brings the data in the right format and prepares it to send
    """

    def __init__(self, controller: InternetController):
        self.com = controller

    def save_count(self, id: int, timestamp: datetime, scans: int, scantime: float, rssi_list: List, instantaneous_counts: List, static_list: List):


        time_format = util.format_datetime_network(timestamp)
        old_format = util.format_datetime_old(timestamp)

        # return value is "ID,Time,Scans,Scantime,Tot.all,Tot.close,Inst.all,Inst.close,Stat.all,Stat.close,Avg RSSI,Std RSSI,Min RSSI,Max RSSI,Stat.ratio,Lat,Lon"
        summary = prepare_row_data_summary(id, time_format, scans, scantime, rssi_list, instantaneous_counts, static_list)
        # {'id': '45', 'date': '20231020', 'time': '104000', 'scans': 8, 'scantime': '9.126',
        #  'tot_all': '26', 'tot_close': '26', 'inst_all': '26', 'inst_close': '26', 'stat_all': '26', 'stat_close': '26',
        #  'rssi_avg': '-93.615', 'rssi_std': '3.329', 'rssi_min': '-99', 'rssi_max': '-85',
        #  'rssi_thresh': -70, 'stat_ratio': '0.7', 'lat': '-3.52842', 'lon': '-15.52842'}

        # %Y%m%d,%H%M%S
        date = datetime.now().strftime("%Y%m%d")

        params = {'id':id,
                  'timestamp':time_format,
                  'date':date,
                  'time':old_format.replace(':', ''),
                  'scans': scans,
                  'scantime':scantime,
                  'tot_all':summary[4],
                  'tot_close':summary[5],
                  'inst_all':summary[6],
                  'inst_close':summary[7],
                  'stat_all':summary[8],
                  'stat_close':summary[9],
                  'rssi_avg':summary[10],
                  'rssi_std':summary[11],
                  'rssi_min':summary[12],
                  'rssi_max':summary[13],
                  'rssi_thresh':Config.Counting.rssi_close_threshold,
                  'static_ratio':Config.Counting.static_ratio,
                  'latitude':Config.latitude,
                  'longitude':Config.longitude
                  }

        self.com.enqueue_count_message(params)

    def save_transit():
        pass
