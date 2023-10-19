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

if 'TimeShift' in inifile['SETTINGS']:
    timeShift = float(inifile.get('SETTINGS','TimeShift'))
else:
    timeShift = 5.0

if 'minRSSI' in inifile['SETTINGS']:
    minRSSI = int(inifile.get('SETTINGS','minRSSI'))
else:
    minRSSI = -70
    
if 'BackupCopy' in inifile['SETTINGS']:
    backupCopy = int(inifile.get('SETTINGS','BackupCopy'))
else:
    backupCopy = 0

# Rewrite INI file
os.remove(filename)
config = configparser.ConfigParser()
config.optionxform = str
config['USER'] = {'devID': serNum}
config['MODE'] = {'mode': mode}
config['SETTINGS'] = {'TimeShift': timeShift, 'minRSSI': minRSSI, 'BackupCopy': backupCopy}

with open(filename, 'w') as inifile:
    config.write(inifile)
