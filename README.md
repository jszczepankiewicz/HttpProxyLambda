[![Build Status](https://travis-ci.org/jszczepankiewicz/HttpProxyLambda.svg?branch=master)](https://travis-ci.org/jszczepankiewicz/HttpProxyLambda)

HTTP proxy for AWS API GW working in REST API mode.

Tested on Python 3.8

Unsupported:
- multi-value headers in request (https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html#multi-value-headers)
