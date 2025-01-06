# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Initializes and installs the Home Assistant component on the Greengrass edge runtime.

Example execution:
python3 install.py arn:aws:secretsmanager:REGION:ACCOUNT:secret:greengrass-home-assistant-ID
"""

import sys
import os
from secret import get_secret

def create_files_from_secret():
    """ Extracts files from the configuration secret and creates them on disk """
    print('Creating files from secret')
    for filename, contents in secret.items():
        print(f'Creating {filename}')
        if '/' in filename:
            os.makedirs(os.path.dirname(filename), exist_ok=True)
        with open(filename, 'w', encoding="utf-8") as file:
            file.write(contents)

if len(sys.argv) == 1:
    print('Secret ARN argument is missing', file=sys.stderr)
    sys.exit(1)

# Get the secure configuration from Secret Manager
secret = get_secret(sys.argv[1])

os.chdir('config')
print('getcwd: ', os.getcwd())

# Extracts secrets.yaml and any optional TLS certificates
create_files_from_secret()
