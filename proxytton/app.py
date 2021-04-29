import base64
import json
import logging
import time
import os
import boto3

import urllib.request
import urllib.parse
from urllib.error import HTTPError

log = logging.getLogger('proxy')
log.setLevel(logging.DEBUG)

# headers(case in-sensitive) not proxied see https://www.freesoft.org/CIE/RFC/2068/143.htm
HOP_BY_HOP_HEADERS = {'connection', 'keep-alive', 'public', 'proxy-authenticate', 'transfer-encoding', 'upgrade',
                      'host'}

OS_PROXY_TARGET_HOST_ENV_NAME = 'PROXY_TARGET_HOST'

ENV_PLAINTEXT_USER = 'PROXY_BASIC_PLAIN_USER'
ENV_PLAINTEXT_PASS = 'PROXY_BASIC_PLAIN_PASS'

SUPPORTED_METHODS = {'GET', 'POST'}

sm_client = boto3.client('secretsmanager')

class ApiProxy:

    def __init__(self, request=None):
        self.request = request

    def __add_basic_auth(self, username, password, request):
        b64auth = base64.b64encode(("%s:%s" % (username, password)).encode("ascii"))
        request.add_header("Authorization", "Basic %s" % b64auth.decode("ascii"))
        return

    def __authorize_downstream(self, request):

        username = None
        password = None

        #   check if credentials provided through plaintext
        if ENV_PLAINTEXT_USER in os.environ:
            log.info("Detected simple credentials injection")
            username = os.getenv(ENV_PLAINTEXT_USER)
            password = os.getenv(ENV_PLAINTEXT_PASS)

        if username is not None:
            log.info("Authorization: Basic will be used")
            self.__add_basic_auth(username, password, request)

        return

    def __http_method(self):
        return self.http_method

    def __proxied_url(self, path=''):

        if OS_PROXY_TARGET_HOST_ENV_NAME in os.environ:
            target_host = os.getenv(OS_PROXY_TARGET_HOST_ENV_NAME)
            target_url = 'https://' + target_host + path
            log.debug('Setting target url: ' + target_url)
            return target_url
        else:
            raise Exception(OS_PROXY_TARGET_HOST_ENV_NAME + ' not set in environment variables')

    def __request(self, path, method):
        return self.request or urllib.request.Request(self.__proxied_url(path), method=method)

    def __strip_hop_headers(self, all_headers):

        if all_headers is None:
            log.debug('Empty response headers')
            return dict()

        end_headers = dict()

        for key in dict(all_headers.items()).keys():
            if key.lower() in HOP_BY_HOP_HEADERS:
                log.debug('Striping response header: ' + key)
            else:
                log.debug('Adding response header: ' + key)
                end_headers[key] = all_headers[key]

        return end_headers

    def __response(self, message, status_code, headers=None):

        response = {
            'statusCode': str(status_code),
            'body': message,
            'headers': self.__strip_hop_headers(headers),
        }

        return response

    def __response_encoding(self, response):
        # should probably be changed to ASCII?
        return response.info().get_content_charset() or 'utf-8'

    def __add_default_headers(self, request):
        request.add_header('User-agent', 'lambda-proxy')
        request.add_header('Accept', '*/*')
        return

    def __proxy_headers(self, request, event):

        if 'headers' not in event.keys():
            log.warning('Request without headers, adding default accept all header')
            self.__add_default_headers(request)
            return

        if len(event['headers']) == 0:
            log.warning('Request with empty headers, adding default accept all header')
            self.__add_default_headers(request)
            return

        for i in event['headers']:
            if i.lower() in HOP_BY_HOP_HEADERS:
                continue

            log.debug('proxying header [' + str(i) + ': ' + event['headers'][i] + ']')
            request.add_header(i, event['headers'][i])

    def __request_path(self, event):
        path = event['path']
        log.debug('URL path: ' + path)
        return path

    def __request_method(self, event):

        method = event['httpMethod']

        if method not in SUPPORTED_METHODS:
            raise Exception('Unsupported HTTP method: ' + method)

        self.http_method = method
        log.debug('HTTP method: ' + method)
        return method


    def __handle_request_body(self, request, event):
        #   TODO: add isbase64 conditional check
        if event['httpMethod'] == 'POST':

            message_bytes = base64.b64decode(event['body'])
            #   TODO: add content type detection
            message = message_bytes.decode('utf-8')
            log.debug('Proxying POST body: ' + message)
            request.data = message_bytes
            return


    def process_event(self, event):
        try:
            log.debug("Before remote site retrieval")
            request_start = time.time()

            request = self.__request(self.__request_path(event), self.__request_method(event))

            self.__handle_request_body(request, event)
            self.__authorize_downstream(request)
            self.__proxy_headers(request, event)

            r = urllib.request.urlopen(request)

            buffer = r.read()

            request_end = time.time()

            log.info("Retrieved results in (ms): " + str((request_end - request_start) * 1000))
            log.debug("Response headers: " + str(r.headers))
            return self.__response(buffer.decode(self.__response_encoding(r)), r.getcode(), r.headers)
        except urllib.error.URLError as exception:
            log.error("Unexpected URLError while retrieving remote site: " + str(exception))
            return self.__response("Unexpected URLError while retrieving remote site: " + str(exception), "502")
        except HTTPError as exception:
            log.error("Unexpected HTTPError while retrieving remote site: " + str(exception))
            return self.__response("Unexpected HTTPError while retrieving remote site: " + str(exception), "502")


def lambda_handler(event, context):
    return ApiProxy().process_event(event)
