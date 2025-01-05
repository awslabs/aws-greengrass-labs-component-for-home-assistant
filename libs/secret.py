# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

"""
API for Home Assistant configuration secret in Secrets Manager.
"""

import boto3

class Secret():
    """ API for Home Assistant configuration secret in Secrets Manager. """

    SECRET_NAME = 'greengrass-home-assistant'
    SECRET_DESCRIPTION = 'Secure configuration for the Home Assistant component on Greengrass'

    def __init__(self, region):
        self.secretsmanager_client = boto3.client('secretsmanager', region_name=region)

    def get(self):
        """ Gets a secret from Secrets Manager """
        try:
            print(f'Getting the Home Assistant secret {self.SECRET_NAME}')
            response = self.secretsmanager_client.get_secret_value(SecretId=self.SECRET_NAME)
        except Exception as e:
            print(f'Failed to get secret\nException: {e}')
            raise e

        return response

    def put(self, secret_string):
        """ Creates or updates the Home Assistant secret in Secrets Manager """
        if self.exists():
            try:
                print(f'Updating the Home Assistant secret {self.SECRET_NAME}')
                response = self.secretsmanager_client.update_secret(SecretId=self.SECRET_NAME,
                                                                    SecretString=secret_string,
                                                                    Description=self.SECRET_DESCRIPTION)
            except Exception as e:
                print(f'Failed to update the Home Assistant secret\nException: {e}')
                raise e
            print('Successfully updated the Home Assistant secret')
        else:
            try:
                print(f'Creating Home Assistant secret {self.SECRET_NAME}')
                response = self.secretsmanager_client.create_secret(Name=self.SECRET_NAME,
                                                                    SecretString=secret_string,
                                                                    Description=self.SECRET_DESCRIPTION)
            except Exception as e:
                print(f'Failed to create the Home Assistant secret\nException: {e}')
                raise e
            print('Successfully created the Home Assistant secret')

        return response

    def exists(self):
        """ Determines whether the Home Assistant secret already exists in Secrets Manager """
        response = self.secretsmanager_client.list_secrets()
        if response is not None:
            for secret in response['SecretList']:
                if secret['Name'] == self.SECRET_NAME:
                    return True

        return False
