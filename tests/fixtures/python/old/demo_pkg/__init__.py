"""Tiny fixture package used only in tests."""

TIMEOUT = 5
DEFAULT_RETRIES = 3

def request(url, timeout=5.0, retries=3):
    return url, timeout, retries

class Client:
    retries = 3

    def __init__(self, timeout=5.0, verify=True):
        self.timeout = timeout
        self.verify = verify
