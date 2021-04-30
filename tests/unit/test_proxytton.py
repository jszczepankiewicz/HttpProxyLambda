import json
import logging
import os
import sys
import unittest
import urllib


from unittest import TestCase, mock

from unittest.mock import call, patch

from proxytton.app import ApiProxy, PathTransformer, PathInjector

ENVIRONMENT_VAR_TARGET_HOST = 'PROXY_TARGET_HOST'
# fixme: use app.py referencing to avoid duplication
ENV_PLAINTEXT_USER = 'PROXY_BASIC_PLAIN_USER'
ENV_PLAINTEXT_PASS = 'PROXY_BASIC_PLAIN_PASS'
ENV_MAPPINGS = 'PROXY_MAPPINGS'
TEST_BASIC_USER = 'SomeUser'
TEST_BASIC_PASS = 'PlainPass'
TEST_BASIC_ENCODED = 'Basic U29tZVVzZXI6UGxhaW5QYXNz'

class ProxyTest(TestCase):

    def __setup_target_host(self, host='reqres.in'):
        os.environ[ENVIRONMENT_VAR_TARGET_HOST] = host

    def __lower_dict(self, d):
        new_dict = dict((k.lower(), v) for k, v in d.items())
        return new_dict

    def __post_request_1_event(self):
        return self.__lambda_event('post-request-1.json')

    def __get_request_empty_header1_event(self):
        return self.__lambda_event('get-request-empty-headers-1.json')

    def __get_request_empty_header2_event(self):
        return self.__lambda_event('get-request-empty-headers-2.json')

    def __get_request_event(self):
        return self.__lambda_event('get-request-event.json')

    def __given_plaintext_password_configured(self):
        os.environ[ENV_PLAINTEXT_USER] = TEST_BASIC_USER
        os.environ[ENV_PLAINTEXT_PASS] = TEST_BASIC_PASS
        return


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

        if ENVIRONMENT_VAR_TARGET_HOST in os.environ:
            del os.environ[ENVIRONMENT_VAR_TARGET_HOST]
        if ENV_PLAINTEXT_USER in os.environ:
            del os.environ[ENV_PLAINTEXT_USER]
        if ENV_PLAINTEXT_PASS in os.environ:
            del os.environ[ENV_PLAINTEXT_PASS]
        if ENV_MAPPINGS in os.environ:
            del os.environ[ENV_MAPPINGS]

        os.environ[ENV_MAPPINGS] = '{"/api/users/2": "https://reqres.in##path##", "/api/register": "https://reqres.in##path##"}'
        #self.__setup_target_host('reqres.in')

    def test_should_support_basic_auth_plaintext_downstream(self):

        self.__given_plaintext_password_configured()

        request = urllib.request.Request("https://localhost")

        with patch.object(urllib.request.Request, 'add_header', wraps=request.add_header):

            response = ApiProxy().process_event(self.__post_request_1_event())

            expected_call_list = [
                call('Authorization',
                     'Basic U29tZVVzZXI6UGxhaW5QYXNz'),
                call('accept',
                     'application/json'),
                call('Content-Type', 'application/json'),
                call("User-Agent",
                     "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.132 Safari/537.36"),
                call("X-Amzn-Trace-Id", "Root=1-5e66d96f-7491f09xmpl79d18acf3d050")]

            self.assertEqual(expected_call_list, request.add_header.call_args_list)

    def test_should_support_post_request(self):

        #   when
        response1 = ApiProxy().process_event(self.__post_request_1_event())
        print(response1['body'])
        #   then
        self.assertEqual("200", response1['statusCode'], 'incorrect response code')
        self.assertEqual('application/json; charset=utf-8', response1['headers']['Content-Type'], 'Unexpected Content-Type')
        self.assertEqual('{"id":4,"token":"QpwL5tke4Pnpja7X4"}', response1['body'], 'unexpected body response')


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
        self.__setup_target_host('invalid.url')

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
        os.environ[ENV_MAPPINGS] = '{"/api/users/2": "https://invalid.url##path##", "/api/register": "https://invalid.url##path##"}'

        response = ApiProxy().process_event(self.__get_request_event())

        self.assertEqual("502", response['statusCode'], 'incorrect response code')

        # on windows Errno 11001 could be observed, on linux Errno -2 for unresolved dns
        expected_responses = {
            'Unexpected URLError while retrieving remote site: <urlopen error [Errno 11001] getaddrinfo failed>',
            'Unexpected URLError while retrieving remote site: <urlopen error [Errno -2] Name or service not known>'}

        self.assertTrue(response['body'] in expected_responses, 'Unexpected response body')

    def test_should_support_path_transform_existing_mapping(self):

        path_mapping = {"/abc": "https://superduper.com##path##",
                        "/xyz/fxc": "https://anno.xyz:8080/pipipi##path##"}
        proxy = PathTransformer(path_mapping)

        target_url = proxy.target_url("/xyz/fxc")
        self.assertEqual("https://anno.xyz:8080/pipipi/xyz/fxc", target_url, "Unexpected target_url")

    def test_should_return_none_path_transform_non_existing_mapping(self):
        path_mapping = {"/abc": "https://superduper.com##path##",
                        "/xyz/fxc": "https://anno.xyz:8080/pipipi##path##"}
        proxy = PathTransformer(path_mapping)

        target_url = proxy.target_url("/abc/nonexisting")
        self.assertIsNone(target_url)


    def test_should_load_path_injections_from_os_variables(self):
        os.environ[ENV_MAPPINGS] = '{"/abc": "https://superduper.com##path##", "/xyz/fxc": "https://anno.xyz:8080/pipipi##path##"}'
        mappings = PathInjector().mappings()
        self.assertEqual({"/abc": "https://superduper.com##path##", "/xyz/fxc": "https://anno.xyz:8080/pipipi##path##"}, mappings)


logging.basicConfig(stream=sys.stderr, level=logging.DEBUG)
if __name__ == "__main__":
    unittest.main()
