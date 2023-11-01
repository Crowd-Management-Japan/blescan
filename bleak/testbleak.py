import bleak
import asyncio

import time
import aiohttp
from datetime import datetime

from bleak.backends.bluezdbus.scanner import BleakScannerBlueZDBus

from config import Config as conf
from config import parse_ini


from digi.xbee.devices import XBeeDevice,RemoteXBeeDevice
from digi.xbee.models.address import XBee16BitAddress
from digi.xbee.exception import TransmitException,XBeeException,TimeoutException

from xbee import encode_data, decode_data

import json

MAC1 = "EC:96:18:3A:8E:D4"

URL = "http://www.claudiofeliciani.online/ble_system/get_count.php"

PORT = "/dev/ttyUSB0" # 42
PORT2 = "/dev/ttyUSB1" # 41
PORT3 = "/dev/ttyUSB2" # 44
BAUD_RATE = 9600

addr_16 = bytearray(b'\xff\xfe')
addr_64 = bytearray(b'\x00\x13\xa2\x00A\xd5.M')

addr_coord = bytearray(b'\x00\x00')


def receive_callback(message):
    print(f"received from {message.remote_device}: {message.data.decode()}")
    parsed = decode_data(message.data.decode())
    print(parsed)

def listen(port):

    with XBeeDevice(port, BAUD_RATE) as device:
        print(f"listening with device {device.get_64bit_addr()}")



async def main():

    controller = XBeeDevice(PORT, BAUD_RATE)
    controller.open()

    controller.add_data_received_callback(receive_callback)
    
    controller.close()
    controller.open()

    d44 = XBeeDevice(PORT3, BAUD_RATE)
    d44.open()

    d44.set_parameter('ID', b'\x00\x00\x00\x00\x00\x00\x00\x01')
    d44.set_parameter('CE', b'\x00')
    d44.set_parameter('NI', bytearray("44_C", 'utf8'))

    d44.write_changes()

    print(d44.get_pan_id())
    print(d44.get_parameter("ID"))
    print(d44.get_role())
    print(d44.get_protocol())
    print(d44.get_parameter("CE"))
    print(d44)


    print("-----")

    device = XBeeDevice(PORT2, BAUD_RATE)
    device.open()

    print(device)
    print(device.get_16bit_addr())
    print(device.get_role())

    print("-----")

    net = device.get_network()

    #net.start_discovery_process(deep=True)
    #while net.is_discovery_running():
    #    time.sleep(0.5)
    #print(net.get_devices()[0].get_16bit_addr())

    remote = net.discover_device("42_C")
    if remote is None:
        print("42_C not found")

    date = datetime.now().strftime("%Y%m%d")
    times = datetime.now().strftime("%H:%M:%S")

    data = {'device_id':45,'date':date,'time':times, 'count':20,'total':20,'rssi_avg':-50,'rssi_std':12,'rssi_min':-99,'rssi_max':2}
    
    #data = json.dumps(data).encode()
    data = encode_data(data)

    print(f"data: {data}")

    print(len(data))

    device.set_sync_ops_timeout(30)

    resp = ""

    try: 
        resp = device.send_data(remote, data)
    except TransmitException:
        pass

    print(resp)
    print("start scanning")

    net.start_discovery_process(deep=True)
    while net.is_discovery_running():
        time.sleep(0.5)
        
    for dev in net.get_devices():
        print(dev)

    print("scan finished")


if __name__ == "__main__":
    asyncio.run(main())