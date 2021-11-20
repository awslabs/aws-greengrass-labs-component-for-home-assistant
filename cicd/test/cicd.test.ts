// Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
// SPDX-License-Identifier: Apache-2.0

import { expect as expectCDK, haveResource, countResources } from '@aws-cdk/assert';
import * as cdk from '@aws-cdk/core';
import * as Cicd from '../lib/cicd-stack';

test('Good Stack', () => {
    const app = new cdk.App({
      context: {
        RepositoryName: 'alpha',
        BranchName: 'beta',
        GreengrassCoreName: 'delta'
      }
    });

    const stack = new Cicd.CicdStack(app, 'MyTestStack');

    expectCDK(stack).to(haveResource('AWS::CodePipeline::Pipeline', { 'Name': 'gg-ha-cicd-pipeline' }));
    expectCDK(stack).to(haveResource('AWS::CodeBuild::Project', { 'Name': 'gg-ha-cicd-build' }));
    expectCDK(stack).to(haveResource('AWS::CodeBuild::Project', { 'Name': 'gg-ha-cicd-deploy' }));
    expectCDK(stack).to(countResources('AWS::S3::Bucket', 1));
    expectCDK(stack).to(countResources('AWS::CodeBuild::ReportGroup', 1));
    expectCDK(stack).to(haveResource('AWS::SNS::Topic', { 'TopicName': 'gg-ha-cicd-notification' }));
    expectCDK(stack).to(countResources('AWS::Events::Rule', 2));
});

test('Missing Context Variables', () => {
  const app = new cdk.App();
  expect(() => {
    new Cicd.CicdStack(app, 'MyTestStack');
  }).toThrowError();
});
