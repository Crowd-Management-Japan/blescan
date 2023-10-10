import time
import serial
from micropyGPS import MicropyGPS

def main():
    uart = serial.Serial('/dev/serial0', 9600, timeout = 10)
    my_gps = MicropyGPS(9, 'dd')

    tm_last = 0
    #while True:
    for i in range(1):
        sentence = uart.readline()
        if len(sentence) > 0:
            for x in sentence:
                if 10 <= x <= 126:
                    stat = my_gps.update(chr(x))
                    if stat:
                        tm = my_gps.timestamp
                        tm_now = (tm[0] * 3600) + (tm[1] * 60) + int(tm[2])
                        if (tm_now - tm_last) >= 10:
                            print('=' * 20)
                            print(my_gps.date_string(), tm[0], tm[1], int(tm[2]))
                            print("latitude:", my_gps.latitude[0], ", longitude:", my_gps.longitude[0])

                            if my_gps.longtitude[0]>0:
                                return True
if __name__ == "__main__":
    main()
