"""Tiny fixture package used only in tests (newer defaults)."""

TIMEOUT = 10
DEFAULT_RETRIES = 3

def request(url, timeout=10.0, retries=3):
    return url, timeout, retries

class Client:
    retries = 5

    def __init__(self, timeout=10.0, verify=True, backoff=0.2):
        self.timeout = timeout
        self.verify = verify
        self.backoff = backoff
