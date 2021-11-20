# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the artifacts.secret module
"""
import pytest
from artifacts.secret import get_secret

def test_get_secret_succeeds(mocker):
    """ Check a successful get_secret call """
    ipc_connect = mocker.patch('awsiot.greengrasscoreipc.connect')
    mocker.patch('json.loads', return_value='stuff')
    secret = get_secret('foobar')
    ipc_connect.assert_called_once()
    assert secret == 'stuff'

def test_get_secret_fails(mocker):
    """ Check a get_secret call that fails due to exception """
    ipc_connect = mocker.patch('awsiot.greengrasscoreipc.connect', side_effect=Exception('mocked exception'))

    # Exception should be caught and result in sys.exit(1)
    with pytest.raises(SystemExit) as system_exit:
        get_secret('foobar')
        assert system_exit.type == SystemExit
        assert system_exit.code == 1

    ipc_connect.assert_called_once()
