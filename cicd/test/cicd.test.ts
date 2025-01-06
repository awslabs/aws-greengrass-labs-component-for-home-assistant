// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import * as Cicd from '../lib/cicd-stack';

const STACK_NAME = 'MyTestStack'

test('Good Stack', () => {
    const app = new cdk.App({
      context: {
        ConnectionId: 'alpha',
        OwnerName: 'beta',
        RepositoryName: 'delta',
        BranchName: 'gamma',
        GreengrassCoreName: 'epsilon'
      }
    });

    const stack = new Cicd.CicdStack(app, STACK_NAME);
    const template = Template.fromStack(stack)

    template.hasResourceProperties('AWS::CodePipeline::Pipeline', { Name: `${STACK_NAME}` });
    template.resourceCountIs('AWS::CodeBuild::Project', 2);
    template.hasResourceProperties('AWS::CodeBuild::Project', { Name: `${STACK_NAME}Build` });
    template.hasResourceProperties('AWS::CodeBuild::Project', { Name: `${STACK_NAME}Deploy` });
    template.resourceCountIs('AWS::S3::Bucket', 1);
    template.resourceCountIs('AWS::CodeBuild::ReportGroup', 1);
    template.hasResourceProperties('AWS::SNS::Topic', { TopicName: `${STACK_NAME}Notification` });
    template.resourceCountIs('AWS::Events::Rule', 1);
});

test('Missing Context Variables', () => {
  const app = new cdk.App();
  expect(() => {
    new Cicd.CicdStack(app, 'STACK_NAME');
  }).toThrow();
});
