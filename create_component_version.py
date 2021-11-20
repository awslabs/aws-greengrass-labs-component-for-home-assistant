# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Creates a new version of the Home Assistant component in the Greengrass cloud service.

Prior to running this script, the user should:
1) Update the configuration YAML files in artifacts/config and secrets directories, as appropriate
2) Create or update the Home Assistant secret by running create_config_secret.py

Example execution:
python3 create_component_version.py 1.0.0 ap-southeast-1
"""

import argparse
import json
import sys
import shutil
import os
import yaml
import boto3
from libs.secret import Secret

ACCOUNT = boto3.client('sts').get_caller_identity().get('Account')
COMPONENT_NAME = 'aws.greengrass.labs.HomeAssistant'
BUCKET_NAME = 'greengrass-home-assistant-' + ACCOUNT
DIRECTORY_ARTIFACTS = 'artifacts/'
DIRECTORY_RECIPES = 'recipes/'
DIRECTORY_BUILD = 'build/'
FILE_RECIPE_TEMPLATE = DIRECTORY_RECIPES + COMPONENT_NAME + '.json'
FILE_ZIP_BASE = 'home-assistant'
FILE_ZIP_EXT = 'zip'
FILE_DOCKER_COMPOSE = DIRECTORY_ARTIFACTS + 'docker-compose.yml'


def check_component_version_exists():
    """ Determines whether the proposed component version already exists in the Greengrass cloud service """
    component_arn = 'arn:aws:greengrass:{}:{}:components:{}:versions:{}'\
                    .format(args.region, ACCOUNT, COMPONENT_NAME, args.version)
    try:
        greengrassv2_client.get_component(arn=component_arn)
        print('Component version {} already exists'.format(args.version))
        sys.exit(1)
    except Exception:
        pass

def create_bucket(bucket_name):
    """ Creates the artifacts bucket if it doesn't already exist """
    print('Creating artifacts bucket {}'.format(bucket_name))
    if bucket_exists(bucket_name):
        print('Bucket {} already exists'.format(bucket_name))
        return
    try:
        if args.region is None or args.region == "us-east-1":
            s3_client.create_bucket(Bucket=bucket_name)
        else:
            location = {'LocationConstraint': args.region}
            s3_client.create_bucket(Bucket=bucket_name, CreateBucketConfiguration=location)
    except Exception as e:
        print('Failed to create artifacts bucket\nException: {}'.format(e))
        sys.exit(1)
    print('Successfully created artifacts bucket')

def bucket_exists(bucket_name):
    """ Determines if the artifacts bucket already exists """
    response = s3_client.list_buckets()
    if response is not None:
        for bucket in response['Buckets']:
            if bucket['Name'] == bucket_name:
                return True

    return False

def create_build_directory():
    """ Creates a directory in which the artifacts archive and recipe file shall be built """
    try:
        os.mkdir(DIRECTORY_BUILD)
    except FileExistsError:
        pass

def create_recipe():
    """ Creates the component recipe file as a string """
    recipe_file_name = DIRECTORY_BUILD + COMPONENT_NAME + '-' + args.version + '.json'
    print('Creating recipe {}'.format(recipe_file_name))

    with open(FILE_DOCKER_COMPOSE, encoding="utf-8") as docker_compose_file:
        docker_compose_yaml = yaml.safe_load(docker_compose_file)

    with open(FILE_RECIPE_TEMPLATE, encoding="utf-8") as recipe_template_file:
        recipe_str = recipe_template_file.read()

    recipe_str = recipe_str.replace('$COMPONENT_VERSION', args.version)
    recipe_str = recipe_str.replace('$SECRET_ARN', secret_value['ARN'])
    recipe_str = recipe_str.replace('$BUCKET_NAME', BUCKET_NAME)
    recipe_str = recipe_str.replace('$DOCKER_IMAGE', docker_compose_yaml['services']['homeassistant']['image'])

    recipe_json = json.loads(recipe_str)
    recipe_str = json.dumps(recipe_json, indent=2)

    with open(recipe_file_name, 'w', encoding="utf-8") as recipe_file:
        recipe_file.write(recipe_str)

    print('Created recipe')
    return recipe_str

def create_artifacts():
    """ Creates the artifacts archive as a ZIP file """
    file_name = DIRECTORY_BUILD + args.version + '/' + FILE_ZIP_BASE
    print('Creating artifacts archive {}'.format(file_name))
    shutil.make_archive(file_name, FILE_ZIP_EXT, DIRECTORY_ARTIFACTS)
    print('Created artifacts archive')
    return file_name + '.' + FILE_ZIP_EXT

def upload_artifacts(file_name, bucket_name, object_name):
    """ Uploads the artifacts archive to S3 """
    print('Uploading artifacts to {}/{}'.format(bucket_name, object_name))
    try:
        s3_client.upload_file(file_name, bucket_name, object_name)
    except Exception as e:
        print('Failed to upload artifacts\nException: {}'.format(e))
        sys.exit(1)
    print('Successfully uploaded artifacts')

def create_component_version(recipe_str):
    """ Creates a new component version in the Greengrass cloud service """
    print('Creating component {} version {}'.format(COMPONENT_NAME, args.version))
    try:
        greengrassv2_client.create_component_version(inlineRecipe=recipe_str)
    except Exception as e:
        print('Failed to create component version\nException: {}'.format(e))
        sys.exit(1)
    print('Successfully created component version')


parser = argparse.ArgumentParser(description='Create a version of the {} component'.format(COMPONENT_NAME))
parser.add_argument('version', help='Version of the component to be created (Example: 1.0.0)')
parser.add_argument('region', help='AWS region (Example: us-east-1)')
args = parser.parse_args()

BUCKET_NAME += '-' + args.region

s3_client = boto3.client('s3')
greengrassv2_client = boto3.client('greengrassv2', region_name=args.region)

secret = Secret(args.region)
secret_value = secret.get()

check_component_version_exists()
create_bucket(BUCKET_NAME)
create_build_directory()
recipe = create_recipe()
artifacts_file_name = create_artifacts()
upload_artifacts(artifacts_file_name, BUCKET_NAME, artifacts_file_name.replace(DIRECTORY_BUILD, ''))
create_component_version(recipe)

print('\nBEFORE DEPLOYING COMPONENT:')
print('1) Add s3:GetObject for arn:aws:s3:::{} to the Greengrass device role'.format(BUCKET_NAME))
print('2) Add secretsmanager:GetSecretValue for {} to the Greengrass device role'.format(secret_value['ARN']))
