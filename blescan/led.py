import threading
from time import sleep
from enum import IntEnum
import logging

logger = logging.getLogger('blescan.LED')

class LED:
    """
    Setting up the LED. 
    @param led_code refers to the path specified in the raspberry where the trigger and brightness file can be found. e.g. 'led0' for the green led.
    """
    def __init__(self, led_code):
        self.trigger = f"/sys/class/leds/{led_code}/trigger"
        self.brightness = f"/sys/class/leds/{led_code}/brightness"
        try:
            with open(self.trigger, 'w') as file:
                file.write("none")
        except FileNotFoundError:
            logger.error("Cannot find LEDs. Disabling LED functionality")
            self.on = lambda: None
            self.off = lambda: None
        except PermissionError:
            logger.error("Missing permission for controlling LEDs. Disabling LED functionality")
            self.on = lambda: None
            self.off = lambda: None
            

    def on(self):
        with open(self.brightness, 'w') as file:
            file.write("1")
    
    def off(self):
        with open(self.brightness, 'w') as file:
            file.write("0")

def LED_ERROR(green: LED, red: LED):
    green.off()
    red.on()

def LED_SETUP(green: LED, red: LED):
    green.off()
    red.on()
    sleep(.25)
    green.on()
    red.off()
    sleep(.25)

def LED_RUNNING(green: LED, red: LED):
    red.off()
    green.on()
    sleep(.25)
    green.off()
    sleep(.25)
    green.on()
    sleep(.25)
    green.off()
    sleep(1)

def _LED_FAST(led:LED):
    led.on()
    sleep(.25)
    led.off()
    sleep(.25)
    
def _LED_SLOW(led:LED):
    led.on()
    sleep(.75)
    led.off()
    sleep(.75)

def LED_GREEN_FAST(green: LED, red: LED):
    _LED_FAST(green)

def LED_GREEN_SLOW(green: LED, red: LED):
    _LED_SLOW(green)

def LED_RED_FAST(green: LED, red: LED):
    _LED_FAST(red)

def LED_RED_SLOW(green: LED, red: LED):
    _LED_SLOW(red)

def LED_BOTH_FAST(green: LED, red: LED):
    green.on()
    red.on()
    sleep(.25)
    green.off()
    red.off()
    sleep(.25)

def LED_BOTH_SLOW(green: LED, red: LED):
    green.on()
    red.on()
    sleep(.75)
    green.off()
    red.off()
    sleep(.75)

def LED_GF_RS(green: LED, red: LED):
    red.on()
    green.on()
    sleep(.25)
    green.off()
    sleep(.25)
    green.on()
    sleep(.25)
    green.off()
    red.off()
    sleep(.25)
    green.on()
    sleep(.25)
    green.off()
    sleep(.25)

def LED_GS_RF(green: LED, red: LED):
    LED_GF_RS(red, green)


class LEDState(IntEnum):
    INTERNET_STACKING = 1
    ZIGBEE_STACKING = 2
    SETUP = 4
    NO_INTERNET_CONNECTION = 8
    NO_ZIGBEE_CONNECTION = 16


def get_led_function(state) -> lambda g,r:None :

    enabled = [s for s,v in state.items() if v]
    sum = 0
    for state in enabled:
        sum += state


    if sum == 0:
        return LED_RUNNING
    
    if LEDState.SETUP in enabled:
        # ignore other errors when still in setup
        return LED_SETUP

    if sum in [1, 9]:
        return LED_GREEN_FAST
    if sum in [2, 18]:
        return LED_RED_FAST
    if sum in [3, 11, 19]:
        return LED_BOTH_FAST
    if sum == 8:
        return LED_GREEN_SLOW
    if sum == 16: 
        return LED_RED_SLOW
    if sum == 24: 
        return LED_BOTH_SLOW
    if sum in [10, 26]:
        return LED_GS_RF
    if sum in [17, 25]: 
        return LED_GF_RS
    
    return LED_ERROR

class LEDCommunicator:
    """
    This Class functions as a communicator towards the outside world. 
    It starts a daemon thread that uses both LEDs on the raspberry to send information
    """

    def __init__(self):
        self.running = False
        self.code = LED_SETUP
        self._states = {
            value: False for value in LEDState
        }
        self._states[LEDState.SETUP] = True
        self._state_changed = True
        self.setup()

    def setup(self):
        self.green = LED('led0')
        self.red = LED('led1')


    def blink_blocking(self):
        function = self.code
        while self.running:
            if self._state_changed:
                function = get_led_function(self._states)
                self._state_changed = False

            function(self.green, self.red)
        logger.info("thread finishing")

    def start_in_thread(self):
        logger.info("--- starting LED thread ---")
        if self.running:
            logger.error("blinking thread already started")
            return
        
        self.running = True

        self.thread = threading.Thread(target=self.blink_blocking, daemon=True)
        self.thread.start()

    def enable_state(self, state):
        if self._states.get(state, False):
            return
        self._states[state] = True
        self._state_changed = True

    def disable_state(self, state):
        if not self._states.get(state, False):
            return
        self._states[state] = False
        self._state_changed = True

    def stop(self):
        logger.info("--- shutting down LED thread ---")
        if self.running == False:
            return
        self.running = False
        self.thread.join()
        logger.info("done")