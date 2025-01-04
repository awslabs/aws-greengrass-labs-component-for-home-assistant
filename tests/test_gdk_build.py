"""
Unit tests for the gdk_build.py script
"""
import runpy
import pytest

NAME = 'FooBar'
VERSION = 'rubbish'
REGION = 'neverland'

DIRECTORY_ARTIFACTS = 'artifacts/'
DIRECTORY_BUILD = 'greengrass-build/artifacts/'
FILE_RECIPE_TEMPLATE = 'recipe.yaml'
FILE_RECIPE = 'greengrass-build/recipes/recipe.yaml'
FILE_DOCKER_COMPOSE = DIRECTORY_ARTIFACTS + 'docker-compose.yml'
FILE_ZIP_BASE = 'home-assistant'
FILE_ZIP_EXT = 'zip'

SECRET_ARN = 'rhubarb'
IMAGE = 'homeassistant/home-assistant:latest'

def recipe(name, version, secret_arn, image):
    """ Create a recipe string fragment """
    recipe_str =\
    f"""
    {{
    "ComponentName": "{name}",
    "ComponentVersion": "{version}",
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
    """

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


@pytest.fixture(name='gdk_config')
def fixture_gdk_config(mocker):
    """ Mock the GDK config """
    gdk_config_class = mocker.patch('libs.gdk_config.GdkConfig')
    gdk_config = gdk_config_class.return_value
    gdk_config.name.return_value = NAME
    gdk_config.version.return_value = VERSION

    yield gdk_config

    gdk_config_class.assert_called_once()


@pytest.fixture(name='secret')
def fixture_secret(mocker):
    """ Mock the GDK config """
    secret_class = mocker.patch('libs.secret.Secret')
    secret = secret_class.return_value
    secret.get.return_value = {'SecretString':'foobar', 'ARN': SECRET_ARN}

    yield secret

    secret_class.assert_called_once()


@pytest.fixture(name='file')
def fixture_file(mocker):
    """ Mock the file handling """
    # Complicated mock: four calls to the file mock, each needing their own side effect
    m = m_docker = mocker.mock_open(read_data=docker_compose(IMAGE))
    m_recipe_template = mocker.mock_open(read_data=recipe('COMPONENT_NAME', 'COMPONENT_VERSION',\
                                                          '$SECRET_ARN', '$DOCKER_IMAGE'))
    m_recipe = mocker.mock_open()
    m.side_effect=[m_docker.return_value, m_recipe_template.return_value, m_recipe.return_value, m_recipe.return_value]
    file = mocker.patch('builtins.open', m)

    yield file

    file.assert_any_call(FILE_DOCKER_COMPOSE, encoding="utf-8")
    file.assert_any_call(FILE_RECIPE_TEMPLATE, encoding="utf-8")
    file.assert_any_call(FILE_RECIPE, 'w', encoding="utf-8")


def test_specific_version(mocker, gdk_config, secret, file):
    """ Confirm GDK build correctly assembles the recipe and the archive when version is specified in GDK config """
    make_archive = mocker.patch('shutil.make_archive')
    runpy.run_module('gdk_build')

    recipe_str = recipe(NAME, VERSION, SECRET_ARN, IMAGE)
    file().write.assert_called_once_with(recipe_str)
    archive_name = DIRECTORY_BUILD + NAME + '/' + VERSION + '/' + FILE_ZIP_BASE
    make_archive.assert_called_once_with(archive_name, FILE_ZIP_EXT, DIRECTORY_ARTIFACTS)
    assert gdk_config.name.call_count == 2
    assert gdk_config.version.call_count == 3
    assert gdk_config.region.call_count == 1
    assert secret.get.call_count == 1


def test_next_patch(mocker, gdk_config, secret, file):
    """ Confirm GDK build correctly assembles the recipe and the archive when NEXT_PATCH is specified in GDK config """
    make_archive = mocker.patch('shutil.make_archive')
    gdk_config.version.return_value = 'NEXT_PATCH'
    runpy.run_module('gdk_build')

    recipe_str = recipe(NAME, 'COMPONENT_VERSION', SECRET_ARN, IMAGE)
    file().write.assert_called_once_with(recipe_str)
    archive_name = DIRECTORY_BUILD + NAME + '/NEXT_PATCH/' + FILE_ZIP_BASE
    make_archive.assert_called_once_with(archive_name, FILE_ZIP_EXT, DIRECTORY_ARTIFACTS)
    assert gdk_config.name.call_count == 2
    assert gdk_config.version.call_count == 2
    assert gdk_config.region.call_count == 1
    assert secret.get.call_count == 1
