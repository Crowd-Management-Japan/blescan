import shutil
import configparser
import csv

# Get device number
filename = '/usr/local/etc/config.ini'
inifile = configparser.ConfigParser()
inifile.read(filename)
deviceID = int(inifile.get('USER','devID'))

# Define constants for DHCP file
settingsDHCP = ["interface usb0","metric 200","static ip_address=192.168.0.10/24",
               "static routers=192.168.0.1","static domain_name_servers=192.168.0.1"]

# Read WiFi settings
with open('/usr/local/etc/wifi_settings.csv', newline='') as csvfile:
    wifiSettings = list(csv.reader(csvfile))

# Read DHCP config file
dhcpFile = open('/etc/dhcpcd.conf', 'r')
fileLines = dhcpFile.readlines()
dhcpFile.close()

# Check for starting lines
startWLAN, startETH, startUSB, count = 0, 0, 0, 0
for line in fileLines:
    if "interface wlan0" in line.strip():
        startWLAN = count
    if "interface eth0" in line.strip():
        startETH = count
    if "metric 201" in line.strip():
        startETH += 1
    count += 1

# Rewrite file
dhcpFile = open('/etc/dhcpcd.conf', 'w')
for i in range(0, startWLAN-1):
    dhcpFile.writelines(fileLines[i])
dhcpFile.writelines("\ninterface wlan0\nmetric 202\n")
dhcpFile.writelines("static ip_address=" + wifiSettings[0][1] + ".2" + "{:02d}".format(deviceID) + "/24\n")
dhcpFile.writelines("static routers=" + wifiSettings[1][1] + "\n")
dhcpFile.writelines("static domain_name_servers=" + wifiSettings[1][1] + "\n\n")
dhcpFile.writelines("interface eth0\nmetric 201\n")
for i in range(startETH+1, startETH+4):
    dhcpFile.writelines(fileLines[i])
dhcpFile.writelines("\n")
for i in range(0,5):
    dhcpFile.writelines(settingsDHCP[i] + "\n")
dhcpFile.close()

# Open config file and check for option
configFile = open('/boot/config.txt', 'r')
fileLines, check = configFile.readlines(), 0
configFile.close()
for line in fileLines:
    if "max_usb_current=1" in line.strip():
        check = 1

# Rewrite file
if check==0:
    configFile = open('/boot/config.txt', 'w')
    for line in fileLines:
        configFile.writelines(line)
    configFile.writelines("\nmax_usb_current=1\n")
    configFile.close()

# Copy files for interfaces and rc.local
shutil.copyfile('/usr/local/etc/interfaces', '/etc/network/interfaces')
shutil.copyfile('/usr/local/etc/rc.local', '/etc/rc.local')
