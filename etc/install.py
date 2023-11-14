import os
import sys


EMPTY_CONFIG_PATH = 'etc/empty_wrapper.conf'
WRAPPER_CONFIG_PATH = 'etc/wrapper.conf'


def main(argv):
    id = argv[1]
    url = argv[2]

    setup_config_file(id, url)


def setup_config_file(id, url):
    text = ''

    with open(EMPTY_CONFIG_PATH, 'r') as empty:
        text = empty.read()

    text = text.replace('$ID', id)
    text = text.replace('$URL', url)

    with open(WRAPPER_CONFIG_PATH, 'w') as conf:
        conf.write(text)


if __name__ == '__main__':
    main(sys.argv)