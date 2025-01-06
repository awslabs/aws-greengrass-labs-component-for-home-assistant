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
import * as kms from 'aws-cdk-lib/aws-kms';
import * as gdkConfig from '../../gdk-config.json';
import { NagSuppressions } from 'cdk-nag'

enum Names {
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
        
        const buildProject = new codebuild.PipelineProject(this, `${this.stackName}Build`, {
            projectName: `${this.stackName}Build`,
            buildSpec: codebuild.BuildSpec.fromSourceFilename('cicd/buildspec.yaml'),
            environment: {
                buildImage: codebuild.LinuxBuildImage.STANDARD_7_0
            },
            timeout: cdk.Duration.minutes(5),
            encryptionKey: kms.Alias.fromAliasName(this, `${this.stackName}BuildS3Key`, 'alias/aws/s3')
        });

        const deployProject = new codebuild.PipelineProject(this, `${this.stackName}Deploy`, {
            projectName: `${this.stackName}Deploy`,
            buildSpec: codebuild.BuildSpec.fromSourceFilename('cicd/deployspec.yaml'),
            environment: {
                buildImage: codebuild.LinuxBuildImage.STANDARD_7_0
            },
            timeout: cdk.Duration.minutes(15),
            encryptionKey: kms.Alias.fromAliasName(this, `${this.stackName}DeployS3Key`, 'alias/aws/s3')
        });

        const pipelineBucket = new s3.Bucket(this, `${this.stackName}Bucket`, {
            bucketName: `${this.stackName.toLowerCase()}-${this.account}-${this.region}`,
            blockPublicAccess: s3.BlockPublicAccess.BLOCK_ALL,
            versioned: false,
            serverAccessLogsPrefix: 'access-logs',
            encryption: s3.BucketEncryption.S3_MANAGED,
            enforceSSL: true
        });

        const topic = new sns.Topic(this, `${this.stackName}Notification`, {
            topicName: `${this.stackName}Notification`,
            displayName: `${this.stackName} CI/CD Notification`
        });

        // Create a policy that enforces SSL but allows AWS services
        // (such as CodePipeline) to publish to the topic via EventBridge
        const topicPolicy = new sns.TopicPolicy(this, `${this.stackName}NotificationPolicy`, {
            topics: [topic]
        });
        topicPolicy.document.addStatements(
            // Allow AWS services to publish
            new iam.PolicyStatement({
                effect: iam.Effect.ALLOW,
                principals: [new iam.ServicePrincipal('events.amazonaws.com')],
                actions: ['sns:Publish'],
                resources: [topic.topicArn]
            }),
            // Deny non-SSL access for all other publishers
            new iam.PolicyStatement({
                effect: iam.Effect.DENY,
                principals: [new iam.AnyPrincipal()],
                actions: ['sns:Publish'],
                resources: [topic.topicArn],
                conditions: {
                    'Bool': {
                        'aws:SecureTransport': false
                    }
                }
            })
        );

        // We create the unit tests report group explicitly, rather than let CodeBuild do it, so that we can define the raw results export
        new codebuild.CfnReportGroup(this, `${this.stackName}UnitTestReportGroup`, {
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
        const buildProjectPolicy = new iam.Policy(this, `${this.stackName}BuildProjectPolicy`, {
            statements: [
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['greengrass:CreateComponentVersion','greengrass:ListComponentVersions'],
                    resources: [`arn:aws:greengrass:${this.region}:${this.account}:components:${componentName}`]
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['s3:CreateBucket','s3:GetBucketLocation'],
                    resources: [`arn:aws:s3:::${bucketName}-${this.region}-${this.account}`]
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['s3:PutObject','s3:GetObject'],
                    resources: [`arn:aws:s3:::${bucketName}-${this.region}-${this.account}/*`]
                })
            ]
        })
        buildProject.role?.attachInlinePolicy(buildProjectPolicy);
    
        // The deploy project needs some extra rights
        const deployProjectPolicy = new iam.Policy(this, `${this.stackName}DeployProjectPolicy`, {
            statements: [
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['greengrass:GetCoreDevice'],
                    resources: [`arn:aws:greengrass:${this.region}:${this.account}:coreDevices:${context.greengrassCoreName}`]
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['greengrass:ListComponentVersions'],
                    resources: [`arn:aws:greengrass:${this.region}:${this.account}:components:*`]
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['greengrass:CreateDeployment'],
                    resources: ['*']
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['greengrass:GetDeployment', 'greengrass:ListDeployments'],
                    resources: [`arn:aws:greengrass:${this.region}:${this.account}:deployments:*`]
                }),
                new iam.PolicyStatement({
                    effect: iam.Effect.ALLOW,
                    actions: ['iot:*'],
                    resources: ['*']
                })
            ]
        })
        deployProject.role?.attachInlinePolicy(deployProjectPolicy);

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
            actionName: `Source`,
            output: source,
            connectionArn: `arn:aws:codestar-connections:${this.region}:${this.account}:connection/${context.connectionId}`,
            owner: context.ownerName,
            repo: context.repositoryName,
            branch: context.branchName
        });

        const buildAction = new codepipeline_actions.CodeBuildAction({
            actionName: `Build`,
            project: buildProject,
            input: source,
            outputs: [build]
        });

        const deployAction = new codepipeline_actions.CodeBuildAction({
            actionName: `Deploy`,
            project: deployProject,
            input: source,
            extraInputs: [build],
            outputs: [deploy],
            environmentVariables: {
                "GREENGRASS_CORE_NAME": { value: context.greengrassCoreName }
            }
        });

        const pipeline = new codepipeline.Pipeline(this, `${this.stackName}`, {
            pipelineName: `${this.stackName}`,
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
        const notificationRule = pipeline.onStateChange(`${this.stackName}StateChange`);
        notificationRule.addEventPattern({ detail: { state: ['SUCCEEDED','FAILED'] } });
        const state = events.EventField.fromPath('$.detail.state')
        const executionId = events.EventField.fromPath('$.detail.execution-id')
        const account = events.EventField.fromPath('$.account')
        notificationRule.addTarget(new events_targets.SnsTopic(topic, {
            message: events.RuleTargetInput.fromText(`Account ${account} ${state} for execution ID ${executionId}`)
        }));

        NagSuppressions.addResourceSuppressions([pipeline, buildProject, deployProject], [
            {
              id: 'AwsSolutions-IAM5',
              reason: 'The default policies created in the code build and pipeline roles include wildcards.'
            }
        ], true )

        NagSuppressions.addResourceSuppressions([buildProjectPolicy, deployProjectPolicy], [
            {
              id: 'AwsSolutions-IAM5',
              reason: 'The wildcards used in these policies are least privilege for the resources or access needed'
            }
        ], true )
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