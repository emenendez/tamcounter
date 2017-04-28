import sys
sys.path.append('requirements/')

import itertools
import json
import os

import boto3
from stravalib.client import Client


settings = {
    'segments': {
        'by foot': {
            'hike': [6094058],
            'run': [6306193, 5604733],
            'walk': [3462619],
        },
        'on wheels': {
            'ride': [651728, 776000],
        },
    },
}


def get_unique_activities(client, athlete_id, segments, extra_activity_ids=[]):
    activities = set()
    for segment_id in segments:
        activities.update((effort.activity.external_id for effort in \
            client.get_segment_efforts(segment_id=segment_id, athlete_id=athlete_id)))
    activities.update(extra_activity_ids)
    return activities


def get_activity_counts(event, context):
    client = Client()
    usersTable = boto3.resource('dynamodb').Table('usersTable')
    request = json.loads(event['body'])

    if 'code' in request:
        # Get a per-user access token
        access_token = client.exchange_code_for_token(
            client_id=os.getenv('STRAVA_CLIENT_ID'),
            client_secret=os.getenv('STRAVA_CLIENT_SECRET'),
            code=request['code'],
        )

        # Now store that access token in DynamoDB
        athlete = client.get_athlete()

        usersTable = boto3.resource('dynamodb').Table('usersTable')
        item = {
           'id': athlete.id,
           'access_token': access_token,
        }
        usersTable.put_item(Item=item)

    if 'athlete' in request:
        item = usersTable.get_item(
            Key={
               'id': request['athlete'],
            }
        )['Item']
        client.access_token = item['access_token']

    response = {}
    for segment_category, segment_types in settings['segments'].iteritems():
        response[segment_category] = get_unique_activities(client, item['id'],
            itertools.chain.from_iterable(segment_types.itervalues()))
        # TODO: add extra_activity_ids for each category

    return {
        "statusCode": 200,
        "body": json.dumps(response)
    }
