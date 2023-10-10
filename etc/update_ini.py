import configparser
import os

# Open INI file and get informations
filename = '/usr/local/etc/config.ini'
inifile = configparser.ConfigParser()
inifile.read(filename)
inisections = inifile.sections()

# Extract existing settings if available
serNum = inifile.get('USER','devID')

if 'mode' in inifile['MODE']:
    mode = int(inifile.get('MODE','mode'))
else:
    mode = 2

if 'minRSSI' in inifile['SETTINGS']:
    threshRSSI = int(inifile.get('SETTINGS','minRSSI'))
else:
    threshRSSI = -75
    
if 'threshRSSI' in inifile['SETTINGS']:
    threshRSSI = int(inifile.get('SETTINGS','threshRSSI'))
    
if 'BackupCopy' in inifile['SETTINGS']:
    backupCopy = int(inifile.get('SETTINGS','BackupCopy'))
else:
    backupCopy = 0
    
if 'macList' in inifile['SETTINGS']:
    macList = int(inifile.get('SETTINGS','macList'))
else:
    macList = 1

# Rewrite INI file
os.remove(filename)
config = configparser.ConfigParser()
config.optionxform = str
config['USER'] = {'devID': serNum}
config['MODE'] = {'mode': mode}
config['SETTINGS'] = {'threshRSSI': threshRSSI, 'backupCopy': backupCopy, 'macList': macList}

with open(filename, 'w') as inifile:
    config.write(inifile)
