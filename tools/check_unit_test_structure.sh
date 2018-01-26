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

# This script identifies the unit test modules that do not correspond
# directly with a module in the code tree.  See TESTING.rst for the
# intended structure.

netforce_path=$(cd "$(dirname "$0")/.." && pwd)
base_test_path=netforce/tests/unit
test_path=$netforce_path/$base_test_path

test_files=$(find ${test_path} -iname 'test_*.py')

ignore_regexes=(
    # The following vendor plugins are not required to confrm to the
    # structural requirements.
    "^plugins/ibm.*$"
    # The following open source plugin tests are not actually unit
    # tests and are ignored pending their relocation to the functional
    # test tree.
    "^plugins/ml2/drivers/mech_sriov/mech_driver/test_mech_sriov_nic_switch.py$"
    "^plugins/ml2/test_security_group.py$"
    "^plugins/ml2/test_port_binding.py$"
    "^plugins/ml2/test_extension_driver_api.py$"
    "^plugins/ml2/test_ext_portsecurity.py$"
    "^plugins/ml2/test_agent_scheduler.py$"
    "^plugins/ml2/drivers/openvswitch/agent/test_agent_scheduler.py$"
    "^plugins/ml2/drivers/openvswitch/agent/test_ovs_tunnel.py$"
    "^plugins/openvswitch/test_agent_scheduler.py$"
)

error_count=0
ignore_count=0
total_count=0
for test_file in ${test_files[@]}; do
    relative_path=${test_file#$test_path/}
    expected_path=$(dirname $netforce_path/netforce/$relative_path)
    test_filename=$(basename "$test_file")
    expected_filename=${test_filename#test_}
    # Module filename (e.g. foo/bar.py -> foo/test_bar.py)
    filename=$expected_path/$expected_filename
    # Package dir (e.g. foo/ -> test_foo.py)
    package_dir=${filename%.py}
    if [ ! -f "$filename" ] && [ ! -d "$package_dir" ]; then
        for ignore_regex in ${ignore_regexes[@]}; do
            if [[ "$relative_path" =~ $ignore_regex ]]; then
                ((ignore_count++))
                continue 2
            fi
        done
        echo "Unexpected test file: $base_test_path/$relative_path"
        ((error_count++))
    fi
    ((total_count++))
done

if [ "$ignore_count" -ne 0 ]; then
    echo "$ignore_count unmatched test modules were ignored"
fi

if [ "$error_count" -eq 0 ]; then
    echo 'Success!  All test modules match targets in the code tree.'
    exit 0
else
    echo "Failure! $error_count of $total_count test modules do not match targets in the code tree."
    exit 1
fi
