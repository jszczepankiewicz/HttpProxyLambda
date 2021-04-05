import json
import logging
import os
import sys
import unittest
import urllib

from unittest import TestCase

from unittest.mock import call, patch

from proxytton.app import ApiProxy

ENVIRONMENT_VAR_TARGET_URL = 'PROXY_OVERRIDE_TARGET_URL'
DEFAULT_USER_AGENT = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"


class ProxyTest(TestCase):

    def setUpTargetUrl(self, url):
        os.environ[ENVIRONMENT_VAR_TARGET_URL] = url

    def lambdaEvent(self, user_agent=DEFAULT_USER_AGENT):

        if os.path.isfile('tests/unit/get-request-event.json'):
            #   as visible in travis ci
            with open('tests/unit/get-request-event.json', 'r') as file:
                data_string = file.read()
        elif os.path.isfile('get-request-event.json'):
            #   as visible in IDE
            with open('get-request-event.json', 'r') as file:
                data_string = file.read()
        else:
            raise Exception('Unsupported environment. Path to test json file can not be determined.')

        return json.loads(data_string)

    def setUp(self):
        """ erase override target url before each test """
        if ENVIRONMENT_VAR_TARGET_URL in os.environ:
            del os.environ[ENVIRONMENT_VAR_TARGET_URL]

    #   https://www.freesoft.org/CIE/RFC/2068/143.htm
    def test_should_proxy_end_to_end_headers(self):
        request = urllib.request.Request("https://localhost")
        self.setUpTargetUrl('https://invalid.url/')

        with patch.object(urllib.request.Request, 'add_header', wraps=request.add_header):

            response = ApiProxy().process_event(self.lambdaEvent())

            expected_call_list = [
                call('accept',
                     'application/json'),
                call("User-Agent",
                     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"),
                call("X-Amzn-Trace-Id", "Root=1-5e66d96f-7491f09xmpl79d18acf3d050")]

            self.assertEqual(expected_call_list, request.add_header.call_args_list)

    def test_should_read_remote_url(self):
        response = ApiProxy().process_event(self.lambdaEvent())

        self.assertEqual("200", response['statusCode'], 'incorrect response code')
        self.assertEqual('application/json', response['headers']['Content-Type'], 'unexpected Content-Type')
        self.assertLess(0, len(response['body']), 'empty body response')

    def test_should_raise_HTTP502_on_unresolved_dns(self):
        self.setUpTargetUrl('https://invalid.url/')

        response = ApiProxy().process_event(self.lambdaEvent())

        self.assertEqual("502", response['statusCode'], 'incorrect response code')

        # on windows Errno 11001 could be observed, on linux Errno -2 for unresolved dns
        expected_responses = {
            'Unexpected URLError while retrieving remote site: <urlopen error [Errno 11001] getaddrinfo failed>',
            'Unexpected URLError while retrieving remote site: <urlopen error [Errno -2] Name or service not known>'}

        self.assertTrue(response['body'] in expected_responses, 'Unexpected response body')


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
if __name__ == "__main__":
    unittest.main()
