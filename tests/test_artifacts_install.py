# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the artifacts.install module
"""
import runpy
import sys
import json
import pytest

def secret_json():
    """ Create secret as a JSON dictionary """
    secret_string = '{"secrets.yaml":"foo","place/cert.pem":"bar"}'

    return json.loads(secret_string)

def test_install_succeeds(mocker):
    """ Confirm that Home Assistant installs correctly """
    sys.path.append('artifacts')
    get_secret = mocker.patch('secret.get_secret', return_value=secret_json())
    os_chdir = mocker.patch('os.chdir')
    os_makedirs = mocker.patch('os.makedirs')
    file = mocker.patch('builtins.open', mocker.mock_open(read_data='rubbish'))
    sys.argv[1:] = ['my_secret_arn']
    runpy.run_module('artifacts.install')

    get_secret.assert_called_once()
    os_chdir.assert_any_call('config')
    os_makedirs.assert_any_call('place', exist_ok=True)
    file.assert_any_call('secrets.yaml', 'w', encoding="utf-8")
    file.assert_any_call('place/cert.pem', 'w', encoding="utf-8")

def test_install_missing_argument():
    """ Confirm that the install fails if the secret ARN argument is missing  """
    sys.path.append('artifacts')

    # Don't pass any arguments
    sys.argv[1:] = []

    with pytest.raises(SystemExit) as system_exit:
        runpy.run_module('artifacts.install')
        assert system_exit.type == SystemExit
        assert system_exit.code == 1
