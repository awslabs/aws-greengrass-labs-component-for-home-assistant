// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from 'aws-cdk-lib';
import * as codebuild from 'aws-cdk-lib/aws-codebuild';
import * as codepipeline from 'aws-cdk-lib/aws-codepipeline';
import * as codepipeline_actions from 'aws-cdk-lib/aws-codepipeline-actions';
import * as s3 from 'aws-cdk-lib/aws-s3';
import * as sns from 'aws-cdk-lib/aws-sns';
import * as events_targets from 'aws-cdk-lib/aws-events-targets';
import * as events from 'aws-cdk-lib/aws-events';
import * as iam from 'aws-cdk-lib/aws-iam';
import * as gdkConfig from '../../gdk-config.json';

enum Names {
    PREFIX_DASH = 'gg-ha-cicd',
    PREFIX_CAMEL = 'GgHaCicd',
    SECRET = 'greengrass-home-assistant'
}

type CicdStackContext = {
    connectionId: string,
    ownerName: string,
    repositoryName: string,
    branchName: string,
    greengrassCoreName: string
}

export class CicdStack extends cdk.Stack {
    constructor(scope: cdk.App, id: string, props?: cdk.StackProps) {
        super(scope, id, props);

        const context = this.getContext();

        // Extract configuration from GDK configuration to prevent mismatches
        const componentName = Object.keys(gdkConfig['component'])[0];
        const bucketName = gdkConfig['component'][componentName as keyof typeof gdkConfig['component']]['publish']['bucket'];
        
        const buildProject = new codebuild.PipelineProject(this, `${Names.PREFIX_CAMEL}Build`, {
            projectName: `${Names.PREFIX_DASH}-build`,
            buildSpec: codebuild.BuildSpec.fromSourceFilename('cicd/buildspec.yaml'),
            environment: {
                buildImage: codebuild.LinuxBuildImage.STANDARD_7_0
            },
            timeout: cdk.Duration.minutes(5),
        });

        const deployProject = new codebuild.PipelineProject(this, `${Names.PREFIX_CAMEL}Deploy`, {
            projectName: `${Names.PREFIX_DASH}-deploy`,
            buildSpec: codebuild.BuildSpec.fromSourceFilename('cicd/deployspec.yaml'),
            environment: {
                buildImage: codebuild.LinuxBuildImage.STANDARD_7_0
            },
            timeout: cdk.Duration.minutes(15),
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
        buildProject.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['greengrass:CreateComponentVersion','greengrass:ListComponentVersions'],
            resources: [`arn:aws:greengrass:${this.region}:${this.account}:components:${componentName}`]
        }));
        buildProject.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['s3:CreateBucket','s3:GetBucketLocation'],
            resources: [`arn:aws:s3:::${bucketName}-${this.region}-${this.account}`]
        }));
        buildProject.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['s3:PutObject','s3:GetObject'],
            resources: [`arn:aws:s3:::${bucketName}-${this.region}-${this.account}/*`]
        }));

        // The deploy project needs some extra rights
        deployProject.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['greengrass:GetCoreDevice'],
            resources: [`arn:aws:greengrass:${this.region}:${this.account}:coreDevices:${context.greengrassCoreName}`]
        }));
        deployProject.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['greengrass:ListComponentVersions'],
            resources: [`arn:aws:greengrass:${this.region}:${this.account}:components:*`]
        }));
        deployProject.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['greengrass:CreateDeployment'],
            resources: ['*']
        }));
        deployProject.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['greengrass:GetDeployment', 'greengrass:ListDeployments'],
            resources: [`arn:aws:greengrass:${this.region}:${this.account}:deployments:*`]
        }));
        deployProject.addToRolePolicy(new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['iot:*'],
            resources: ['*']
        }));

        // All projects need to be able to get the secret value
        const secretPolicy = new iam.PolicyStatement({
            effect: iam.Effect.ALLOW,
            actions: ['secretsmanager:GetSecretValue'],
            resources: [`arn:aws:secretsmanager:${this.region}:${this.account}:secret:${Names.SECRET}-*`]
        });
        buildProject.addToRolePolicy(secretPolicy);
        deployProject.addToRolePolicy(secretPolicy);

        const source = new codepipeline.Artifact('Source');
        const build = new codepipeline.Artifact('Build');
        const deploy = new codepipeline.Artifact('Deploy');

        const sourceAction = new codepipeline_actions.CodeStarConnectionsSourceAction({
            actionName: `${Names.PREFIX_DASH}-source`,
            output: source,
            connectionArn: `arn:aws:codestar-connections:${this.region}:${this.account}:connection/${context.connectionId}`,
            owner: context.ownerName,
            repo: context.repositoryName,
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
            pipelineType: codepipeline.PipelineType.V2,
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
        const connectionId          = this.getContextVariable('ConnectionId',       'CodeStar connection ID of the repo, hosted in GitHub, BitBucket and GitHub Enterprise Server');
        const ownerName             = this.getContextVariable('OwnerName',          'Name of the owner of the repo, hosted in GitHub, BitBucket and GitHub Enterprise Server');    
        const repositoryName        = this.getContextVariable('RepositoryName',     'Name of the repository containing the source code (Default: aws-greengrass-labs-component-for-home-assistant)');
        const branchName            = this.getContextVariable('BranchName',         'Name of the branch to use in the repository (Default: main)');
        const greengrassCoreName    = this.getContextVariable('GreengrassCoreName', 'Name of the Greengrass core device to which the Home Assistant component should be deployed');

        return {
            connectionId,
            ownerName,
            repositoryName,
            branchName,
            greengrassCoreName
        }
    }
}