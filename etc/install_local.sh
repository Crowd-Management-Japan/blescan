#!/bin/bash

# install blescan on a local raspberry without any connection to some kind of backend
# this means that only blescan/config.ini is used for everything

directory=`pwd`

# add user to bluetooth group, such that blescan can be executed without sudo
sudo usermod -a -G bluetooth `whoami`


# install apt requirements
sudo apt install git python3-venv -y  


echo -------- creating python environment --------

python3 -m venv .venv
source .venv/bin/activate

# to avoid issues with wheels being removed from pywheels they are stored and installed locally
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_DIR="$(cd "$SCRIPT_DIR/.." && pwd)"
cd "$PROJECT_DIR"

WHEEL_DIR="$PROJECT_DIR/etc/wheels"

pip install --no-index --find-links "file://$WHEEL_DIR" -r requirements.txt

# somehow pyserial is installed with the current version but still there
# is some issue that we have to reinstall it to work.
yes | pip uninstall pyserial
pip install pyserial

blpy=`find .venv/ -name "bluepy-helper"`

# needed to run bluepy without sudo
sudo setcap cap_net_raw+e $blpy
sudo setcap cap_net_admin+eip $blpy

echo -------- completed --------
echo -------- install systemd services --------

# install systemd service for blescan
cp etc/blescan_service_template etc/blescan.service
sed "s|BLESCAN_DIRECTORY|$directory|g" etc/blescan_service_template > etc/blescan.service

sudo cp -f etc/blescan.service /lib/systemd/system/
sudo systemctl enable blescan.service

# add service deleting the restart counter at shutdown
cp etc/counter_reset_service_template etc/counter_reset.service
sed "s|BLESCAN_DIRECTORY|$directory|g" etc/counter_reset_service_template > etc/counter_reset.service

sudo cp -f etc/counter_reset.service /lib/systemd/system/
sudo systemctl enable counter_reset.service

# add crontab for daily reset:
# device is rebooted at 2 am (network connection can be slow for LTE dongles)
# service is rebooted at 3 am  (at this time LTE device will be operating)
echo -------- add crontab commands --------
CRON_REBOOT="0 2 * * * /sbin/shutdown -r now"
(sudo crontab -l | grep -Fxq "$CRON_REBOOT") || (sudo crontab -l; echo "$CRON_REBOOT") | sudo crontab -
CRON_RESTART="0 3 * * * systemctl restart blescan"
(sudo crontab -l | grep -Fxq "$CRON_RESTART") || (sudo crontab -l; echo "$CRON_RESTART") | sudo crontab -

echo -------- completed --------
echo -------- run blescan installation --------

# install_wrapper without parameter will make the local installation
python etc/install_wrapper.py

# finally reboot or state that user should reboot
echo -------- installation script finished --------
echo -------- please reboot the device --------
