# Copyright 2018 eBay Inc.
# Copyright 2012 OpenStack LLC.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#      https://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

# This exceptions might be encountered during trace CR creation.
# Note: Have kept the exceptions seperate and not calling base exception
# so that it can be moved to neutron and can be re-used.


class ResourceRedirect(Exception):
    def __init__(self, reason):
        self.message = "Resource %(uri)s has been redirected"


class RequestBad(Exception):
    def __init__(self, reason):
        self.message = "Request %(uri)s is Bad, response %(response)s"


class Forbidden(Exception):
    def __init__(self, reason):
        self.message = "Forbidden: %(uri)s"


class ResourceNotFound(Exception):
    def __init__(self, reason):
        self.message = "Resource %(uri)s not found"


class MediaTypeUnsupport(Exception):
    def __init__(self, reason):
        self.message = "Media Type %(uri)s is not supported"


class ServiceUnavailable(Exception):
    def __init__(self, reason):
        self.message = "Service Unavailable: %(uri)s"


class ChangeStopActive(Exception):
    def __init__(self):
        self.message = 'CR creation is stopped for time being. Please try' \
                       ' once change stop is inactive.'


class EsamsClientException(Exception):
    pass
