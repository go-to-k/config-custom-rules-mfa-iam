#!/bin/bash

set -eu

cd $(dirname $0)

TEMPLATE_FILE="template.yml"
STACK_BUCKET="config-custom-rules"
WHITELIST_USER_FILE="./whitelist_users/sample.txt"
REGION="ap-northeast-1"

STACK_NAME="ConfigCustomRules"

WHITELIST_USERS=","
if [ -f ${WHITELIST_USER_FILE} ]; then
  for user in $(cat ${WHITELIST_USER_FILE} | tr -d " \t" | grep -v "^#" | sed -e "s/\([^#]*\)#.*$/\1/g"); do
    if [ -n "${user}" ]; then
      WHITELIST_USERS="${user},${WHITELIST_USERS}"
    fi
  done
fi

BUCKET_PREFIX=$(aws sts get-caller-identity \
  --query "Account" \
  --output text \
  --region ${REGION})

BUCKET_PATH="${BUCKET_PREFIX}-${STACK_BUCKET}"
if [ -z "$(aws s3 ls | grep ${BUCKET_PATH})" ]; then
  aws s3 mb "s3://${BUCKET_PATH}"
fi

sam build --template-file ${TEMPLATE_FILE}

sam deploy \
  --region ${REGION} \
  --stack-name ${STACK_NAME} \
  --s3-bucket ${BUCKET_PATH} \
  --capabilities CAPABILITY_IAM CAPABILITY_NAMED_IAM \
  --parameter-overrides \
  WhitelistUsers=${WHITELIST_USERS} \
  --no-fail-on-empty-changeset
