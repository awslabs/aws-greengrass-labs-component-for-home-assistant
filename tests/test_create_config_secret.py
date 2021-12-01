# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the create_config_secret.py script
"""
import runpy

FILENAMES = ['foo.yml', 'foo/bar.yml']
CONTENTS = 'rocinante'
REGION = 'foobar'
SECRET_STRING = '{"' + FILENAMES[0] + '":"' + CONTENTS +\
                '","' + FILENAMES[1] + '":"' + CONTENTS + '"}'

def test_create_config_secret(mocker):
    """ Confirm that the secret string is correctly formed """
    mocker.patch('glob.glob', return_value=FILENAMES)
    gdk_config_init = mocker.patch('libs.gdk_config.GdkConfig.__init__', return_value=None)
    gdk_config_region = mocker.patch('libs.gdk_config.GdkConfig.region', return_value=REGION)
    secret_init = mocker.patch('libs.secret.Secret.__init__', return_value=None)
    secret_put = mocker.patch('libs.secret.Secret.put')
    file = mocker.patch('builtins.open', mocker.mock_open(read_data=CONTENTS))
    runpy.run_module('create_config_secret')

    file.assert_any_call(FILENAMES[0], encoding="utf-8")
    file.assert_any_call(FILENAMES[1], encoding="utf-8")
    gdk_config_init.assert_called_once()
    gdk_config_region.assert_called_once()
    secret_init.assert_called_once_with(REGION)
    secret_put.assert_called_once_with(SECRET_STRING)
