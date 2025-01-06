# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the artifacts.secret module
"""
import json
import pytest
from artifacts.secret import get_secret

def test_get_secret_succeeds(mocker):
    """ Check a successful get_secret call """
    ipc_client_class = mocker.patch('artifacts.secret.GreengrassCoreIPCClientV2')
    ipc_client = ipc_client_class.return_value
    secret_string = '{\"password\": \"junk\"}'
    ipc_client.get_secret_value.return_value.secret_value.secret_string = secret_string
    secret = get_secret('foobar')
    ipc_client.get_secret_value.assert_called_once_with(secret_id='foobar', refresh=True)
    assert secret == json.loads(secret_string)

def test_get_secret_fails(mocker):
    """ Check a get_secret call that fails due to exception """
    ipc_client_class = mocker.patch('artifacts.secret.GreengrassCoreIPCClientV2')
    ipc_client = ipc_client_class.return_value
    ipc_client.get_secret_value.side_effect = Exception('mocked exception')

    # Exception should be caught and result in sys.exit(1)
    with pytest.raises(SystemExit) as system_exit:
        get_secret('foobar')
        assert system_exit.type == SystemExit
        assert system_exit.code == 1

    ipc_client.get_secret_value.assert_called_once_with(secret_id='foobar', refresh=True)
