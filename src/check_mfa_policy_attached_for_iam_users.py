import boto3
import logging
import os
from datetime import datetime

session = boto3.Session()
iam_client = session.client('iam')
config_client = session.client('config')
ssm_client = session.client('ssm')

target_policy_name = os.environ['TARGET_POLICY_NAME']
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
    logger.info(f'event: {str(event)}')
    result_token = event['resultToken']

    try:
        ssm_value = get_parameters()
        whitelist_users = [val.strip() for val in ssm_value.split(',')]

        iam_users = iam_client.list_users()

        if not iam_users:
            logger.info('IAM User does not exist')
            return

        for user in iam_users['Users']:
            user_name = user['UserName']
            if user_name not in whitelist_users:
                evaluate_compliance(
                    user_name, user['UserId'], result_token)
            else:
                logger.info(f'{user_name} is in whitelists')
    except Exception as e:
        logger.error(f'error: {str(e)}')


def evaluate_compliance(user_name, user_id, result_token):
    try:
        user_policies = iam_client.list_attached_user_policies(
            UserName=user_name)

        compliance_type = 'NON_COMPLIANT'
        for policy_name in user_policies['AttachedPolicies']:
            if target_policy_name in policy_name['PolicyName']:
                compliance_type = 'COMPLIANT'

        logger.info(f'{user_name} is {compliance_type}')
        config_client.put_evaluations(
            Evaluations=[
                {
                    'ComplianceResourceType': 'AWS::IAM::User',
                    'ComplianceResourceId': user_id,
                    'ComplianceType': compliance_type,
                    'OrderingTimestamp': datetime.today()
                }
            ],
            ResultToken=result_token
        )
    except Exception as e:
        return e