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

pip install -r requirements.txt

# somehow pyserial is installed with the current version but still there
# is some issue that we have to reinstall it to work.
yes | pip uninstall pyserial
pip install pyserial

blpy=`find .venv/ -name "bluepy-helper`

# needed to run bluepy without sudo
sudo setcap cap_net_raw+e $blpy
sudo setcap cap_net_admin+eip $blpy

echo -------- completed --------
echo -------- install systemd service --------

# install systemd service
service_file=`cat etc/service_template`
service=`echo ${service_file//BLESCAN_DIRECTORY/$directory}`
echo $service > etc/blescan.service
sudo cp -f etc/blescan.service /lib/systemd/system/
sudo systemctl enable blescan.service

# add crontab for daily restart for every night 1 am
(sudo crontab -l && echo "0 1 * * * reboot") | sudo crontab

echo -------- completed --------
echo -------- run blescan installation --------

# install_wrapper without parameter will make the local installation
python etc/install_wrapper.py

# finally reboot or state that user should reboot
echo -------- installation script finished --------
echo -------- please reboot the device --------