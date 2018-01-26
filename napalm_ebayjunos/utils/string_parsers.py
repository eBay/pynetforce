# Copyright 2018 eBay Inc.
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


import re


def sorted_nicely(l):
    """Sorting function.

    Sort the given iterable in the way that humans expect.
    """

    def convert(text):
        return int(text) if text.isdigit() else text

    def alphanum_key(key):
        return [convert(c) for c in re.split('([0-9]+)', key)]
    return sorted(l, key=alphanum_key)


def colon_separated_string_to_dict(string, separator=':'):
    """Converts a string in the format:

        Name: Et3
        Switchport: Enabled
        Administrative Mode: trunk
        Operational Mode: trunk
        MAC Address Learning: enabled
        Access Mode VLAN: 3 (VLAN0003)
        Trunking Native Mode VLAN: 1 (default)
        Administrative Native VLAN tagging: disabled
        Administrative private VLAN mapping: ALL
        Trunking VLANs Enabled: 2-3,5-7,20-21,23,100-200
        Trunk Groups:

    into a dictionary
    """

    dictionary = dict()

    for line in string.splitlines():
        line_data = line.split(separator)

        if len(line_data) > 1:
            dictionary[line_data[0].strip()] = ''.join(line_data[1:]).strip()
        elif len(line_data) == 1:
            dictionary[line_data[0].strip()] = None
        else:
            raise Exception('Something went wrong parsing the colo'
                            ' separated string {}'.format(line))

    return dictionary


def hyphen_range(string):
    """Expands a string of numbers into a list.

    Expands a string of numbers separated by commas and hyphens into
    a list of integers.
    For example:  2-3,5-7,20-21,23,100-200
    """
    list_numbers = list()
    temporary_list = string.split(',')

    for element in temporary_list:
        sub_element = element.split('-')

        if len(sub_element) == 1:
            list_numbers.append(int(sub_element[0]))
        elif len(sub_element) == 2:
            for x in range(int(sub_element[0]), int(sub_element[1]) + 1):
                list_numbers.append(x)
        else:
            raise Exception('Something went wrong expanding'
                            ' the range {}'.format(string))

    return list_numbers


def convert_uptime_string_seconds(uptime):
    """Uptime conversion to seconds

    Convert uptime strings to seconds. The string can be formatted
    various ways, eg.
    1 hour, 56 minutes
    """

    regex_1 = re.compile(
        r"((?P<weeks>\d+) week(s)?,\s+)?((?P<days>\d+) day(s)?,\s+)"
        r"?((?P<hours>\d+) hour(s)?,\s+)?((?P<minutes>\d+) minute(s)?)")

    regex_2 = re.compile(
        r"((?P<hours>\d+)):((?P<minutes>\d+)):((?P<seconds>\d+))")

    regex_list = [regex_1, regex_2]

    uptime_dict = dict()
    for regex in regex_list:
        uptime_dict = regex.search(uptime)
        if uptime_dict is not None:
            uptime_dict = uptime_dict.groupdict()
            break
        uptime_dict = dict()

    uptime_seconds = 0

    for unit, value in uptime_dict.iteritems():
        if value is not None:
            if unit == 'weeks':
                uptime_seconds += int(value) * 604800
            elif unit == 'days':
                uptime_seconds += int(value) * 86400
            elif unit == 'hours':
                uptime_seconds += int(value) * 3600
            elif unit == 'minutes':
                uptime_seconds += int(value) * 60
            elif unit == 'seconds':
                uptime_seconds += int(value)
            else:
                raise Exception('Unrecognized unit "{}" in'
                                ' uptime:{}'.format(unit, uptime))

    return uptime_seconds
