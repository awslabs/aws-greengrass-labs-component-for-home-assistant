# CI/CD Pipeline Stack

The CI/CD pipeline for the AWS Greengrass Home Assistant component is a TypeScript CDK application that deploys a CodePipeline pipeline. 

# Table of Contents
* [Architecture](#architecture)
* [How to](#how-to)
    * [Prerequisites](#prerequisites)
    * [Build the application](#build-the-application)
    * [Run unit tests](#run-unit-tests)
    * [Context variables](#context-variables)
    * [Synthesize a CloudFormation template](#synthesize-a-cloudformation-template)
    * [Deploy the pipeline](#deploy-the-pipeline)

# Architecture

The pipeline consists of two stages: build and test. The build stage creates a new component version and the deploy stage deploys that version to the Greengrass Edge runtime. 

![ggv2-ha-cicd-pipeline-architecture](images/ggv2-ha-cicd-pipeline-architecture.png)

Source code is obtained from CodeCommit in the same region as what the pipeline is deployed. Therefore it's necessary to clone the code to a CodeCommit repository. Alternatively you can modify the pipeline to obtain the source code from a different repository.

The pipeline automatically increments the component version number by assigning the build stage CodeBuild build number as the patch revision of the **major.minor.patch** version. Major and minor revision updates are achieved by changing **buildspec.yml**.

The pipeline publishes success or failure notifications to an SNS topic.

# How to

## Prerequisites

Follow the [Getting started with the AWS SDK guide (for Typescript)](https://docs.aws.amazon.com/cdk/latest/guide/getting_started.html) to install CDK and bootstrap your environment.

## Build the application

Compile TypeScript to JS.

```
npm run build
```
## Run unit tests

Uses the Jest framework.

```
npm run test
```

## Context variables

Synthesis and deployment of the stack requires the following context variables:

| Name                  | Description                                                                             |
| --------------------- | --------------------------------------------------------------------------------------- |
| RepositoryName        | The name of the CodeCommit repository containing the component's source code.           |
| BranchName            | The name of the branch to use within the CodeCommit repository.                         |
| GreengrassCoreName    | The name of the Greengrass Core device that the component shall be deployed to.         |

## Synthesize a CloudFormation template 

Example synthesis:

```
cdk synth -c RepositoryName=aws-greengrass-labs-component-for-home-assistant -c BranchName=main -c GreengrassCoreName=GGHomeAssistant
```
## Deploy the pipeline

Example deployment:

```
cdk deploy -c RepositoryName=aws-greengrass-labs-component-for-home-assistant -c BranchName=main -c GreengrassCoreName=GGHomeAssistant
```
