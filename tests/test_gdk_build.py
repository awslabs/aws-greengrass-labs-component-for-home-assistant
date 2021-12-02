# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Unit tests for the gdk_build.py script
"""
import json
import runpy

NAME = 'FooBar'
VERSION = 'rubbish'
REGION = 'neverland'

DIRECTORY_ARTIFACTS = 'artifacts/'
DIRECTORY_BUILD = 'greengrass-build/artifacts/'
FILE_RECIPE_TEMPLATE = 'recipe.json'
FILE_RECIPE = 'greengrass-build/recipes/recipe.json'
FILE_DOCKER_COMPOSE = DIRECTORY_ARTIFACTS + 'docker-compose.yml'
FILE_ZIP_BASE = 'home-assistant'
FILE_ZIP_EXT = 'zip'

SECRET_ARN = 'rhubarb'
IMAGE = 'homeassistant/home-assistant:latest'

def recipe(secret_arn, image):
    """ Create a recipe string fragment """
    recipe_str =\
    """
    {{
    "ComponentConfiguration": {{
        "DefaultConfiguration": {{
        "secretArn": "{secret_arn}"
        }}
    }},
    "Manifests": [
        {{
        "Artifacts": [
            {{
            "URI": "docker:{image}"
            }}
        ]
        }}
    ]
    }}
    """.format(secret_arn=secret_arn, image=image)

    recipe_json = json.loads(recipe_str)
    recipe_str = json.dumps(recipe_json, indent=2)

    return recipe_str


def docker_compose(image):
    """ Create a Docker compose fragment """
    docker_compose_str =\
    """
    services:
        homeassistant:
            image: {image}
    """.format(image=image)

    return docker_compose_str


def test_gdk_build(mocker):
# pylint: disable-msg=too-many-locals
    """ Confirm that the GDK build correctly assembles the recipe and the archive """
    gdk_config_init = mocker.patch('libs.gdk_config.GdkConfig.__init__', return_value=None)
    gdk_config_name = mocker.patch('libs.gdk_config.GdkConfig.name', return_value=NAME)
    gdk_config_version = mocker.patch('libs.gdk_config.GdkConfig.version', return_value=VERSION)
    gdk_config_region = mocker.patch('libs.gdk_config.GdkConfig.region', return_value=REGION)
    secret_value = {'SecretString':'foobar', 'ARN': SECRET_ARN}
    secret_init = mocker.patch('libs.secret.Secret.__init__', return_value=None)
    secret_get = mocker.patch('libs.secret.Secret.get', return_value=secret_value)

    # Complicated mock: four calls to the file mock, each needing their own side effect
    m = m_docker = mocker.mock_open(read_data=docker_compose(IMAGE))
    m_recipe_template = mocker.mock_open(read_data=recipe('$SECRET_ARN', '$DOCKER_IMAGE'))
    m_recipe = mocker.mock_open()
    m.side_effect=[m_docker.return_value, m_recipe_template.return_value, m_recipe.return_value, m_recipe.return_value]

    file = mocker.patch('builtins.open', m)
    make_archive = mocker.patch('shutil.make_archive')
    runpy.run_module('gdk_build')

    file.assert_any_call(FILE_DOCKER_COMPOSE, encoding="utf-8")
    file.assert_any_call(FILE_RECIPE_TEMPLATE, encoding="utf-8")
    file.assert_any_call(FILE_RECIPE, 'w', encoding="utf-8")
    recipe_str = recipe(SECRET_ARN, IMAGE)
    file().write.assert_called_once_with(recipe_str)
    archive_name = DIRECTORY_BUILD + NAME + '/' + VERSION + '/' + FILE_ZIP_BASE
    make_archive.assert_called_once_with(archive_name, FILE_ZIP_EXT, DIRECTORY_ARTIFACTS)
    gdk_config_init.assert_called_once()
    gdk_config_name.assert_called_once()
    gdk_config_version.assert_called_once()
    gdk_config_region.assert_called_once()
    secret_init.assert_called_once_with(REGION)
    secret_get.assert_called_once()
