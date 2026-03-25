import logging
import sys

# Structured log format
LOG_FORMAT = "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
logging.basicConfig(level=logging.INFO, stream=sys.stdout, format=LOG_FORMAT)

logger = logging.getLogger("payu-processing-service")
