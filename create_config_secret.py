# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Creates or updates the Home Assisant configuration secret in Secrets Manager.
This puts the Home Assistant secrets.yaml file into an AWS Secrets Manager
secret so that the component can get the secrets securely. If using BYO
SSL or MQTT certificates, these files should be placed into the secrets directory prior
to creating the secret; these are also bundled into the secret.

Example execution:
python3 create_config_secret.py ap-southeast-1
"""

import argparse
import glob
from libs.secret import Secret

DIRECTORY_CONFIG = 'secrets/'

def escape(in_str):
    """ Escapes a string to make it suitable for storage in JSON """
    return in_str.replace('"', '\\"').replace('\n', '\\n').replace('\r', '\\r')

parser = argparse.ArgumentParser(description='Create (or update) a secret to '\
                                                'hold the Home Assistant secrets.yaml '\
                                                'and optional certificates securely')
parser.add_argument('region', help='AWS region (Example: us-east-1)')
args = parser.parse_args()

secret_string = '{'

filenames = glob.glob(DIRECTORY_CONFIG + '/**/*.*', recursive=True)

print('Files to add to secret: {}'.format(filenames))

for filename in filenames:
    with open(filename, encoding="utf-8") as file:
        file_str = file.read()
        secret_string += '"{}":"{}",'.format(filename.replace(DIRECTORY_CONFIG, ''), escape(file_str))

secret_string = secret_string[:-1] + '}'

secret = Secret(args.region)
secret.put(secret_string)
