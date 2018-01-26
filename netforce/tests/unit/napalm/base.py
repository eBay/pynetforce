
#!/usr/bin/env python

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

import unittest


class DietTestCase(unittest.TestCase):
    """Same great taste, less filling.

    DietTestCase performs setup and teardown activities that ALL other unit
    tests should also perform. Each test suite should inherit from
    DietTestCase, and run super().setUp() before running it's own setup
    activities. Same for teardown.
    """

    def setUp(self):
        """Perform setup activies for all unit tests

        """

        pass

    def tearDown(self):
        """Perform teardown activies for all unit tests

        """

        pass
