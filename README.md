[![Build Status](https://travis-ci.org/jszczepankiewicz/HttpProxyLambda.svg?branch=master)](https://travis-ci.org/jszczepankiewicz/HttpProxyLambda)

# HTTP proxy for AWS API GW working in REST API mode.

Tested on Python 3.8

## HOWTOS
### HOWTO configure proxy target host and path mapping
Following env variable contains mapping:
PROXY_MAPPINGS
content should be json formatted. Example mapping configuration:
`
{"/abc": "https://superduper.com##path##", "/xyz/fxc": "https://anno.xyz:8080/pipipi##path##"}
`
which means:
if /abc will be invoked than target url will be https://superduper.com/abc

### HOWTO add basic authentication downstream using ENV Variables injection
Function supports providing BASIC HTTP auth credentials using injection through env variables. To inject that please make sure 
following env variables are set:
PROXY_BASIC_PLAIN_USER - username
PROXY_BASIC_PLAIN_PASS - password

## Unsupported:
- multi-value headers in request (https://docs.aws.amazon.com/elasticloadbalancing/latest/application/lambda-functions.html#multi-value-headers)
