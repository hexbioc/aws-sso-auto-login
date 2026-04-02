import logging

logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

ch = logging.StreamHandler()
ch.setLevel(logging.DEBUG)
ch.setFormatter(logging.Formatter("%(asctime)s|%(name)s|%(levelname)s|(%(filename)s:%(lineno)d): %(message)s"))

logger.addHandler(ch)
