# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Custom build script for GDK component build operation. This script is not designed to
be executed directly. It is designed to be used by GDK.

Prior to running "gdk component build", the user should:
1) Update the configuration YAML files in artifacts/config and secrets directories, as appropriate
2) Set the desired AWS region in ggk-config.json.
3) Create or update the Home Assistant secret by running create_config_secret.py

Example execution:
gdk component build
"""

import shutil
import yaml
from libs.secret import Secret
from libs.gdk_config import GdkConfig

DIRECTORY_ARTIFACTS = 'artifacts/'
DIRECTORY_BUILD = 'greengrass-build/artifacts/'
FILE_RECIPE_TEMPLATE = 'recipe.yaml'
FILE_RECIPE = 'greengrass-build/recipes/recipe.yaml'
FILE_ZIP_BASE = 'home-assistant'
FILE_ZIP_EXT = 'zip'
FILE_DOCKER_COMPOSE = DIRECTORY_ARTIFACTS + 'docker-compose.yml'


def create_recipe():
    """ Creates the component recipe, filling in the Docker images and Secret ARN """
    print(f'Creating recipe {FILE_RECIPE}')

    with open(FILE_DOCKER_COMPOSE, encoding="utf-8") as docker_compose_file:
        docker_compose_yaml = yaml.safe_load(docker_compose_file)

    with open(FILE_RECIPE_TEMPLATE, encoding="utf-8") as recipe_template_file:
        recipe_str = recipe_template_file.read()

    recipe_str = recipe_str.replace('COMPONENT_NAME', gdk_config.name())
    if gdk_config.version() != 'NEXT_PATCH':
        recipe_str = recipe_str.replace('COMPONENT_VERSION', gdk_config.version())

    recipe_str = recipe_str.replace('$SECRET_ARN', secret_value['ARN'])
    recipe_str = recipe_str.replace('$DOCKER_IMAGE', docker_compose_yaml['services']['homeassistant']['image'])

    with open(FILE_RECIPE, 'w', encoding="utf-8") as recipe_file:
        recipe_file.write(recipe_str)

    print('Created recipe')

def create_artifacts():
    """ Creates the artifacts archive as a ZIP file """
    file_name = DIRECTORY_BUILD + gdk_config.name() + '/' + gdk_config.version() + '/' + FILE_ZIP_BASE
    print(f'Creating artifacts archive {file_name}')
    shutil.make_archive(file_name, FILE_ZIP_EXT, DIRECTORY_ARTIFACTS)
    print('Created artifacts archive')


gdk_config = GdkConfig()

secret = Secret(gdk_config.region())
secret_value = secret.get()

create_recipe()
create_artifacts()
