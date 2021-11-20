# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Deploys a component version to the Greengrass core device target. This should be
called after create_component_version.py.

Example execution:
python3 deploy_component_version.py 1.0.0 ap-southeast-1 MyCoreDeviceThingName
"""

import argparse
import sys
import time
import boto3
from libs.secret import Secret

ACCOUNT = boto3.client('sts').get_caller_identity().get('Account')
COMPONENT_NAME = 'aws.greengrass.labs.HomeAssistant'
COMPONENT_DOCKER_APPLICATION_MANAGER = 'aws.greengrass.DockerApplicationManager'
COMPONENT_SECRET_MANAGER = 'aws.greengrass.SecretManager'

def get_newest_component_version(component_name):
    """ Gets the newest version of a component """
    component_arn = 'arn:aws:greengrass:{}:aws:components:{}'.format(args.region, component_name)

    try:
        response = greengrassv2_client.list_component_versions(arn=component_arn)
    except Exception as e:
        print('Failed to get component versions for {}\nException: {}'.format(component_name, e))
        sys.exit(1)

    return response['componentVersions'][0]['componentVersion']

def get_deployment_components(name):
    """ Gets the details of the existing deployment """
    try:
        response = greengrassv2_client.list_deployments()
    except Exception as e:
        print('Failed to list deployments\nException: {}'.format(e))
        sys.exit(1)

    components = []

    for deployment in response['deployments']:
        if deployment['deploymentName'] == name:

            try:
                response = greengrassv2_client.get_deployment(deploymentId=deployment['deploymentId'])
                components = response['components']
                break
            except Exception as e:
                print('Failed to get deployment\nException: {}'.format(e))
                sys.exit(1)

    return components

def update_deployment_components(components):
    """ Updates the existing components to the desired versions """

    # If Docker Application manager is not in the deployment, add the latest version
    if COMPONENT_DOCKER_APPLICATION_MANAGER not in components:
        version = get_newest_component_version(COMPONENT_DOCKER_APPLICATION_MANAGER)
        print('Adding {} {} to the deployment'.format(COMPONENT_DOCKER_APPLICATION_MANAGER, version))
        components.update({COMPONENT_DOCKER_APPLICATION_MANAGER: {'componentVersion': version}})

    # If Secret manager is not in the deployment, add the latest version
    if COMPONENT_SECRET_MANAGER not in components:
        version = get_newest_component_version(COMPONENT_SECRET_MANAGER)
        print('Adding {} {} to the deployment'.format(COMPONENT_SECRET_MANAGER, version))
    else:
        # If it's already in the deployment, use the current version
        version = components[COMPONENT_SECRET_MANAGER]['componentVersion']

    # Ensure that Secret Manager is configured for the secret
    components.update({COMPONENT_SECRET_MANAGER: {
        'componentVersion': version,
        'configurationUpdate': {'merge': '{"cloudSecrets":[{"arn":"' + secret_value['ARN'] + '"}]}'}}
    })

    # Add or update our component to the specified version
    if COMPONENT_NAME not in components:
        print('Adding {} {} to the deployment'.format(COMPONENT_NAME, args.version))
    else:
        print('Updating deployment with {} {}'.format(COMPONENT_NAME, args.version))
    components.update({COMPONENT_NAME: {'componentVersion': args.version}})

def create_deployment(name, components):
    """ Creates a deployment of the Home Assistant component to the given Greengrass core device """
    thing_arn = 'arn:aws:iot:{}:{}:thing/{}'.format(args.region, ACCOUNT, args.coreDeviceThingName)

    try:
        response = greengrassv2_client.create_deployment(
            targetArn=thing_arn,
            deploymentName=name,
            components=components
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


parser = argparse.ArgumentParser(description='Deploy a version of the {} component'.format(COMPONENT_NAME))
parser.add_argument('version', help='Version of the component to be created (Example: 1.0.0)')
parser.add_argument('region', help='AWS region (Example: us-east-1)')
parser.add_argument('coreDeviceThingName', help='Greengrass core device to deploy to')
args = parser.parse_args()

greengrassv2_client = boto3.client('greengrassv2', region_name=args.region)

secret = Secret(args.region)
secret_value = secret.get()

print('Deploying version {} to {}'.format(args.version, args.coreDeviceThingName))

deployment_name='Deployment for {}'.format(args.coreDeviceThingName)

# Get the components of the existing deployment (if the deployment already exists)
deployment_components = get_deployment_components(deployment_name)

# Update the components of the existing deployment (or create if the deployment doesn't already exist)
update_deployment_components(deployment_components)

deployment_id = create_deployment(deployment_name, deployment_components)
print('Deployment {} successfully created. Waiting for completion ...'.format(deployment_id))
wait_for_deployment_to_finish(deployment_id)
