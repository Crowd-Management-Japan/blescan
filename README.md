# blescan
Blescan is a software developed for raspberry pi's to gather information about crowd densities and pedestrian behaviour.

Its focus is to be flexible and easy to use for everbody, mainly scientist in the field of crowd management.

# How it works
Blescan basically uses the bluetooth LE technology (ble) to scan for nearby available devices (e.g. smartphones). 
This information will be collected and processed to be used for density estimation (if many devices were scanned, there are many smartphones thus many people).
Bluetooth technology is somehow limited in the range, but we can setup a grid of Raspberry Pi's running this software and observe movement of crowds, 
create live heatmaps of certain places or track specific devices (e.g. bluetooth beacons handed out to people (see privacy)).

For this, blescan consists of two modi, which work independently but can also run simultaneously.

## Mode 1: general scanning
In this mode, blescan scans for all available ble-devices that could be connected to.
This data can be filtered, for example setting a minimum threshold to reduce background noise of too far away devices.
After this, the data is saved locally, but can optionally also be sent to a server for live analysis. 
This happens automatically when a Raspberry Pi is configured in this way has an internet connection.  
To reduce costs, when supplying Raspi's with possible internet connections (we used UMTS with data sims), the devices can also build a zigbee network.
If this is set up correctly, all information will be sent to a subset of devices that have a possible uplink.

## Mode 2:
The second possible mode filters scanned devices on a given uuid. 
For this we used iBeacons, which can be configured with an app to send exactly the same data all the time. 
These beacons were handed out to customers of the location where the tracking should take place. 
They get briefed what these beacons are and that they are used for tracking and analysing the route and time spent at difference places of the facility.

Because of the long-term analysis the method used is a sliding window and if a beacon is detected more than N times in the last X seconds, it is considered present.
As soon as it is not present anymore, the data is saved with time entered and total staying time near the concrete device.
The values can be configured using the config file.

# Privacy
As this topic is about tracking people and analysing crowd densities, privacy is an important part to think about.
Luckily - or sadly, depending on your point of view - it is generally not possible to track people using bluetooth over a longer perion of time.
Modern smartphones have inbuilt privacy features that use randomized mac addresses when advertising themself with bluetooth. 
This means that 'different' devices, detected on two points in time at a different place, could be actually the same smartphone.

For this project this is not a big problem, since Mode 1 is about the pure amount of devices. 
It doesn't matter if a device suddenly disappeared and another device with a different mac address just popped up.
The total amount of detected devices stays the same and that is what this method is working on.

For Mode 2 it is a different thing, as it is based on tracking.
Since it does not work 'in secret' by detecting smartphones, you have to give special devices (namely beacons) to people.
These beacons are for this purpose and do not change their mac address over time. 
It is always the same.
They have to be handed out to people, so they know that they get something that has to do with an experiment.
Is is important and your responsibility to brief them according to privacy laws in your country!

# How to use
TODO
