# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for deploy_component_version.py
"""

from unittest.mock import call
import copy
import runpy
import sys
import pytest

REGION = 'us-east-1'
COMPONENT_NAME = 'Maynard'
COMPONENT_VERSION = 'Aenima'
CORE_DEVICE_NAME = 'Tool'
DEPLOYMENT_ID = 'jambi'
DEPLOYMENT_NAME = f'Deployment for {CORE_DEVICE_NAME}'
TARGET_ARN = f'arn:aws:iot:us-east-1:000011112222:thing/{CORE_DEVICE_NAME}'
NEW_DEPLOYMENT_ID = 'the pot'
SECRET_ARN = 'lateralus'
COMPONENT_DOCKER_APPLICATION_MANAGER = 'aws.greengrass.DockerApplicationManager'
COMPONENT_SECRET_MANAGER = 'aws.greengrass.SecretManager'
COMPONENTS = {
                COMPONENT_DOCKER_APPLICATION_MANAGER: {
                    'componentVersion': COMPONENT_VERSION
                },
                COMPONENT_SECRET_MANAGER: {
                    'componentVersion': COMPONENT_VERSION,
                    'configurationUpdate': {'merge': '{\"cloudSecrets\":[{\"arn\": \"' + SECRET_ARN + '\"}]}'}
                },
                COMPONENT_NAME: {
                    'componentVersion': COMPONENT_VERSION
                },
            }

@pytest.fixture(name='boto3_client')
def fixture_boto3_client(mocker):
    """ Mocked boto3 client object """
    boto3_client = mocker.patch('boto3.client')
    # Make our mock get returned by the client() method call
    boto3_client.return_value = boto3_client

    # Mock the GDK configuration
    gdk_config_class = mocker.patch('libs.gdk_config.GdkConfig')
    gdk_config = gdk_config_class.return_value
    gdk_config.name.return_value = COMPONENT_NAME
    gdk_config.region.return_value = REGION

    # Mock the secret
    secret_class = mocker.patch('libs.secret.Secret')
    secret = secret_class.return_value
    secret.get.return_value = {'SecretString':'foobar', 'ARN': SECRET_ARN}

    boto3_client.get_caller_identity.return_value.get.return_value = '000011112222'
    boto3_client.list_deployments.return_value = {'deployments': [{'deploymentId': DEPLOYMENT_ID}]}
    boto3_client.get_deployment.return_value = {'deploymentName': DEPLOYMENT_NAME,
                                                'components': copy.deepcopy(COMPONENTS),
                                                'targetArn': TARGET_ARN, 'deploymentStatus': 'whatever'}
    boto3_client.create_deployment.return_value = {'deploymentId': NEW_DEPLOYMENT_ID}
    boto3_client.list_component_versions.return_value = {'componentVersions': [{'componentName': COMPONENT_NAME,
                                                                          'componentVersion': COMPONENT_VERSION}]}
    yield boto3_client

    gdk_config_class.assert_called_once()
    boto3_client.list_deployments.assert_called_once()

def confirm_exit():
    """ Confirm program hits sys.exit(1) """
    sys.argv[1:] = [COMPONENT_VERSION, CORE_DEVICE_NAME]
    with pytest.raises(SystemExit) as system_exit:
        runpy.run_module('deploy_component_version')
        assert system_exit.type == SystemExit
        assert system_exit.code == 1

def confirm_success(boto3_client):
    """ Confirm program exit with no error """
    sys.argv[1:] = [COMPONENT_VERSION, CORE_DEVICE_NAME]
    runpy.run_module('deploy_component_version')
    calls=[call(deploymentId=DEPLOYMENT_ID), call(deploymentId=NEW_DEPLOYMENT_ID)]
    boto3_client.get_deployment.assert_has_calls(calls)
    boto3_client.create_deployment.assert_called_once_with(targetArn=TARGET_ARN, deploymentName=DEPLOYMENT_NAME,
                                                           components=COMPONENTS)

def test_fails_if_list_deployments_exception(boto3_client):
    """ Should exit abruptly if list_deployments throws an exception """
    boto3_client.list_deployments.side_effect = Exception('mocked error')
    confirm_exit()

def test_fails_if_no_existing_deployments(boto3_client):
    """ Should exit abruptly if there are zero deployments """
    boto3_client.list_deployments.return_value = {'deployments': []}
    confirm_exit()

def test_fails_if_get_deployment_exception(boto3_client):
    """ Should exit abruptly if get_deployment throws an exception """
    boto3_client.get_deployment.side_effect = Exception('mocked error')
    confirm_exit()
    boto3_client.get_deployment.assert_called_once_with(deploymentId=DEPLOYMENT_ID)

def test_fails_if_list_component_versions_exception(boto3_client):
    """ Should exit abruptly if list_component_versions throws an exception """
    boto3_client.list_component_versions.side_effect = Exception('mocked error')
    del boto3_client.get_deployment.return_value['components'][COMPONENT_DOCKER_APPLICATION_MANAGER]
    confirm_exit()
    component_arn = f'arn:aws:greengrass:{REGION}:aws:components:{COMPONENT_DOCKER_APPLICATION_MANAGER}'
    boto3_client.get_deployment.assert_called_once_with(deploymentId=DEPLOYMENT_ID)
    boto3_client.list_component_versions.assert_called_once_with(arn=component_arn)

def test_fails_if_create_deployment_exception(boto3_client):
    """ Should exit abruptly if create_deployment throws an exception """
    boto3_client.create_deployment.side_effect = Exception('mocked error')
    confirm_exit()
    boto3_client.get_deployment.assert_called_once_with(deploymentId=DEPLOYMENT_ID)
    boto3_client.create_deployment.assert_called_once_with(targetArn=TARGET_ARN, deploymentName=DEPLOYMENT_NAME,
                                                           components=COMPONENTS)

def test_fails_if_second_get_deployment_exception(boto3_client):
    """ Should exit abruptly if the second get_deployment throws an exception """
    boto3_client.get_deployment.side_effect = [boto3_client.get_deployment.return_value, Exception('mocked error')]
    confirm_exit()
    calls=[call(deploymentId=DEPLOYMENT_ID), call(deploymentId=NEW_DEPLOYMENT_ID)]
    boto3_client.get_deployment.assert_has_calls(calls)
    boto3_client.create_deployment.assert_called_once_with(targetArn=TARGET_ARN, deploymentName=DEPLOYMENT_NAME,
                                                           components=COMPONENTS)

def test_fails_if_deployment_times_out(mocker, boto3_client):
    """ Should exit abruptly if the deployment times out """
    boto3_client.get_deployment.return_value['deploymentStatus'] = 'ACTIVE'
    mocker.patch('time.time', side_effect=[0, 0, 900])
    confirm_exit()
    calls=[call(deploymentId=DEPLOYMENT_ID), call(deploymentId=NEW_DEPLOYMENT_ID)]
    boto3_client.get_deployment.assert_has_calls(calls)
    boto3_client.create_deployment.assert_called_once_with(targetArn=TARGET_ARN, deploymentName=DEPLOYMENT_NAME,
                                                           components=COMPONENTS)

def test_fails_if_deployment_status_failed(boto3_client):
    """ Should exit abruptly if the deployment failed """
    boto3_client.get_deployment.return_value['deploymentStatus'] = 'FAILED'
    confirm_exit()
    calls=[call(deploymentId=DEPLOYMENT_ID), call(deploymentId=NEW_DEPLOYMENT_ID)]
    boto3_client.get_deployment.assert_has_calls(calls)
    boto3_client.create_deployment.assert_called_once_with(targetArn=TARGET_ARN, deploymentName=DEPLOYMENT_NAME,
                                                           components=COMPONENTS)

def test_succeeds_named_add(boto3_client):
    """ Successful deployment to a named deployment, first time adding the component """
    boto3_client.get_deployment.return_value['deploymentStatus'] = 'COMPLETED'
    del boto3_client.get_deployment.return_value['components'][COMPONENT_NAME]
    confirm_success(boto3_client)

def test_succeeds_named_exists(boto3_client):
    """ Successful deployment to a named deployment, component already in the deployment """
    boto3_client.get_deployment.return_value['deploymentStatus'] = 'COMPLETED'
    confirm_success(boto3_client)

def test_succeeds_unnamed_add(boto3_client):
    """ Successful deployment to an unnamed deployment, first time adding the component """
    boto3_client.get_deployment.return_value['deploymentStatus'] = 'COMPLETED'
    del boto3_client.get_deployment.return_value['components'][COMPONENT_NAME]
    del boto3_client.get_deployment.return_value['deploymentName']
    confirm_success(boto3_client)

def test_succeeds_unnamed_exists(boto3_client):
    """ Successful deployment to an unnamed deployment, component already in the deployment """
    boto3_client.get_deployment.return_value['deploymentStatus'] = 'COMPLETED'
    del boto3_client.get_deployment.return_value['deploymentName']
    confirm_success(boto3_client)

def test_succeeds_add_docker_application_manager(boto3_client):
    """ Successful deployment, adding the Docker application manager component """
    boto3_client.get_deployment.return_value['deploymentStatus'] = 'COMPLETED'
    del boto3_client.get_deployment.return_value['components'][COMPONENT_DOCKER_APPLICATION_MANAGER]
    confirm_success(boto3_client)

def test_succeeds_add_secret_manager(boto3_client):
    """ Successful deployment, adding the Docker Secret manager component """
    boto3_client.get_deployment.return_value['deploymentStatus'] = 'COMPLETED'
    del boto3_client.get_deployment.return_value['components'][COMPONENT_SECRET_MANAGER]
    confirm_success(boto3_client)

def test_succeeds_add_secret_manager_no_secret(boto3_client):
    """ Successful deployment, adding a secret to existing Secret manager component """
    boto3_client.get_deployment.return_value['deploymentStatus'] = 'COMPLETED'
    secret_manager = boto3_client.get_deployment.return_value['components'][COMPONENT_SECRET_MANAGER]
    # Erase the secret
    secret_manager['configurationUpdate']['merge'] = '{\"cloudSecrets\":[]}'
    confirm_success(boto3_client)
