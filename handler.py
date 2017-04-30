import sys
sys.path.append('requirements/')

import itertools
import json
import os

import boto3
from stravalib.client import Client


settings = {
    'segments': {
        'by_foot': {
            'hike': [6094058],
            'run': [6306193, 5604733],
            'walk': [3462619],
        },
        'on_wheels': {
            'ride': [651728, 776000],
        },
    },
}


class UsersTable(object):
    def __init__(self):
        self.table = boto3.resource('dynamodb').Table('usersTable')

    def get(self, id):
        return self.table.get_item(
            Key={
               'id': int(id),
            },
            ReturnConsumedCapacity='NONE',
        ).get('Item')

    def update(self, id, access_token):
        return self.table.update_item(
            Key={
                'id': int(id),
            },
            UpdateExpression='SET access_token = :access_token',
            ExpressionAttributeValues={
                ':access_token': access_token,
            },
            ReturnValues='ALL_NEW',
            ReturnConsumedCapacity='NONE',
        ).get('Attributes')


def get_unique_activities(client, athlete_id, segments, extra_activity_ids=[]):
    activities = set()
    for segment_id in segments:
        activities.update((effort.activity.id for effort in \
            client.get_segment_efforts(segment_id=segment_id, athlete_id=athlete_id)))
    activities.update(extra_activity_ids)
    return list(activities)


def get_activity_counts(event, context):
    client = Client()
    usersTable = UsersTable()
    request = json.loads(event['body'])

    if 'code' in request:
        # We have been redirected here from the Strava OAuth flow. Use the
        # provided code to get a per-user access token.
        access_token = client.exchange_code_for_token(
            client_id=os.getenv('STRAVA_CLIENT_ID'),
            client_secret=os.getenv('STRAVA_CLIENT_SECRET'),
            code=request['code'],
        )

        # Now get the athlete info
        # TODO: Modify stravalib to get this directly from the api call above
        athlete = client.get_athlete()

        # Now store that access token in DynamoDB. Update to make sure we don't
        # overwrite any extra attributes for existing users.
        item = usersTable.update(id=athlete.id, access_token=access_token)

    if 'athlete' in request:
        # Retreive the athlete-specific access token.
        item = usersTable.get(request['athlete'])
        client.access_token = item['access_token']

    # Calculate the Tamcount
    response = {
        'athlete_id': int(item['id']),
        'activities': {},
    }
    for segment_category, segment_types in settings['segments'].iteritems():
        response['activities'][segment_category] = get_unique_activities(
            client,
            item['id'],
            itertools.chain.from_iterable(segment_types.itervalues()),
            map(int, item.get('extra_' + segment_category, set())))

    return {
        "statusCode": 200,
        "headers": {
            "Access-Control-Allow-Origin": os.getenv("ORIGIN", "*"),
        },
        "body": json.dumps(response)
    }
