# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Creates or updates the Home Assisant configuration secret in Secrets Manager.
This puts the Home Assistant secrets.yaml file into an AWS Secrets Manager
secret so that the component can get the secrets securely. If using BYO
SSL or MQTT certificates, these files should be placed into the secrets directory prior
to creating the secret; these are also bundled into the secret. The gdk-config.json file
should be updated with the desired AWS region prior to running this script.

Example execution:
python3 create_config_secret.py
"""

import glob
from libs.secret import Secret
from libs.gdk_config import GdkConfig

DIRECTORY_CONFIG = 'secrets/'

def escape(in_str):
    """ Escapes a string to make it suitable for storage in JSON """
    return in_str.replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

secret_string = '{'

filenames = glob.glob(DIRECTORY_CONFIG + '/**/*.*', recursive=True)

print(f'Files to add to secret: {filenames}')

for filename in filenames:
    with open(filename, encoding="utf-8") as file:
        file_str = file.read()
        secret_string += f'"{filename.replace(DIRECTORY_CONFIG, "")}":"{escape(file_str)}",'

secret_string = secret_string[:-1] + '}'

gdk_config = GdkConfig()

secret = Secret(gdk_config.region())
secret_response = secret.put(secret_string)

print('\nBEFORE DEPLOYING COMPONENT:')
print(f'Add secretsmanager:GetSecretValue for {secret_response["ARN"]} to the Greengrass device role')
