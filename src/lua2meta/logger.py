import logging
import sys

__all__ = ["logger"]

logger = logging.getLogger("lua2meta")
logger.setLevel(logging.INFO)

formatter = logging.Formatter('%(levelname)s: %(message)s')
console_handler = logging.StreamHandler(sys.stdout)

console_handler.setFormatter(formatter)
logger.addHandler(console_handler)
