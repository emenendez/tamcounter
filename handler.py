import sys
sys.path.append('requirements/')

import itertools
import json
import threading
import os
from collections import defaultdict
from decimal import Decimal

import boto3
from raven import Client as Raven
from stravalib.client import Client


raven = Raven(os.getenv('RAVEN_DSN'))

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


class Activity(dict):
    def __init__(self, effort):
        if isinstance(effort, Decimal):
            self['id'] = int(effort)
        else:
            self['id'] = effort.activity.id
            self['private'] = effort.activity.private
            if not self['private']:
                self['name'] = effort.activity.name
                self['start_date_local'] = effort.activity.start_date_local

    def __cmp__(self, other):
        if isinstance(other, Activity):
            return self['id'].__cmp__(other['id'])
        else:
            return self['id'].__cmp__(other)

    def __hash__(self):
        return self['id']


class StravaClient(Client):
    @property
    def athlete_id(self):
        return self._athlete_id

    @athlete_id.setter
    def athlete_id(self, v):
        self._athlete_id = int(v)

    def get_segment_efforts(self, activities_set, segment_id):
        activities_set.update(
            map(Activity, super(StravaClient, self).get_segment_efforts(
                segment_id=segment_id,
                athlete_id=self.athlete_id)))


def get_activity_counts(event, context):
    try:
        strava = StravaClient()
        usersTable = UsersTable()
        request = json.loads(event['body'])

        if 'code' in request:
            # We have been redirected here from the Strava OAuth flow. Use the
            # provided code to get a per-user access token.
            athlete = strava.exchange_code_for_token(
                client_id=os.getenv('STRAVA_CLIENT_ID'),
                client_secret=os.getenv('STRAVA_CLIENT_SECRET'),
                code=request['code'],
            )

            # Now store that access token in DynamoDB. Update to make sure we don't
            # overwrite any extra attributes for existing users.
            item = usersTable.update(id=athlete.id, access_token=strava.access_token)

        if 'athlete' in request:
            # Retreive the athlete-specific access token.
            item = usersTable.get(request['athlete'])
            strava.access_token = item['access_token']

        # Set the athlete ID on the Strava client
        strava.athlete_id = item['id']

        # Get efforts for each segment
        activities = defaultdict(set)
        threads = []
        for category, types in settings['segments'].iteritems():
            for segment_id in itertools.chain.from_iterable(types.itervalues()):
                threads.append(threading.Thread(
                    target=strava.get_segment_efforts,
                    args=( activities[category], segment_id)))
                threads[-1].start()
            # Add extra activities
            activities[category].update(
                map(Activity, item.get('extra_' + category, [])))

        # Wait for all threads to finish
        for t in threads:
            t.join()

        # Assemble the response
        response = {
            'athlete_id': strava.athlete_id,
            'activities': { category: sorted(efforts) for category, efforts
                            in activities.iteritems() },
        }

        return {
            "statusCode": 200,
            "headers": {
                "Access-Control-Allow-Origin": os.getenv("ORIGIN", "*"),
            },
            "body": json.dumps(response)
        }

    except Exception:
        client.captureException()
