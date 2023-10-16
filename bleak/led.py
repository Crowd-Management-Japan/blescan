import threading
from time import sleep

class LED:

    """
    Setting up the LED. 
    @param led_code refers to the path specified in the raspberry where the trigger and brightness file can be found. e.g. 'led0' for the green led.
    """
    def __init__(self, led_code):
        self.trigger = f"/sys/class/leds/{led_code}/trigger"
        self.brightness = f"/sys/class/leds/{led_code}/brightness"
        with open(self.trigger, 'w') as file:
            file.write("none")
            # TODO undo when deconstructing

    def on(self):
        with open(self.brightness, 'w') as file:
            file.write("1")
    
    def off(self):
        with open(self.brightness, 'w') as file:
            file.write("0")

def LED_ERROR(green: LED, red: LED):
    green.off()
    red.on()

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

class LEDCommunicator:

    def __init__(self):
        self.running = False
        self.code = LED_RUNNING
        self.green = LED('led0')
        self.red = LED('led1')
        pass

    def blink_blocking(self):
        while self.running:
            function = self.code
            function(self.green, self.red)
        print("thread finishing")

    def start_in_thread(self):
        if self.running:
            print("blinking thread already started")
            return
        
        self.running = True

        self.thread = threading.Thread(target=self.blink_blocking)
        self.thread.start()


    def stop(self):
        self.running = False