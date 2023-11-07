import configparser

class Config:

    id = 0
    url = ''

def read_config(path='./config.ini'):
    print(f"Parsing ini file {path}")
    inifile = configparser.ConfigParser()
    inifile.read(path)

    section = inifile["BASE"]

    Config.id = section.get('id')
    Config.url = section.get('url')

def read_last_updated(path='../bleak/config.ini'):
    try:
        inifile = configparser.ConfigParser()
        inifile.read(path)
        section = inifile["USER"]

        return int(section.get('last_updated', 0))
    except:
        return 0