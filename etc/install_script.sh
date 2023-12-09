# install blescan on a local raspberry
# create python virtual environment and add service to /lib/systemd


# add user to bluetooth group, such that blescan can be executed without sudo
sudo usermod -a -G bluetooth `whoami`


python3 -m venv .venv
source .venv/bin/activate

pip install -r requirements.txt

echo -------- running install.py -------

python etc/install.py $id $server_url

# add to autostart

sudo cp etc/blescan.service /lib/systemd/system/
sudo systemctl enable blescan.service

# finally reboot or state that user should reboot