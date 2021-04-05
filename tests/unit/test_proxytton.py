import json
import logging
import os
import sys
import unittest
import urllib
import app
from unittest import TestCase

from unittest.mock import call, patch

ENVIRONMENT_VAR_TARGET_URL = 'PROXY_OVERRIDE_TARGET_URL'
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"


class ProxyTest(TestCase):

    def setUpTargetUrl(self, url):
        os.environ[ENVIRONMENT_VAR_TARGET_URL] = url

    def lambdaEvent(self, user_agent=DEFAULT_USER_AGENT):
        with open('../resources/get-request-event.json', 'r') as file:
            dataString = file.read()

        data = json.loads(dataString.replace('$user_agent', user_agent))

        return data

    def setUp(self):
        """ erase override target url before each test """
        if ENVIRONMENT_VAR_TARGET_URL in os.environ:
            del os.environ[ENVIRONMENT_VAR_TARGET_URL]

    #   https://www.freesoft.org/CIE/RFC/2068/143.htm
    def test_should_proxy_end_to_end_headers(self):
        request = urllib.request.Request("https://localhost")
        self.setUpTargetUrl('https://invalid.url/')

        with patch.object(urllib.request.Request, 'add_header', wraps=request.add_header):

            response = app.lambda_handler(self.lambdaEvent(), object())

            expected_call_list = [
                call('accept',
                     'application/json'),
                call("User-Agent",
                     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"),
                call("X-Amzn-Trace-Id", "Root=1-5e66d96f-7491f09xmpl79d18acf3d050")]

            self.assertEqual(expected_call_list, request.add_header.call_args_list)

    def test_should_read_remote_url(self):
        response = app.lambda_handler(self.lambdaEvent(), object())

        self.assertEqual("200", response['statusCode'], 'incorrect response code')
        self.assertEqual('application/json', response['headers']['Content-Type'], 'unexpected Content-Type')
        self.assertLess(0, len(response['body']), 'empty body response')

    def test_should_raise_HTTP502_on_invalid_url(self):
        self.setUpTargetUrl('https://invalid.url/')

        response = app.lambda_handler(self.lambdaEvent(), object())

        self.assertEqual("502", response['statusCode'], 'incorrect response code')
        self.assertEqual(
            "Unexpected URLError while retrieving remote site: <urlopen error [Errno 11001] getaddrinfo failed>",
            response['body'], 'incorrect response body')


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
if __name__ == "__main__":
    unittest.main()
