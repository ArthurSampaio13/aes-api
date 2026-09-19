#!/bin/sh
set -e

awslocal s3 mb "s3://${AES_STORAGE_BUCKET}" 2>/dev/null || true
awslocal sqs create-queue --queue-name "${AES_SQS_QUEUE_NAME}" --attributes VisibilityTimeout=900
QUEUE_URL=$(awslocal sqs get-queue-url --queue-name "${AES_SQS_QUEUE_NAME}" --query QueueUrl --output text)
awslocal sqs set-queue-attributes --queue-url "${QUEUE_URL}" --attributes VisibilityTimeout=900
