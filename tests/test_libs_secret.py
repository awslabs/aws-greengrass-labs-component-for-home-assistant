# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the libs.secret module
"""
from unittest.mock import Mock
import pytest
from libs.secret import Secret

SECRET_STRING = 'foobar'
REGION ='us-east-1'

@pytest.fixture(name='boto3_client')
def fixture_boto3_client(mocker):
    """ Mocked boto3 client object """
    boto3_client = mocker.patch('boto3.client')
    # Make our mock get returned by the client() method call
    boto3_client.return_value = boto3_client
    yield boto3_client

@pytest.fixture(name="secret")
def fixture_secret():
    """ Instantiates a Secret object """
    return Secret(REGION)

def test_secret_get_success(secret):
    """ Get should succeed if there's a secret """
    expected_response = {'SecretString': SECRET_STRING}
    secret.secretsmanager_client.get_secret_value = Mock(return_value = expected_response)
    response = secret.get()
    assert response == expected_response
    secret.secretsmanager_client.get_secret_value.assert_called_once()

def test_secret_get_fail(secret):
    """ Get should fail if there's no secret """
    secret.secretsmanager_client.get_secret_value = Mock(side_effect = Exception('mocked error'))
    with pytest.raises(Exception):
        secret.get()
    secret.secretsmanager_client.get_secret_value.assert_called_once()

def test_secret_put_create_success(secret):
    """ Put should succeed, with no exception generated """
    secret_list = {'SecretList': []}
    secret.secretsmanager_client.list_secrets = Mock(return_value = secret_list)
    expected_response = {'ARN': 'mocked_arn'}
    secret.secretsmanager_client.create_secret = Mock(return_value = expected_response)
    response = secret.put(SECRET_STRING)
    secret.secretsmanager_client.create_secret.assert_called_once_with(
        Name=secret.SECRET_NAME,
        SecretString=SECRET_STRING,
        Description=secret.SECRET_DESCRIPTION
    )
    assert response == expected_response

def test_secret_put_create_fail(secret):
    """ Put should fail, if the create gets an exception """
    secret_list = {'SecretList': []}
    secret.secretsmanager_client.list_secrets = Mock(return_value = secret_list)
    secret.secretsmanager_client.create_secret = Mock(side_effect = Exception('mocked error'))
    with pytest.raises(Exception):
        secret.put(SECRET_STRING)
    secret.secretsmanager_client.create_secret.assert_called_once_with(
        Name=secret.SECRET_NAME,
        SecretString=SECRET_STRING,
        Description=secret.SECRET_DESCRIPTION
    )

def test_secret_put_update_success(secret):
    """ Put should succeed, with no exception generated """
    secret_list = {'SecretList': [{'Name': secret.SECRET_NAME}]}
    secret.secretsmanager_client.list_secrets = Mock(return_value = secret_list)
    expected_response = {'ARN': 'mocked_arn'}
    secret.secretsmanager_client.update_secret = Mock(return_value = expected_response)
    response = secret.put(SECRET_STRING)
    secret.secretsmanager_client.update_secret.assert_called_once_with(
        SecretId=secret.SECRET_NAME,
        SecretString=SECRET_STRING,
        Description=secret.SECRET_DESCRIPTION
    )
    assert response == expected_response

def test_secret_put_update_fail(secret):
    """ Put should fail, if the update gets an exception """
    secret_list = {'SecretList': [{'Name': secret.SECRET_NAME}]}
    secret.secretsmanager_client.list_secrets = Mock(return_value = secret_list)
    secret.secretsmanager_client.update_secret = Mock(side_effect = Exception('mocked error'))
    with pytest.raises(Exception):
        secret.put(SECRET_STRING)
    secret.secretsmanager_client.update_secret.assert_called_once_with(
        SecretId=secret.SECRET_NAME,
        SecretString=SECRET_STRING,
        Description=secret.SECRET_DESCRIPTION
    )

def test_secret_exists_success(secret):
    """ Returns true if a secret exists """
    secret_list = {'SecretList': [{'Name': secret.SECRET_NAME}]}
    secret.secretsmanager_client.list_secrets = Mock(return_value = secret_list)
    assert secret.exists()

def test_secret_exists_fail(secret):
    """ Returns false if a secret doesn't exist """
    secret_list = {'SecretList': []}
    secret.secretsmanager_client.list_secrets = Mock(return_value = secret_list)
    assert not secret.exists()
