# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the libs.secret module
"""
import os
import pytest
from moto import mock_secretsmanager
from libs.secret import Secret

SECRET_STRING = 'foobar'
REGION ='us-east-1'

@mock_secretsmanager
@pytest.fixture(name="secret") # Magic to beat Pylint complaints about the fixture
def fixture_secret():
    """ Instantiates a Secret object, using dummy credentials """
    os.environ['AWS_ACCESS_KEY_ID'] = 'testing'
    os.environ['AWS_SECRET_ACCESS_KEY'] = 'testing'
    os.environ['AWS_SECURITY_TOKEN'] = 'testing'
    os.environ['AWS_SESSION_TOKEN'] = 'testing'
    sec = Secret(REGION)
    return sec

@mock_secretsmanager
def test_secret_get_fail(secret):
    """ Get should fail if there's no secret """
    with pytest.raises(Exception):
        secret.get()

@mock_secretsmanager
def test_secret_put_success(secret):
    """ Put should succeed, with no exception generated """
    secret.put(SECRET_STRING)
    assert True

@mock_secretsmanager
def test_secret_put_get_success(secret):
    """ Get should succeed if preceded by a put """
    secret.put(SECRET_STRING)
    secret_value = secret.get()
    assert secret_value['SecretString'] == SECRET_STRING

@mock_secretsmanager
def test_secret_put_put_get_success(secret):
    """ Second put should update the secret value """
    secret.put(SECRET_STRING)
    secret.put('stuff')
    secret_value = secret.get()
    assert secret_value['SecretString'] == 'stuff'

@mock_secretsmanager
def test_secret_exists_fail(secret):
    """ No secret should exist if we haven't done a put """
    assert not secret.exists()

@mock_secretsmanager
def test_secret_exists_success(secret):
    """ Secret should exist if we've done a put """
    secret.put(SECRET_STRING)
    assert secret.exists()
