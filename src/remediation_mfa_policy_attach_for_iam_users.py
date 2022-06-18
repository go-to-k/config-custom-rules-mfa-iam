import boto3
import logging
import os

session = boto3.Session()
iam_client = session.client('iam')
ssm_client = session.client('ssm')

config_rule_name = os.environ['CONFIG_RULE_NAME']
target_policy_arn = os.environ['TARGET_POLICY_ARN']
ssm_param_key = os.environ['SSM_PARAM_KEY']

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def get_parameters():
    response = ssm_client.get_parameters(
        Names=[
            ssm_param_key,
        ],
        WithDecryption=True
    )
    for parameter in response['Parameters']:
        return parameter['Value']


def lambda_handler(event, _context):
    logger.info(f"event: {str(event)}")

    if 'detail' in event:
        detail = event['detail']
        if 'configRuleName' in detail and detail['configRuleName'] == config_rule_name:
            try:
                ssm_value = get_parameters()
                whitelist_users = [val.strip() for val in ssm_value.split(',')]

                users = iam_client.list_users()
                for user in users['Users']:
                    if detail['resourceId'] == user['UserId'] and user['UserName'] not in whitelist_users:
                        user_policies = iam_client.list_attached_user_policies(
                            UserName=user['UserName'])

                        for policy in user_policies['AttachedPolicies']:
                            if policy['PolicyArn'] == target_policy_arn:
                                return

                        iam_client.attach_user_policy(
                            UserName=user['UserName'],
                            PolicyArn=target_policy_arn,
                        )
                        logger.info(f"user: {user['UserName']}")
            except Exception as e:
                logger.error(f"error: {str(e)}")