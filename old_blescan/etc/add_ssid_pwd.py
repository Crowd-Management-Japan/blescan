import csv

# Read CSV file with SSIDs and passwords
with open('/usr/local/etc/wifi_ssid_pwd.csv', newline='') as csvfile:
    wifiData = list(csv.reader(csvfile))

# Write initial lines
wpaFile = open('/etc/wpa_supplicant/wpa_supplicant.conf', 'w')
wpaFile.writelines("ctrl_interface=DIR=/var/run/wpa_supplicant GROUP=netdev\n")
wpaFile.writelines("update_config=1\ncountry=JP\n\n")

# Write part with passwords
for i in range(0, len(wifiData)):
    wpaFile.writelines("network={\n")
    wpaFile.writelines("\tssid=\"" + wifiData[i][0] + "\"\n")
    wpaFile.writelines("\tpsk=\"" + wifiData[i][1] + "\"\n")
    wpaFile.writelines("}\n")
wpaFile.close()
