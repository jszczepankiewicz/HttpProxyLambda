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

class ProxyTest(TestCase):

    def setUpTargetUrl(self, url):
        os.environ[ENVIRONMENT_VAR_TARGET_URL] = url

    def __lower_dict(self, d):
        new_dict = dict((k.lower(), v) for k, v in d.items())
        return new_dict

    def __get_request_empty_header1_event(self):
        return self.__lambda_event('get-request-empty-headers-1.json')

    def __get_request_empty_header2_event(self):
        return self.__lambda_event('get-request-empty-headers-2.json')

    def __get_request_event(self):
        return self.__lambda_event('get-request-event.json')

    def __lambda_event(self, path):

        if os.path.isfile('tests/unit/' + path):
            #   as visible in travis ci
            with open('tests/unit/' + path, 'r') as file:
                data_string = file.read()
        elif os.path.isfile(path):
            #   as visible in IDE
            with open(path, 'r') as file:
                data_string = file.read()
        else:
            raise Exception('Unsupported environment. Path to test json file can not be determined.')

        return json.loads(data_string)

    def setUp(self):
        """ erase override target url before each test """
        if ENVIRONMENT_VAR_TARGET_URL in os.environ:
            del os.environ[ENVIRONMENT_VAR_TARGET_URL]

    def test_should_support_empty_request_headers(self):

        #   when
        response1 = ApiProxy().process_event(self.__get_request_empty_header1_event())
        response2 = ApiProxy().process_event(self.__get_request_empty_header2_event())

        #   then
        self.assertEqual("200", response1['statusCode'], 'incorrect response code')
        self.assertEqual('application/json; charset=utf-8', response1['headers']['Content-Type'], 'Unexpected Content-Type')
        self.assertLess(0, len(response1['body']), 'empty body response')

        self.assertEqual("200", response2['statusCode'], 'incorrect response code')
        self.assertEqual('application/json; charset=utf-8', response2['headers']['Content-Type'], 'Unexpected Content-Type')
        self.assertLess(0, len(response2['body']), 'empty body response')


    #   https://www.freesoft.org/CIE/RFC/2068/143.htm
    def test_should_proxy_end_to_end_headers(self):
        request = urllib.request.Request("https://localhost")
        self.setUpTargetUrl('https://invalid.url/')

        with patch.object(urllib.request.Request, 'add_header', wraps=request.add_header):

            response = ApiProxy().process_event(self.__get_request_event())

            expected_call_list = [
                call('accept',
                     'application/json'),
                call("User-Agent",
                     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"),
                call("X-Amzn-Trace-Id", "Root=1-5e66d96f-7491f09xmpl79d18acf3d050")]

            self.assertEqual(expected_call_list, request.add_header.call_args_list)

    def test_should_read_remote_url(self):
        response = ApiProxy().process_event(self.__get_request_event())

        self.assertEqual("200", response['statusCode'], 'incorrect response code')
        self.assertEqual('application/json; charset=utf-8', response['headers']['Content-Type'], 'Unexpected Content-Type')
        self.assertLess(0, len(response['body']), 'empty body response')

    def test_should_read_remote_url_without_request_headers(self):
        response = ApiProxy().process_event(self.__get_request_event())

        self.assertEqual("200", response['statusCode'], 'incorrect response code')
        self.assertEqual('application/json; charset=utf-8', response['headers']['Content-Type'], 'Unexpected Content-Type')
        self.assertLess(0, len(response['body']), 'empty body response')

    def test_should_return_response_headers(self):
        response = ApiProxy().process_event(self.__get_request_event())
        headers_lower = self.__lower_dict(response['headers'])

        self.assertEqual("200", response['statusCode'], 'incorrect response code')
        self.assertLess(0, len(response['body']), 'empty body response')
        self.assertEqual('application/json; charset=utf-8', headers_lower['content-type'], 'Unexpected Content-Type')
        self.assertEqual('Express', headers_lower['x-powered-by'], 'Unexpected X-Powered-By')
        self.assertEqual('*', headers_lower['access-control-allow-origin'], 'Access-Control-Allow-Origin')
        self.assertEqual('max-age=14400', headers_lower['cache-control'], 'Unexpected Cache-Control')
        self.assertEqual('bytes', headers_lower['accept-ranges'], 'Unexpected Accept-Ranges')
        self.assertEqual('Accept-Encoding', headers_lower['vary'], 'Unexpected Vary')
        self.assertEqual('cloudflare', headers_lower['server'], 'Unexpected Server')

        expected_temporal_headers = {'Date', 'Etag', 'CF-Cache-Status', 'Age', 'cf-request-id', 'Expect-CT',
                                     'Report-To', 'NEL', 'CF-RAY', 'alt-svc'}

        for i in expected_temporal_headers:
            self.assertTrue((i in response['headers']), 'Missing expected temporal header: ' + i)

        #   should be lower case, hop-by-hop headers
        #   TODO: add better case-insensitive checks
        unexpected_headers = {'Connection', 'Keep-Alive', 'Public', 'Proxy-Authenticate', 'Transfer-Encoding',
                              'Upgrade', 'Host'}

        for i in unexpected_headers:
            self.assertFalse((i in response['headers']), 'Unexpected presence of hop-by-hop header: ' + i)


    def test_should_raise_HTTP502_on_unresolved_dns(self):
        self.setUpTargetUrl('https://invalid.url/')

        response = ApiProxy().process_event(self.__get_request_event())

        self.assertEqual("502", response['statusCode'], 'incorrect response code')

        # on windows Errno 11001 could be observed, on linux Errno -2 for unresolved dns
        expected_responses = {
            'Unexpected URLError while retrieving remote site: <urlopen error [Errno 11001] getaddrinfo failed>',
            'Unexpected URLError while retrieving remote site: <urlopen error [Errno -2] Name or service not known>'}

        self.assertTrue(response['body'] in expected_responses, 'Unexpected response body')


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
if __name__ == "__main__":
    unittest.main()
