# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the libs.gdk_config module
"""
from libs.gdk_config import GdkConfig

NAME = 'FooBar'
VERSION = 'rubbish'
REGION = 'neverland'

CONTENTS = '\
{\
    "component" :{\
      "' + NAME + '": {\
        "author": "Amazon",\
        "version": "' + VERSION + '",\
        "build": {\
          "build_system": "custom",\
          "custom_build_command": [\
            "python3",\
            "gdk_build.py"\
          ]\
        },\
        "publish": {\
          "bucket": "blah",\
          "region": "' + REGION + '"\
        }\
      }\
    },\
    "gdk_version": "1.0.0"\
}\
'

def test_config_loads(mocker):
    """ Confirm that the configuration loads correctly """
    file = mocker.patch('builtins.open', mocker.mock_open(read_data=CONTENTS))

    gdk_config = GdkConfig()

    file.assert_any_call('gdk-config.json', encoding="utf-8")
    assert gdk_config.name() == NAME
    assert gdk_config.version() == VERSION
    assert gdk_config.region() == REGION
