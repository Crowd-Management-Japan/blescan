import configparser
import sys

inifile=configparser.ConfigParser()
inifile.read('/usr/local/etc/config.ini')

mode=int(inifile.get('MODE','mode'))

if mode == 0:
    sys.exit(0)
elif mode == 1:
    sys.exit(1)
elif mode == 2:
    sys.exit(2)
else:
    sys.exit(255)
