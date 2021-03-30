from unittest import TestCase
import json
import proxytton
import logging
import os

ENVIRONMENT_VAR_TARGET_URL = 'PROXY_OVERRIDE_TARGET_URL'

class Test(TestCase):

    def setUpTargetUrl(self, url):
        os.environ[ENVIRONMENT_VAR_TARGET_URL] = url

    def setUp(self):
        """ erase override target url before each test """
        if ENVIRONMENT_VAR_TARGET_URL in os.environ:
            del os.environ[ENVIRONMENT_VAR_TARGET_URL]

    def test_should_read_remote_url(self):
        with open('test/get-request-event.json') as f:
            event = json.load(f)
        response = proxytton.lambda_handler(event, object())
        logging.info('Response: ' + str(response))
        self.assertEqual("200", response['statusCode'], 'incorrect response code')

        self.assertLess(0, len(response['body']), 'empty body response')

    def test_should_raise_HTTP502_on_invalid_url(self):

        self.setUpTargetUrl('https://invalid.url/')

        with open('test/get-request-event.json') as f:
            event = json.load(f)

        response = proxytton.lambda_handler(event, object())

        self.assertEqual("502", response['statusCode'], 'incorrect response code')
        self.assertEqual("Unexpected URLError while retrieving remote site: <urlopen error [Errno 11001] getaddrinfo failed>", response['body'], 'incorrect response body')

