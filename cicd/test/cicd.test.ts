// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import * as cdk from 'aws-cdk-lib';
import { Template } from 'aws-cdk-lib/assertions';
import * as Cicd from '../lib/cicd-stack';

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

    const stack = new Cicd.CicdStack(app, 'MyTestStack');
    const template = Template.fromStack(stack)

    template.hasResourceProperties('AWS::CodePipeline::Pipeline', { Name: 'gg-ha-cicd-pipeline' });
    template.resourceCountIs('AWS::CodeBuild::Project', 2);
    template.hasResourceProperties('AWS::CodeBuild::Project', { Name: 'gg-ha-cicd-build' });
    template.hasResourceProperties('AWS::CodeBuild::Project', { Name: 'gg-ha-cicd-deploy' });
    template.resourceCountIs('AWS::S3::Bucket', 1);
    template.resourceCountIs('AWS::CodeBuild::ReportGroup', 1);
    template.hasResourceProperties('AWS::SNS::Topic', { TopicName: 'gg-ha-cicd-notification' });
    template.resourceCountIs('AWS::Events::Rule', 1);
});

test('Missing Context Variables', () => {
  const app = new cdk.App();
  expect(() => {
    new Cicd.CicdStack(app, 'MyTestStack');
  }).toThrow();
});
