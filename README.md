# Blescan
Blescan is a software developed for raspberry pi's to gather information about crowd densities and pedestrian behaviour.

Its focus is to be flexible and easy to use for everbody, mainly scientists in the field of crowd management.

# How it works
Blescan basically uses the bluetooth LE technology (ble) to scan for nearby available devices (e.g. smartphones). 
This information will be collected and processed to be used for density estimation (if many devices were scanned, there are many smartphones and thus many people).
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

## Mode 2: beacon detection annd tracking
The second possible mode filters scanned devices on a given uuid. 
For this we used iBeacons, which can be configured with an app to send exactly the same data all the time. 
These beacons were handed out to customers of the location where the tracking should take place. 
They get briefed what these beacons are and that they are used for tracking and analysing the route and time spent at difference places of the facility.

Because of the long-term analysis the method used is a sliding window and if a beacon is detected more than N times in the last X seconds, it is considered present.
As soon as it is not present anymore, the data is saved with time entered and total staying time near the concrete device.
The values can be configured using the config file.

# Privacy
As this topic is about tracking people and analysing crowd densities, privacy is an important part to think about.
Luckily - or sadly, depending on your point of view - it is generally not possible to track people using bluetooth over a long period of time.
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

We use this project for around 50 raspberry devices. To make things easier we created the [blescan-backend](https://github.com/Crowd-Management-Japan/blescan-backend).
It provides a simple API and webinterface for easy setup and following live-data.
The setup process is more focused on working with this backend.

## single raspberry 
Clone the repository to the raspberry.
When using the productive version, run the `etc/install_script.sh`. It will also install a service and add it to autostart.  

Doing manually:
- (optional) create python environment
- install requirements `pip install -r requirements.txt`
- edit `blescan/config.ini` as you need
- run `blescan/main.py`

## Using multiple raspberry pi's
When using multiple raspi's it might be good to have a look at the [blescan-backend](https://github.com/Crowd-Management-Japan/blescan-backend).

### Installation
With the backend the installation process is much easier. First, install the backend and make sure that it is set up correctly (look that the install_script uses the correct ip-address of the server).
Then, inside the raspberry just run `curl <ip:port>/setup/install_<id> > install.sh` where id is the id of the raspberry used (needed when uploading the data later, just choose a number).
This will download a script with the full setup and installation.
After a reboot the software will start automatically in the background. Check with `sudo systemctl status blescan.service`.

Tip:
If you setup a static IP (for example in `/etc/dhcpcd.conf`) you can use the endpoint `/setup/install_ip` to automatically detect the device id by the last two digits of the IP address.
Note, that this only works when running the backend in the local network.

### Running
When running the backend, you should not run `blescan/main.py` directly. Instead run `./etc/start.sh`. It will start a wrapper first, that communicates with the backend, downloads the latest config and then starts blescan based on this config.

# Contributing
Feel free to open Issues, or resolve them and open merge requests.

# Suggested references
If you found this project useful and/or it contributed to your research, we would be grateful if you could cite this work:
Tanida, S., Feliciani, C., Jia, X., Kim, H., Aikoh, T., & Nishinari, K. (2024). Investigating the congestion levels on a mesoscopic scale during outdoor events. Journal of Disaster Research, 19(2), 347-358.
The same work may be also useful if you want to learn more about scienficic applications to our software and/or case studies where the software was employed. Please be also aware that the work above used an early version of this code and some parameters may be different to what used here.
