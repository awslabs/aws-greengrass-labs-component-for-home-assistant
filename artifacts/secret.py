# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Gets a secret from the Secret manager component
"""

import json
import sys
import traceback
import awsiot.greengrasscoreipc
from awsiot.greengrasscoreipc.model import GetSecretValueRequest

def get_secret(secret_id):
    """ Gets a locally stored secret from the Secret Manager component """
    try:
        print('Getting IPC client')
        ipc_client = awsiot.greengrasscoreipc.connect()

        print('Getting secret: ' + secret_id)
        request = GetSecretValueRequest()
        request.secret_id = secret_id
        operation = ipc_client.new_get_secret_value()
        operation.activate(request)
        future_response = operation.get_response()

        response = future_response.result(timeout=10)
        secret_json = json.loads(response.secret_value.secret_string)
        print('Successfully got secret: ' + secret_id)
    except Exception:
        print('Exception', file=sys.stderr)
        traceback.print_exc()
        sys.exit(1)

    return secret_json
