
import logging
import time
import os

import urllib.request
import urllib.parse
from urllib.error import HTTPError

log = logging.getLogger('proxy')
log.setLevel(logging.DEBUG)

target_url = 'https://dog-facts-api.herokuapp.com/api/v1/resources/dogs?number=1'

# headers(case in-sensitive) not proxied see https://www.freesoft.org/CIE/RFC/2068/143.htm
HOP_BY_HOP_HEADERS = {'connection', 'keep-alive', 'public', 'proxy-authenticate', 'transfer-encoding', 'upgrade', 'host'}

# remote response single chunk size
CHUNKSIZE = 4096

# max allowed response size in bytes
RESPONSE_MAX_SIZE_BYTES = 100 * 1024

class ApiProxy:
    def __init__(self, request=None):
        self.request = request

    def __request(self):
        return self.request or urllib.request.Request("https://localhost")

    def __response(self, message, status_code, content_type='text/plain'):
        return {
            'statusCode': str(status_code),
            'body': message,
            'headers': {
                'Content-Type': str(content_type),
                'Access-Control-Allow-Origin': '*'
            },
        }

    def __proxied_url(self):
        target = os.getenv('PROXY_OVERRIDE_TARGET_URL') or target_url
        log.debug('setting target url: ' + target)
        return target

    def __response_encoding(self, response):
        # should probably be changed to ASCII?
        return response.info().get_content_charset() or 'utf-8'

    def __proxy_headers(self, request, event):
        for i in event['headers']:
            if i.lower() in HOP_BY_HOP_HEADERS:
                continue

            log.debug('proxying header [' + str(i) + ': ' + event['headers'][i] + ']')
            request.add_header(i, event['headers'][i])

    def process_event(self, event):
        try:
            log.debug("Before remote site retrieval")
            startTime = time.time()

            request = self.__request()
            request.full_url = self.__proxied_url()
            self.__proxy_headers(request, event)

            r = urllib.request.urlopen(request)

            buffer = b''

            while True:
                chunk = r.read(CHUNKSIZE)
                if not chunk:
                    break

                buffer += chunk

            scanEndTime = time.time()
            http_message = r.info()
            log.info("Retrieved results in (ms): " + str((scanEndTime - startTime) * 1000))
            log.debug("Response headers: " + str(r.headers))
            return self.__response(buffer.decode(self.__response_encoding(r)), r.getcode(), 'application/json')
        except urllib.error.URLError as exception:
            log.error("Unexpected URLError while retrieving remote site: " + str(exception))
            return self.__response("Unexpected URLError while retrieving remote site: " + str(exception), "502")
        except HTTPError as exception:
            log.error("Unexpected HTTPError while retrieving remote site: " + str(exception))
            return self.__response("Unexpected HTTPError while retrieving remote site: " + str(exception), "502")


def lambda_handler(event, context):
    return ApiProxy().process_event(event)
