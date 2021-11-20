#!/bin/bash

# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

# This script is designed for quickstart. 
#
# Before running the script, users must deploy Greengrass V2 to a physical Linux machine or 
# instance (can be EC2). 
#
# This script will:
# 1) Install required Python packages.
# 2) Upload the secure parts of the Home Assistant configuration to Secrets Manager.
# 3) Create a new component version.
# 4) Deploy the new component version to the Greengrass core.
# 5) Run Robot Framework integration tests to confirm that Home Assistant is running under Greengrass.
#
# Example execution:
# bash quickstart.sh ap-southeast-1 1.0.0 GGHomeAssistant

# Fail if we don't get the correct number of arguments
if [ "$#" -ne 6 ]; then
    echo "Usage: bash quickstart.sh region componentVersion GGCoreDeviceName"
    exit 1
fi

# Exit when any command fails
set -e

banner() {
    echo -e "\n---------- $1 ----------"
}

# Install requirements
banner "Install required packages"
pip3 install -r requirements.txt

# Create the Home Assistant configuration secret in Secrets Manager to hold the secrets.yaml configuration securely
banner "Create or update the Home Assistant configuration secret" 
python3 create_config_secret.py $1

# Create a new component version
banner "Create a Greengrass component version"
python3 create_component_version.py $2 $1

# Don't let them proceed until they've added the S3 bucket and secret permissions to the Greengrass device role
done=0
while [ $done -eq 0 ]; do
    echo "Have you added the bucket and secret permissions to the Greengrass device role? ('Press 'y' for yes or 'x' to exit)"
    read -rsn1 keypress

    if [ "$keypress" = "x" ]; then
        echo "Deployment not performed"
        exit 1
    elif [ "$keypress" = "y" ]; then
        done=1
    fi
done

# Deploy the new component version
banner "Deploy the Greengrass component version" 
python3 deploy_component_version.py $2 $1 $3
