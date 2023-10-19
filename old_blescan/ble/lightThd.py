import time
import os
import threading

class LightThd(threading.Thread):

    global on
    global off
    on = "1"
    off= "0"

    def __init__(self):
        super().__init__()
        self.terminated = False
        self.mode = 0

    def isOff(self):
        self.terminated = True

    def isOn(self):
        self.start()

    def run(self):
        self.lightLed()
    def setMode(self,mode):
        self.mode = mode


    def lightLed(self):
        # 緑LEDを点滅させる
        with open ("/sys/class/leds/led0/brightness","w") as ledfile:
            if self.mode == 0:
                while not self.terminated:
                        ledfile.write(on)
                        ledfile.flush()
                        time.sleep(0.2)
                        ledfile.write(off)
                        ledfile.flush()
                        time.sleep(6)
            else:
                while not self.terminated:
                        ledfile.write(on)
                        ledfile.flush()
                        time.sleep(0.2)
                        ledfile.write(off)
                        ledfile.flush()
                        time.sleep(0.1)
                        ledfile.write(on)
                        ledfile.flush()
                        time.sleep(0.2)
                        ledfile.write(off)
                        ledfile.flush()
                        time.sleep(6)


    @staticmethod
    def writeAppeal():
        with open ("/sys/class/leds/led1/brightness","w") as ledfile:
            ledfile.write(on)
            ledfile.flush()
            time.sleep(1)
        with open ("/sys/class/leds/led1/brightness","w") as ledfile:
            ledfile.write(off)
            ledfile.flush()
