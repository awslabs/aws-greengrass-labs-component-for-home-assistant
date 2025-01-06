# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Deploys a component version to the Greengrass core device target. This should be
called after "gdk component build" and "gdk component publish".

Example execution:
python3 deploy_component_version.py 1.0.0 MyCoreDeviceThingName
"""

import argparse
import json
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
    component_arn = f'arn:aws:greengrass:{gdk_config.region()}:aws:components:{component_name}'

    try:
        response = greengrassv2_client.list_component_versions(arn=component_arn)
    except Exception as e:
        print(f'Failed to get component versions for {component_name}\nException: {e}')
        sys.exit(1)

    return response['componentVersions'][0]['componentVersion']

def get_deployment():
    """ Gets the details of the existing deployment """
    thing_arn = f'arn:aws:iot:{gdk_config.region()}:{ACCOUNT}:thing/{args.coreDeviceThingName}'

    print(f'Searching for existing single Thing deployment for {args.coreDeviceThingName}')

    try:
        # Get the latest deployment for the specified core device name
        response = greengrassv2_client.list_deployments(
            targetArn=thing_arn,
            historyFilter='LATEST_ONLY',
            maxResults=1
        )
    except Exception as e:
        print(f'Failed to list deployments\nException: {e}')
        sys.exit(1)

    # We expect to update an existing deployment, not create a new one
    if len(response['deployments']) == 0:
        print('No existing Thing deployment for this Core Device. Abort.')
        sys.exit(1)

    # We expect at most one result in the list
    deployment_id = response['deployments'][0]['deploymentId']

    try:
        response = greengrassv2_client.get_deployment(deploymentId=deployment_id)

        if 'deploymentName' in response:
            print(f'Found existing named deployment "{response["deploymentName"]}"')
        else:
            print(f'Found existing unnamed deployment {deployment_id}')
    except Exception as e:
        print(f'Failed to get deployment\nException: {e}')
        sys.exit(1)

    return response

def update_deployment(deployment):
    """ Updates the current deplyment with the desired versions of the components """

    # If Docker Application manager is not in the deployment, add the latest version
    if COMPONENT_DOCKER_APPLICATION_MANAGER not in deployment['components']:
        version = get_newest_component_version(COMPONENT_DOCKER_APPLICATION_MANAGER)
        print(f'Adding {COMPONENT_DOCKER_APPLICATION_MANAGER} {version} to the deployment')
        deployment['components'].update({COMPONENT_DOCKER_APPLICATION_MANAGER: {'componentVersion': version}})

    # If Secret manager is not in the deployment, add the latest version
    if COMPONENT_SECRET_MANAGER not in deployment['components']:
        version = get_newest_component_version(COMPONENT_SECRET_MANAGER)
        print(f'Adding {COMPONENT_SECRET_MANAGER} {version} to the deployment')
        cloud_secrets = [{"arn": secret_value['ARN']}]
    else:
        # If it's already in the deployment, use the current version
        version = deployment['components'][COMPONENT_SECRET_MANAGER]['componentVersion']
        merge_str = deployment['components'][COMPONENT_SECRET_MANAGER]['configurationUpdate']['merge']
        cloud_secrets = json.loads(merge_str)['cloudSecrets']

        # Add our secret to the list of configured secrets
        if secret_value['ARN'] not in merge_str:
            print(f'Adding secret {secret_value["ARN"]} to Secret Manager configuration')
            cloud_secrets.append({"arn": secret_value['ARN']})

    # Update Secret Manager with the appropriate version and configuration
    deployment['components'].update({COMPONENT_SECRET_MANAGER: {
        'componentVersion': version,
        'configurationUpdate': {'merge': '{"cloudSecrets":' + json.dumps(cloud_secrets) + '}'}}
    })

    # Add or update our component to the specified version
    if gdk_config.name() not in deployment['components']:
        print(f'Adding {gdk_config.name()} {args.version} to the deployment')
    else:
        print(f'Updating deployment with {gdk_config.name()} {args.version}')
    deployment['components'].update({gdk_config.name(): {'componentVersion': args.version}})

def create_deployment(deployment):
    """ Creates a deployment of the component to the given Greengrass core device """

    # Give the deployment a name if it doesn't already have one
    if 'deploymentName' in deployment:
        deployment_name = deployment['deploymentName']
    else:
        deployment_name = f'Deployment for {args.coreDeviceThingName}'
        print(f'Renaming deployment to "{deployment_name}"')

    try:
        # We deploy to a single Thing and hence without an IoT job configuration
        # Deploy with default deployment policies and no tags
        response = greengrassv2_client.create_deployment(
            targetArn=deployment['targetArn'],
            deploymentName=deployment_name,
            components=deployment['components']
        )
    except Exception as e:
        print(f'Failed to create deployment\nException: {e}')
        sys.exit(1)

    return response['deploymentId']

def wait_for_deployment_to_finish(deploy_id):
    """ Waits for the deployment to complete """
    deployment_status = 'ACTIVE'
    snapshot = time.time()

    while deployment_status == 'ACTIVE' and (time.time() - snapshot) < 900:
        try:
            response = greengrassv2_client.get_deployment(deploymentId=deploy_id)
            deployment_status = response['deploymentStatus']
        except Exception as e:
            print(f'Failed to get deployment\nException: {e}')
            sys.exit(1)

    if deployment_status == 'COMPLETED':
        print(f'Deployment completed successfully in {time.time() - snapshot:.1f} seconds')
    elif deployment_status == 'ACTIVE':
        print('Deployment timed out')
        sys.exit(1)
    else:
        print(f'Deployment error: {deployment_status}')
        sys.exit(1)


gdk_config = GdkConfig()

parser = argparse.ArgumentParser(description=f'Deploy a version of the {gdk_config.name()} component')
parser.add_argument('version', help='Version of the component to be deployed (Example: 1.0.0)')
parser.add_argument('coreDeviceThingName', help='Greengrass core device to deploy to')
args = parser.parse_args()

greengrassv2_client = boto3.client('greengrassv2', region_name=gdk_config.region())

secret = Secret(gdk_config.region())
secret_value = secret.get()

print(f'Attempting deployment of version {args.version} to core device {args.coreDeviceThingName}')

# Get the latest (single Thing) deployment for the specified core device
current_deployment = get_deployment()

# Update the components of the current deployment
update_deployment(current_deployment)

# Create a new deployment
new_deployment_id = create_deployment(current_deployment)
print(f'Deployment {new_deployment_id} successfully created. Waiting for completion ...')
wait_for_deployment_to_finish(new_deployment_id)
