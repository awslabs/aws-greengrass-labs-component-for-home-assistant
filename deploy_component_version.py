# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Deploys a component version to the Greengrass core device target. This should be
called after "gdk component build" and "gdk component publish".

Example execution:
python3 deploy_component_version.py 1.0.0 MyCoreDeviceThingName
"""

import argparse
import sys
import time
import boto3
from libs.secret import Secret
from libs.gdk_config import GdkConfig

ACCOUNT = boto3.client('sts').get_caller_identity().get('Account')
COMPONENT_DOCKER_APPLICATION_MANAGER = 'aws.greengrass.DockerApplicationManager'
COMPONENT_SECRET_MANAGER = 'aws.greengrass.SecretManager'

def get_newest_component_version(component_name):
    """ Gets the newest version of a component """
    component_arn = 'arn:aws:greengrass:{}:aws:components:{}'.format(gdk_config.region(), component_name)

    try:
        response = greengrassv2_client.list_component_versions(arn=component_arn)
    except Exception as e:
        print('Failed to get component versions for {}\nException: {}'.format(component_name, e))
        sys.exit(1)

    return response['componentVersions'][0]['componentVersion']

def get_deployment():
    """ Gets the details of the existing deployment """
    thing_arn = 'arn:aws:iot:{}:{}:thing/{}'.format(gdk_config.region(), ACCOUNT, args.coreDeviceThingName)

    try:
        # Get the latest deployment for the specified core device name
        response = greengrassv2_client.list_deployments(
            targetArn=thing_arn,
            historyFilter='LATEST_ONLY',
            maxResults=1
        )
    except Exception as e:
        print('Failed to list deployments\nException: {}'.format(e))
        sys.exit(1)

    # We expect to update an existing deployment, not create a new one
    if len(response['deployments']) == 0:
        print('No existing deployment for this Core Device. Abort!')
        sys.exit(1)

    # We expect at most one result in the list
    deployment_id = response['deployments'][0]['deploymentId']

    try:
        response = greengrassv2_client.get_deployment(deploymentId=deployment_id)
    except Exception as e:
        print('Failed to get deployment\nException: {}'.format(e))
        sys.exit(1)

    return response

def update_deployment(deployment):
    """ Updates the current deplyment with the desired versions of the components """

    # If Docker Application manager is not in the deployment, add the latest version
    if COMPONENT_DOCKER_APPLICATION_MANAGER not in deployment['components']:
        version = get_newest_component_version(COMPONENT_DOCKER_APPLICATION_MANAGER)
        print('Adding {} {} to the deployment'.format(COMPONENT_DOCKER_APPLICATION_MANAGER, version))
        deployment['components'].update({COMPONENT_DOCKER_APPLICATION_MANAGER: {'componentVersion': version}})

    # If Secret manager is not in the deployment, add the latest version
    if COMPONENT_SECRET_MANAGER not in deployment['components']:
        version = get_newest_component_version(COMPONENT_SECRET_MANAGER)
        print('Adding {} {} to the deployment'.format(COMPONENT_SECRET_MANAGER, version))
    else:
        # If it's already in the deployment, use the current version
        version = deployment['components'][COMPONENT_SECRET_MANAGER]['componentVersion']

    # Ensure that Secret Manager is configured for the secret
    deployment['components'].update({COMPONENT_SECRET_MANAGER: {
        'componentVersion': version,
        'configurationUpdate': {'merge': '{"cloudSecrets":[{"arn":"' + secret_value['ARN'] + '"}]}'}}
    })

    # Add or update our component to the specified version
    if gdk_config.name() not in deployment['components']:
        print('Adding {} {} to the deployment'.format(gdk_config.name(), args.version))
    else:
        print('Updating deployment with {} {}'.format(gdk_config.name(), args.version))
    deployment['components'].update({gdk_config.name(): {'componentVersion': args.version}})

def create_deployment(deployment):
    """ Creates a deployment of the component to the given Greengrass core device """

    # Give the deployment a name if it doesn't already have one
    if 'deploymentName' in deployment:
        deployment_name = deployment['deploymentName']
    else:
        deployment_name = 'Deployment for {}'.format(args.coreDeviceThingName)

    try:
        # We deploy to a single Thing and hence without an IoT job configuration
        # Deploy with default deployment policies and no tags
        response = greengrassv2_client.create_deployment(
            targetArn=deployment['targetArn'],
            deploymentName=deployment_name,
            components=deployment['components']
        )
    except Exception as e:
        print('Failed to create deployment\nException: {}'.format(e))
        sys.exit(1)

    return response['deploymentId']

def wait_for_deployment_to_finish(deploy_id):
    """ Waits for the deployment to complete """
    deployment_status = 'ACTIVE'
    snapshot = time.time()

    while deployment_status == 'ACTIVE' and (time.time() - snapshot) < 300:
        try:
            response = greengrassv2_client.get_deployment(deploymentId=deploy_id)
            deployment_status = response['deploymentStatus']
        except Exception as e:
            print('Failed to get deployment\nException: {}'.format(e))
            sys.exit(1)

    if deployment_status == 'COMPLETED':
        print('Deployment completed successfully in {:.1f} seconds'.format(time.time() - snapshot))
    elif deployment_status == 'ACTIVE':
        print('Deployment timed out')
        sys.exit(1)
    else:
        print('Deployment error: {}'.format(deployment_status))
        sys.exit(1)


gdk_config = GdkConfig()

parser = argparse.ArgumentParser(description='Deploy a version of the {} component'.format(gdk_config.name()))
parser.add_argument('version', help='Version of the component to be deployed (Example: 1.0.0)')
parser.add_argument('coreDeviceThingName', help='Greengrass core device to deploy to')
args = parser.parse_args()

greengrassv2_client = boto3.client('greengrassv2', region_name=gdk_config.region())

secret = Secret(gdk_config.region())
secret_value = secret.get()

print('Deploying version {} to core device {}'.format(args.version, args.coreDeviceThingName))

# Get the latest (singe Thing) deployment for the specified core device
current_deployment = get_deployment()

# Update the components of the current deployment
update_deployment(current_deployment)

# Create a new deployment
new_deployment_id = create_deployment(current_deployment)
print('Deployment {} successfully created. Waiting for completion ...'.format(new_deployment_id))
wait_for_deployment_to_finish(new_deployment_id)
