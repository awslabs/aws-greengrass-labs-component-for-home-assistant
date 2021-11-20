// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from '@aws-cdk/core';
import { CfnParameter, Duration } from '@aws-cdk/core';
import codebuild = require('@aws-cdk/aws-codebuild');
import codecommit = require('@aws-cdk/aws-codecommit');
import codepipeline = require('@aws-cdk/aws-codepipeline');
import codepipeline_actions = require('@aws-cdk/aws-codepipeline-actions');
import s3 = require('@aws-cdk/aws-s3');
import sns = require('@aws-cdk/aws-sns');
import events_targets = require('@aws-cdk/aws-events-targets');
import events = require('@aws-cdk/aws-events');
import { Effect, PolicyStatement } from '@aws-cdk/aws-iam';

enum Names {
    PREFIX_DASH = 'gg-ha-cicd',
    PREFIX_CAMEL = 'GgHaCicd',
    COMPONENT = 'aws.greengrass.labs.HomeAssistant',
    COMPONENT_BUCKET = 'greengrass-home-assistant',
    SECRET = 'greengrass-home-assistant'
}

type CicdStackContext = {
    repositoryName: string,
    branchName: string,
    greengrassCoreName: string
}

export class CicdStack extends cdk.Stack {
    constructor(scope: cdk.Construct, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        const context = this.getContext();

        const buildProject = new codebuild.PipelineProject(this, `${Names.PREFIX_CAMEL}Build`, {
            projectName: `${Names.PREFIX_DASH}-build`,
            buildSpec: codebuild.BuildSpec.fromSourceFilename('cicd/buildspec.yaml'),
            environment: {
                buildImage: codebuild.LinuxBuildImage.STANDARD_5_0
            },
            timeout: Duration.minutes(5),
        });

        const deployProject = new codebuild.PipelineProject(this, `${Names.PREFIX_CAMEL}Deploy`, {
            projectName: `${Names.PREFIX_DASH}-deploy`,
            buildSpec: codebuild.BuildSpec.fromSourceFilename('cicd/deployspec.yaml'),
            environment: {
                buildImage: codebuild.LinuxBuildImage.STANDARD_5_0
            },
            timeout: Duration.minutes(5),
        });

        const pipelineBucket = new s3.Bucket(this, `${Names.PREFIX_CAMEL}Bucket`, {
            bucketName: `${Names.PREFIX_DASH}-${this.account}-${this.region}`,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
            versioned: false,
        });

        const topic = new sns.Topic(this, `${Names.PREFIX_CAMEL}Notification`, {
            topicName: `${Names.PREFIX_DASH}-notification`,
            displayName: 'GG Home Assistant CI/CD Notification'
        });

        // We create the unit tests report group explicitly, rather than let CodeBuild do it, so that we can define the raw results export
        new codebuild.CfnReportGroup(this, `${Names.PREFIX_CAMEL}UnitTestReportGroup`, {
            type: 'TEST',
            name: `${buildProject.projectName}-UnitTestsReport`,
            exportConfig: {
                exportConfigType: 'S3',
                s3Destination: {
                    bucket: pipelineBucket.bucketName,
                    encryptionDisabled: true,
                    packaging: 'NONE'
                }
            }
        });

        // The build project needs some extra rights
        buildProject.addToRolePolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ['greengrass:GetComponent','greengrass:CreateComponentVersion'],
            resources: [`arn:aws:greengrass:${this.region}:${this.account}:components:${Names.COMPONENT}`]
        }));
        buildProject.addToRolePolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ['s3:ListAllMyBuckets'],
            resources: ['*']
        }));
        buildProject.addToRolePolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ['s3:CreateBucket'],
            resources: [`arn:aws:s3:::${Names.COMPONENT_BUCKET}-${this.account}-${this.region}`]
        }));
        buildProject.addToRolePolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ['s3:PutObject','s3:GetObject'],
            resources: [`arn:aws:s3:::${Names.COMPONENT_BUCKET}-${this.account}-${this.region}/*`]
        }));

        // The deploy project needs some extra rights
        deployProject.addToRolePolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ['greengrass:GetCoreDevice'],
            resources: [`arn:aws:greengrass:${this.region}:${this.account}:coreDevices:${context.greengrassCoreName}`]
        }));
        deployProject.addToRolePolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ['greengrass:ListComponentVersions'],
            resources: [`arn:aws:greengrass:${this.region}:${this.account}:components:*`]
        }));
        deployProject.addToRolePolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ['greengrass:CreateDeployment'],
            resources: ['*']
        }));
        deployProject.addToRolePolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ['greengrass:GetDeployment', 'greengrass:ListDeployments'],
            resources: [`arn:aws:greengrass:${this.region}:${this.account}:deployments:*`]
        }));
        deployProject.addToRolePolicy(new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ['iot:*'],
            resources: ['*']
        }));

        // All projects need to be able to get the secret value
        const secretPolicy = new PolicyStatement({
            effect: Effect.ALLOW,
            actions: ['secretsmanager:GetSecretValue'],
            resources: [`arn:aws:secretsmanager:${this.region}:${this.account}:secret:${Names.SECRET}-*`]
        });
        buildProject.addToRolePolicy(secretPolicy);
        deployProject.addToRolePolicy(secretPolicy);

        const source = new codepipeline.Artifact('Source');
        const build = new codepipeline.Artifact('Build');
        const deploy = new codepipeline.Artifact('Deploy');

        const codeCommitRepository = codecommit.Repository.fromRepositoryName(this, `${Names.PREFIX_CAMEL}CCRepo`, context.repositoryName);

        const sourceAction = new codepipeline_actions.CodeCommitSourceAction({
            actionName: `${Names.PREFIX_DASH}-source`,
            output: source,
            repository: codeCommitRepository,
            branch: context.branchName
        });

        const buildAction = new codepipeline_actions.CodeBuildAction({
            actionName: `${Names.PREFIX_DASH}-build`,
            project: buildProject,
            input: source,
            outputs: [build]
        });

        const deployAction = new codepipeline_actions.CodeBuildAction({
            actionName: `${Names.PREFIX_DASH}-deploy`,
            project: deployProject,
            input: source,
            extraInputs: [build],
            outputs: [deploy],
            environmentVariables: {
                "GREENGRASS_CORE_NAME": { value: context.greengrassCoreName }
            }
        });

        const pipeline = new codepipeline.Pipeline(this, `${Names.PREFIX_CAMEL}Pipeline`, {
            pipelineName: `${Names.PREFIX_DASH}-pipeline`,
            artifactBucket: pipelineBucket,
            stages: [
                {
                    stageName: 'Source',
                    actions: [sourceAction],
                },
                {
                    stageName: 'Build',
                    actions: [buildAction],
                },
                {
                    stageName: 'Deploy',
                    actions: [deployAction],
                }
            ],
        });

        // Send only SUCCEEDED and FAILED states to the SNS topic, to give a pipeline execution result
        const notificationRule = pipeline.onStateChange(`${Names.PREFIX_CAMEL}StateChange`);
        notificationRule.addEventPattern({ detail: { state: ['SUCCEEDED','FAILED'] } });
        const state = events.EventField.fromPath('$.detail.state')
        const executionId = events.EventField.fromPath('$.detail.execution-id')
        const account = events.EventField.fromPath('$.account')
        notificationRule.addTarget(new events_targets.SnsTopic(topic, {
            message: events.RuleTargetInput.fromText(`Account ${account} ${state} for execution ID ${executionId}`)
        }));
    }

    private getContextVariable(name:string, desc:string): string {
        const contextVariable = this.node.tryGetContext(name);

        if (contextVariable === undefined) {
            throw new Error(`Variable undefined: ${name}\n${desc}`);
        }

        return contextVariable;
    }

    private getContext(): CicdStackContext {
        const repositoryName        = this.getContextVariable('RepositoryName',         'Name of the Code Commit repository containing the source code');
        const branchName            = this.getContextVariable('BranchName',             'Name of the branch to use in the Code Commit repository');
        const greengrassCoreName    = this.getContextVariable('GreengrassCoreName',     'Name of the Greengrass core device to which the Home Assistant component should be deployed');

        return {
            repositoryName,
            branchName,
            greengrassCoreName
        }
    }
}