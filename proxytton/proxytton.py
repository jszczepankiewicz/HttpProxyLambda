
import logging
import time
import os

import urllib.request
import urllib.parse
from urllib.error import HTTPError

log = logging.getLogger()
log.setLevel(logging.INFO)

target_url = 'https://api.exchangeratesapi.io/latest'
user_agent = 'Mozilla/5.0 (Windows NT 6.1; Win64; x64)'

# remote response single chunk size
CHUNKSIZE = 4096

# max allowed response size in bytes
RESPONSE_MAX_SIZE_BYTES = 100 * 1024

def response(message, status_code):
    return {
        'statusCode': str(status_code),
        'body': message,
        'headers': {
            'Content-Type': 'application/json',
            'Access-Control-Allow-Origin': '*'
        },
    }

def proxied_url():
    return os.getenv('PROXY_OVERRIDE_TARGET_URL') or target_url

def response_encoding(response):
    # should probably be changed to ASCII?
    return response.info().get_content_charset() or 'utf-8'

def lambda_handler(event, context):

    try:
        log.debug("Before remote site retrieval")
        startTime = time.time()

        request = urllib.request.Request(proxied_url())
        r = urllib.request.urlopen(request)

        buffer = b''

        while True:
            chunk = r.read(CHUNKSIZE)
            if not chunk:
                break

            buffer += chunk

        scanEndTime = time.time()
        log.info("Retrieved results in (ms): " + str((scanEndTime - startTime) * 1000))
        return response(buffer.decode(response_encoding(r)), r.getcode())
    except urllib.error.URLError as exception:
        log.error("Unexpected URLError while retrieving remote site: " + str(exception))
        return response("Unexpected URLError while retrieving remote site: " + str(exception), "502")
    except HTTPError as exception:
        log.error("Unexpected HTTPError while retrieving remote site: " + str(exception))
        return response("Unexpected HTTPError while retrieving remote site: " + str(exception), "502")