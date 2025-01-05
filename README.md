# AWS IoT Greengrass V2 Community Component - Home Assistant

[Home Assistant](https://www.home-assistant.io/) is an [open-source home automation solution](https://github.com/home-assistant/core). 

This repository packages Home Assistant into an [AWS IoT Greengrass V2](https://docs.aws.amazon.com/greengrass/v2/developerguide/what-is-iot-greengrass.html) component named **aws.greengrass.labs.HomeAssistant**. This enables use cases where you requre Home Assistant for local control, but also require integration with AWS services at the edge and in the cloud. 

Using the Home Assistant [MQTT Integration](https://www.home-assistant.io/integrations/mqtt/), Home Assistant can publish and subscribe to topics on [AWS IoT Core](https://docs.aws.amazon.com/iot/latest/developerguide/mqtt.html) and/or on the Greengrass local [EMQX MQTT broker](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-broker-emqx-component.html) or [Moquette MQTT broker](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-broker-moquette-component.html). This allows integration with the cloud, with other Greengrass components on the same device and/or with other devices on the local network. Home Assistant can therefore leverage [AWS-managed Greengrass components](https://docs.aws.amazon.com/greengrass/v2/developerguide/public-components.html), [custom Greengrass components](https://docs.aws.amazon.com/greengrass/v2/developerguide/develop-greengrass-components.html), [community Greengrass components](https://github.com/orgs/awslabs/teams/aws-greengrass-labs/repositories) and AWS services to deliver powerful home automation solutions that extend Home Assistant's capabilities.

# Table of Contents
* [Architecture](#architecture)
* [Repository Contents](#repository-contents)
* [Requirements and Prerequisites](#requirements-and-prerequisites)
  * [Greengrass Core Device](#greengrass-core-device)
    * [Platform](#platform)
    * [Edge Runtime](#edge-runtime)
    * [Docker Requirements](#docker-requirements)
    * [Python Requirements](#python-requirements)
  * [Greengrass Cloud Services](#greengrass-cloud-services)
    * [Core Device Role](#core-device-role)
  * [Developer Machine](#developer-machine)
    * [AWS CLI](#aws-cli)
    * [Python](#python)
    * [GDK CLI](#gdk-cli)
    * [Bash](#bash)
    * [jq](#jq)
* [Getting Started](#getting-started)
  * [Quickstart](#quickstart)
  * [Slowstart](#slowstart)
    * [Manual Deployment](#manual-deployment)
    * [Example Execution](#example-execution)
    * [CI/CD Pipeline](#cicd-pipeline)
* [Home Assistant Configuration Tips](#home-assistant-configuration-tips)
  * [Defaults](#defaults)
  * [Machine Specific Images](#machine-specific-images)
  * [MQTT](#mqtt)
    * [AWS IoT Core](#aws-iot-core)
    * [Greengrass MQTT Broker](#greengrass-mqtt-broker)
* [Operations](#operations)
  * [Clean Uninstall](#clean-uninstall)
  * [Data Backup](#data-backup)
* [Troubleshooting](#troubleshooting)
  * [Troubleshooting Tools](#troubleshooting-tools)
    * [Core Device Log Files](#core-device-log-files)
    * [Greengrass CLI](#greengrass-cli)
    * [Docker Container Logs](#docker-container-logs)
  * [Common Failures](#common-failures)
    * [Wrong Docker Image Architecture](#wrong-docker-image-architecture)
    * [Secret Configuration Changes Not Deployed](#secret-configuration-changes-not-deployed)
* [Development](#development)
  * [Static Analysis](#static-analysis)
  * [Unit Tests](#unit-tests)

# Architecture

An overview of the system architecture is presented below.

![ggv2-ha-architecture](images/ggv2-ha-architecture.png)

The **aws.greengrass.labs.HomeAssistant** component is a thin wrapper around a conventional [Home Assistant Container](https://www.home-assistant.io/installation/) deployment. 

Home Assistant Container is delivered as a Docker image on [Docker Hub](https://hub.docker.com/r/homeassistant/home-assistant) and on [GitHub](https://github.com/orgs/home-assistant/packages?repo_name=core). This Greengrass component downloads the selected Docker image from Docker Hub or GitHub with the help of the [Docker application manager](https://docs.aws.amazon.com/greengrass/v2/developerguide/docker-application-manager-component.html) component.

Home Assistant configuration files are [designed to be split](https://www.home-assistant.io/docs/configuration/splitting_configuration/) as the solution scales. By convention, [secrets are typically separated from the rest of the configuration](https://www.home-assistant.io/docs/configuration/secrets/) and stored in a file named **secrets.yaml**. This Greengrass component handles **secrets.yaml** by storing it as a secret in [AWS Secrets Manager](https://aws.amazon.com/secrets-manager/) in the cloud. At the edge, this component retrieves the **secrets.yaml** file from Secrets Manager with the help of the [Secret manager](https://docs.aws.amazon.com/greengrass/v2/developerguide/secret-manager-component.html) managed component. From the developer machine, the contents of the **secrets** directory are placed into the Secrets Manager secret by calling **create_config_secret.py**.

As shown in **blue** on the architecture diagram, Home Assistant can use its [MQTT integration](https://www.home-assistant.io/integrations/mqtt/) to connect directly to AWS IoT Core. Alternatively, and more powerfully, Home Assistant can instead connect to the local Greengrass [EMQX MQTT broker](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-broker-emqx-component.html) or [Moquette MQTT broker](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-broker-moquette-component.html). This is option is shown in **red**. If Home Assistant and other devices on the local network are registered as [Local Client Devices with Greengrass](https://aws.amazon.com/blogs/iot/implementing-local-client-devices-with-aws-iot-greengrass/), this architecture allows Home Assistant to communicate with those [other devices via the broker](https://docs.aws.amazon.com/greengrass/v2/developerguide/interact-with-local-iot-devices.html) **and** with AWS IoT Core and other Greengrass components via the [MQTT bridge](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-bridge-component.html) and [Greengrass Interprocess Communication](https://docs.aws.amazon.com/greengrass/v2/developerguide/ipc-publish-subscribe.html). 

# Repository Contents

| Item                          | Description                                                                                           |
| ----------------------------- | ----------------------------------------------------------------------------------------------------- |
| /artifacts                    | Greengrass V2 component artifacts that run on the Greengrass edge runtime.                            |
| /cicd                         | CDK Typescript app for a CodePipeline CI/CD pipeline.                                                 |
| /images                       | Images for README files.                                                                              |
| /libs                         | Python libraries shared by Python scripts.                                                            |
| /secrets                      | Home Assistant secrets (secrets.yaml and other optional files).                                      |
| /tests                        | Pytest unit tests.                                                                                    |
| create_config_secret.py       | Creates or updates the Home Assistant configuration secret in Secrets Manager.                        |
| deploy_component_version.py   | Deploys a component version to the Greengrass core device target.                                     |
| gdk_build.py                  | Custom build script for the Greengrass Development Kit (GDK) - Command Line Interface.                |
| gdk-config.json               | Configuration for the Greengrass Development Kit (GDK) - Command Line Interface.                      |
| quickstart.sh                 | Creates a secret, and creates and deploys a component version in a single operation.                  |
| recipe.yaml                   | Greengrass V2 component recipe template.                                                              |

# Requirements and Prerequisites

## Greengrass Core Device

### Platform

This component requires that the Greengrass device be running a Linux operating system. It [supports all architectures supported by Greengrass itself](https://docs.aws.amazon.com/greengrass/v2/developerguide/setting-up.html#greengrass-v2-supported-platforms).

### Edge Runtime

The [Greengrass edge runtime needs to be deployed](https://docs.aws.amazon.com/greengrass/v2/developerguide/getting-started.html) to a suitable machine, virtual machine or EC2 instance. Please see the [Home Assistant installation guide](https://www.home-assistant.io/installation/) for information on the resources required.

### Docker Requirements

Your core device must [meet the requirements to run Docker containers using Docker Compose and Docker Hub](https://docs.aws.amazon.com/greengrass/v2/developerguide/run-docker-container.html).

### Python Requirements

This component requires both **python3** and **pip3** to be installed on the core device.

## Greengrass Cloud Services

### Core Device Role

Assuming the bucket name in **gdk-config.json** is left unchanged, this component downloads artifacts from an S3 bucket named **greengrass-home-assistant-REGION-ACCOUNT**. Therefore your Greengrass core device role must allow the **s3:GetObject** permission for this bucket. For more information: https://docs.aws.amazon.com/greengrass/v2/developerguide/device-service-role.html#device-service-role-access-s3-bucket

Additionally, this component downloads sensitive Home Assistant configuration from Secrets Manager. Therefore your Greengrass core device role must also allow the **secretsmanager:GetSecretValue** permission for the **greengrass=home-assistant-ID** secret. 

Policy template to add to your device role (substituting correct values for ACCOUNT, REGION and ID):

```
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Action": [
        "s3:GetObject"
      ],
      "Resource": "arn:aws:s3:::greengrass-home-assistant-REGION-ACCOUNT/*"
    },
    {
      "Effect": "Allow",
      "Action": [
        "secretsmanager:GetSecretValue"
      ],
      "Resource": "arn:aws:secretsmanager:REGION:ACCOUNT:secret:greengrass-home-assistant-ID"
    }
  ]
}
```

## Developer Machine

### AWS CLI

The AWS CLI should be installed.

### Python

Most of the scripts in this repository are Python scripts. They are Python 3 scripts and hence **python3** and **pip3** are required.

Package dependencies can be resolved as follows:

```
pip3 install -r requirements.txt
```

Please consider to use a [virtual environment](https://docs.python.org/3/library/venv.html).

[Boto3](https://boto3.amazonaws.com/v1/documentation/api/latest/index.html) is included in the package dependencies and therefore your machine requires appropriate [credentials](https://boto3.amazonaws.com/v1/documentation/api/latest/guide/credentials.html).

### GDK CLI

This component makes use of the [Greengrass Development Kit (GDK) - Command Line Interface (CLI)](https://github.com/aws-greengrass/aws-greengrass-gdk-cli). This can be installed as follows:

```
pip3 install git+https://github.com/aws-greengrass/aws-greengrass-gdk-cli.git
```

### Bash

The **quickstart.sh** script is a Bash script. If using a Windows machine, you will need a Bash environment. Alternatively you can run the Python scripts individually.

### jq

The **jq** utility is used by **quickstart.sh**. Release packages for Linux, OS X and Windows are available on the [jq](https://stedolan.github.io/jq/) site.

Alternatively, Ubuntu includes a **jq** package:

```
sudo apt update
sudo apt install jq
```

# Getting Started

You can choose between two ways to get started: Quickstart or Slowstart.

All scripts are compatible with Linux, Mac or Windows operating systems, provided a Bash environment is available.

## Quickstart

The **quickstart.sh** bash script is supplied to help you get going fast. It rolls the constituent steps up into a single command.

Before running the script, users must deploy Greengrass V2 to a physical machine, virtual machine or EC2 instance, meeting all of the prerequisites including [the requirements to run Docker containers using Docker Compose and Docker Hub](https://docs.aws.amazon.com/greengrass/v2/developerguide/run-docker-container.html). Addtionally, users must set the AWS region in **gdk-config.json**.

It is not necessary to perform any Home Assistant configuration changes. Out of the box, Home Assistant will be deployed with default configuration.

The Quickstart script will:

1. Install required Python packages on your developer machine.
2. Upload the default (null) secret configuration (**secrets.yaml**) to a secret in Secrets Manager, creating the secret.
3. Use GDK to build the component.
4. Use GDK to publish a new component version to Greengrass cloud services and upload artifacts to an S3 bucket.
5. Prompt you to add permissions for the configuration secret and artifacts bucket to the Greengrass core device role. 
6. Deploy the new component version to the Greengrass core.

The script accepts 1 argument: the Greengrass Core device name.

Example execution:

```
bash quickstart.sh MyCoreDeviceThingName
```
## Slowstart

For any serious use of the component, Quickstart shall not be appropriate.

### Manual Deployment
If not using Quickstart, you must perform the following steps:

1. Deploy the Greengrass runtime to your machine, virtual machine or EC2 instance, meeting all of the prerequisites.
2. Select your desired Home Assistant Container image and tag by modifying **artifacts/docker-compose.yml**.
3. Configure Home Assistant by modifying the configuration YAML files in **artifacts/config** and **secrets** as desired. 
4. Set the AWS region and component version in **gdk-config.json**.
5. Run **create_config_secret.py** to create the configuration secret in Secrets Manager.
6. Run **gdk component build** to build the component.
7. Run **gdk component publish** to create a component version in Greengrass cloud service, and upload artifacts to S3.
8. Add permissions for the configuration secret and artifacts bucket to the Greengrass core device role. 
9. The component can then be deployed using [the console or using the AWS CLI](https://docs.aws.amazon.com/greengrass/v2/developerguide/create-deployments.html) in the normal way. Alternatively it can be deployed using the supplied **deploy_component_version.py** script. 

For iterative configuration changes, repeat steps as appropriate.

### Example Execution

Example of steps 5, 6, 7 and 9:

```
python3 create_config_secret.py
gdk component build
gdk component publish
python3 deploy_component_version.py 1.1.0 MyCoreDeviceThingName
```

This example:

1. Creates a Secrets Manager secret in your account in the region specified in **gdk-config.json**.
2. Builds the component and publishes it to your account in the region specified in **gdk-config.json**.
2. Deploys the new component version to Greengrass core device **MyCoreDeviceThingName**.

### CI/CD Pipeline

This repository offers a CodePipeline [CI/CD pipeline](cicd/README.md) as a CDK application. This can be optionally deployed to the same account as the Greengrass core.

This CI/CD pipeline automates steps 6, 7 and 9. With the pipeline deployed, users can make iterative configuration changes, update the configuration secret using **create_config_secret.py**, and then trigger the CI/CD pipeline to handle the rest.

# Home Assistant Configuration Tips

Configuration of Home Assistant can be done predominantly through its user interface. However, it can also be configured using the YAML files in **artifacts/config** and **secrets**. Please consult the [Home Assistant configuration documentation](https://www.home-assistant.io/docs/configuration/) for details.

## Defaults

The configuration files in this projects are merely skeleton files. Home Assistant can be deployed with these files, yielding a greenfields installation. 

## Machine Specific Images

Docker images from Home Assistant's GitHub releases can be used directly as the image in **artifacts/docker-compose.yml**.

## MQTT

You can use the Home Assistant [MQTT Integration](https://www.home-assistant.io/integrations/mqtt/) to integrate your devices and Home Assistant with AWS IoT services, by configuring your MQTT broker as being AWS IoT Core or one of the AWS IoT Greengrass brokers.

Install the MQTT integration and use the Home Assistant UI to configure the integration. You will need to enable **Advanced mode** in your Home Assistant user settings to be able to setup a TLS connection to your preferred broker.

### AWS IoT Core

To connect Home Assistant directly to AWS IoT Core, firstly create a Thing representing Home Assistant, and obtain the device certificate, private key and Amazon Root CA certificate.

Obtain the AWS IoT Core endpoint:

```bash
aws iot describe-endpoint --endpoint-type iot:Data-ATS
{
    "endpointAddress": "ENDPOINTID-ats.iot.REGION.amazonaws.com"
}
```

Then configure the MQTT integration through the UI with the following settings.

| Configuration Item            | Description                             |
| ----------------------------- | --------------------------------------- |
| Broker                        | ENDPOINTID-ats.iot.REGION.amazonaws.com |
| Port                          | 8883                                    |
| Client ID                     | The AWS IoT Core thing name             |
| Client certificate            | FINGERPRINT-certificate.pem.crt         |
| Private key                   | FINGERPRINT-private.pem.key             |
| Broker certificate validation | Custom                                  |
| CA certificate                | AmazonRootCA1.pem                       |
| MQTT protocol                 | 3.1.1 or 5                              |
| MQTT transport                | TCP                                     |

### Greengrass MQTT Broker

Greengrass V2 includes two AWS-managed brokers, the [EMQX MQTT broker component](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-broker-emqx-component.html) and the [Moquette MQTT broker component](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-broker-moquette-component.html). Either of these can be deployed to Greengrass to [allow Greengrass components and devices on your local network to communicate with each other](https://docs.aws.amazon.com/greengrass/v2/developerguide/interact-with-local-iot-devices.html), without relying on an internet connection to AWS IoT Core. 

Using the [MQTT Integration](https://www.home-assistant.io/integrations/mqtt/), Home Assistant can be a "local IoT device" that connects to the EMQX or Moquette broker. Additionally, Greengrass V2 includes an [AWS-managed MQTT Bridge component](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-bridge-component.html). When this is also deployed, Home Assistant can use its MQTT Integration to communicate with local devices, Greengrass components and AWS IoT Core; the best of all worlds.

To begin, [update the Greengrass deployment to add the necessary components](https://docs.aws.amazon.com/greengrass/v2/developerguide/client-devices-tutorial.html) to your Greengrass core device:

* [MQTT broker (EMQX)](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-broker-emqx-component.html) or [MQTT broker (Moquette)](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-broker-moquette-component.html)
* [MQTT bridge](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-bridge-component.html)
* [Client device auth](https://docs.aws.amazon.com/greengrass/v2/developerguide/client-device-auth-component.html)
* [IP detector](https://docs.aws.amazon.com/greengrass/v2/developerguide/ip-detector-component.html)

You will then need to:

1. Create a Thing representing Home Assistant, and obtain the device certificate and private key.
2. [Associate](https://docs.aws.amazon.com/greengrass/v2/developerguide/associate-client-devices.html) this Thing with your Greengrass core device.
3. [Configure the Client device auth component](https://docs.aws.amazon.com/greengrass/v2/developerguide/client-device-auth-component.html#client-device-auth-component-configuration) to define what Home Assistant is authorized to do.
4. [Configure the MQTT Bridge component](https://docs.aws.amazon.com/greengrass/v2/developerguide/mqtt-bridge-component.html#mqtt-bridge-component-configuration) to define the desired message relaying.

You can then configure the MQTT integration broker settings as described above for AWS IoT Core, but with the following adjustments:

1. The broker should be `localhost` because the broker is on the same machine as Home Assistant.
2. Use [your own certificate authority (CA)](https://docs.aws.amazon.com/greengrass/v2/developerguide/connecting-to-mqtt.html#use-your-own-CA), configure the [Client device auth](https://docs.aws.amazon.com/greengrass/v2/developerguide/client-device-auth-component.html) component to use it, and configure the MQTT integration to use that as the CA certificate to validate the broker. Alternatively, disable broker certificate validation in the MQTT integration.

# Operations

## Clean Uninstall

Removing this component from your deployment will not remove all vestiges from your Greengrass core device. Additional steps:

- Remove any Home Assistant Docker images that have persisted.
- Remove the working directory: **/greengrass/v2/work/aws.greengrass.labs.HomeAssistant**. This also deletes persistent data and settings.

## Data Backup

If this component is deployed with default settings, persistent data and settings are located in **/greengrass/v2/work/aws.greengrass.labs.HomeAssistant/config**.

# Troubleshooting

Tips for investigating failed deployments, or deployments that succeed but Home Assistant is still not working as expected.

## Troubleshooting Tools

### Core Device Log Files

Detailed component logs can be found on the Core Device in **/greengrass/v2/logs/aws.greengrass.labs.HomeAssistant.log**.

The Greengrass Core log file can be found at **/greengrass/v2/logs/greengrass.log**.

For more information please refer to the Greengrass V2 documentation: https://docs.aws.amazon.com/greengrass/v2/developerguide/monitor-logs.html

### Greengrass CLI

Consider to install the [Greengrass Command Line Interface component](https://docs.aws.amazon.com/greengrass/v2/developerguide/gg-cli.html) to obtain greater visibility into the state of your core device.

### Docker Container Logs

The logs within the Docker container can be inspected as follows:

```
docker logs homeassistant
```

## Common Failures

### Wrong Docker Image Architecture

If a Docker image of the wrong architecture is deployed, it will fail to start. A message similar to the following indicates that the wrong architecture is being used:

```
standard_init_linux.go:228: exec user process caused: exec format error
```

This message will appear in **/greengrass/v2/logs/aws.greengrass.labs.HomeAssistant.log**. 

To resolve incorrect architecture, please check the available architectures for the image tag. Image tags on DockerHub do not always support all architectures. Update **docker-compose.yml** and deploy a new version of the component.

### Secret Configuration Changes Not Deployed

The Greengrass Secret Manager component needs to fetch the configuration secret from the cloud, for any changes to **secrets.yaml** or the certificates to be seen by the Home Assistant component. The Secret Manager will not necessarily fetch the secret even when a new version of the component is deployed. Restart or reboot the core device to force a fetch.

The deployed **secrets.yaml** can be found at **/greengrass/v2/work/aws.greengrass.labs.HomeAssistant/secrets.yaml**.

# Development

## Static Analysis

Static analysis is performed using [Pylint](https://pylint.org/). Example execution:

```
pylint artifacts libs tests *.py
```

## Unit Tests

Unit tests are performed using [pytest](https://pytest.org/).

Example execution:

```
pytest --cov=artifacts --cov=.
```

Producing an HTML coverage report into the **htmlcov** directory:

```
pytest --cov=artifacts --cov=. --cov-report=html
```

Producing a coverage report for just the on-device artifacts (100% coverage):

```
pytest --cov=artifacts
```
