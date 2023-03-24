import logging
import time


class UtcFormatter(logging.Formatter):
    converter = time.gmtime
