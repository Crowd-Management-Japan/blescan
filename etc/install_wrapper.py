import os
import sys


EMPTY_CONFIG_PATH = 'etc/empty_wrapper.conf'
WRAPPER_CONFIG_PATH = 'etc/wrapper.conf'


def main(argv):

    local = len(argv) == 1

    id = 0 if local else argv[1]
    url = "" if local else argv[2]

    setup_config_file(id, url, local)


def setup_config_file(id: int, url: str, local:bool=False):
    text = ''

    with open(EMPTY_CONFIG_PATH, 'r') as empty:
        text = empty.read()

    text = text.replace('$LOCAL', '1' if local else '0')
    text = text.replace('$ID', str(id))
    text = text.replace('$URL', url)

    with open(WRAPPER_CONFIG_PATH, 'w') as conf:
        conf.write(text)


if __name__ == '__main__':
    main(sys.argv)