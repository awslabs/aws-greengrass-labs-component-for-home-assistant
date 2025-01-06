# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Gets a secret from the Secret manager component
"""

import json
import sys
import traceback
from awsiot.greengrasscoreipc.clientv2 import GreengrassCoreIPCClientV2

def get_secret(secret_id):
    """ Gets a locally stored secret from the Secret Manager component """
    try:
        print('Getting IPC client')
        ipc_client = GreengrassCoreIPCClientV2()

        print('Refreshing and getting secret: ' + secret_id)
        response = ipc_client.get_secret_value(secret_id=secret_id, refresh=True)
        secret_json = json.loads(response.secret_value.secret_string)
        print('Successfully got secret: ' + secret_id)
    except Exception:
        print('Exception', file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    return secret_json
