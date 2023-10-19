
from storage import Storage

class Upstream(Storage):

    def __init__(self, url):
        self.url = url
