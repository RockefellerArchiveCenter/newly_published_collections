#!/usr/bin/env python3

"""Post a list of newly published archival collections to a Microsoft Teams channel.

Requires the following environment variables to be set:
    - AWS_ACCESS_KEY_ID
    - AWS_SECRET_ACCESS_KEY
    - AWS_BUCKET_NAME
    - AS_BASEURL
    - AS_USERNAME
    - AS_PASSWORD
"""

import calendar
import json
import logging
from datetime import datetime
from os import environ

import boto3
import requests
import shortuuid
from asnake.aspace import ASpace

PREVIOUS_RESULTS_KEY = "results.json"

logger = logging.getLogger()
logger.setLevel(logging.INFO)


def main(event, context):
    url = "https://rockarchorg.webhook.office.com/webhookb2/6af11fd0-82fd-4071-ac16-373d9cee9d88@cd5cff62-bf10-444c-be6a-8f045c6f10d6/IncomingWebhook/c1395668419c463ab46d32eb7ec6ba10/4aeb25ac-1389-42dc-88a9-d47cbceb394e"
    date_format_string = '%B %e, %Y'
    s3_client = boto3('s3')

    today = datetime.now()
    prev_month = today.month - 1
    from_date = datetime(
        year=today.year,
        month=prev_month,
        day=1,
        hour=0,
        minute=0,
        second=0)
    to_date = datetime(
        year=today.year,
        month=prev_month,
        day=calendar.monthrange(
            today.year,
            prev_month)[1],
        hour=0,
        minute=0,
        second=0)

    previous_as_results = get_aspace_previously_published(s3_client)
    as_results = get_updated_archivesspace_resources(previous_as_results)
    cartographer_results = get_updated_cartographer_maps(from_date)
    formatted_results = [
        format_result(r) for r in as_results +
        cartographer_results] if len(
        as_results +
        cartographer_results) else no_results()

    message = {
        "$schema": "http://adaptivecards.io/schemas/adaptive-card.json",
        "type": "AdaptiveCard",
        "version": "1.0",
        "body": [
            {
                "type": "Container",
                "padding": "Default",
                "spacing": "None",
                "style": "emphasis",
                "items": [
                    {
                        "type": "TextBlock",
                        "text": f"Collections published between {from_date.strftime(date_format_string)} and {to_date.strftime(date_format_string)}",
                        "wrap": True,
                        "weight": "Bolder",
                        "size": "Large"
                    }
                ]
            },
            {
                "type": "Container",
                "padding": {
                    "top": "Small",
                    "bottom": "Small",
                    "left": "Small",
                    "right": "Default"
                },
                "spacing": "Small",
                "separator": True,
                "items": formatted_results,
                "horizontalAlignment": "Left"
            }
        ],
        "padding": "None"
    }

    print(message)

    encoded_msg = json.dumps(message).encode('utf-8')
    response = requests.post(url, body=encoded_msg)

    update_aspace_previously_published(as_results, s3_client)

    logger.info('Status Code: {}'.format(response.status))
    logger.info('Response: {}'.format(response.data))


def format_result(result):
    """Creates a formatted TextBlock from a result."""
    dimes_id = shortuuid.uuid(name=result['uri'])
    return {
        "type": "TextBlock",
        "text": f"[{result['title']}](https://dimes.rockarch.org/collections/{dimes_id})",
        "wrap": True}


def get_updated_archivesspace_resources(previously_published):
    """Gets updated resource records from ArchivesSpace."""
    client = ASpace(
        baseurl=environ.get('AS_BASEURL'),
        username=environ.get('AS_USERNAME'),
        password=environ.get('AS_PASSWORD')).client
    current_published = client.get_paged(
        "/search?q=publish:true&type[]=resource&fields[]=title,uri")
    return [p for p in current_published if p not in previously_published]


def get_updated_cartographer_maps(from_date):
    """Gets updated maps from Cartographer."""
    resp = requests.get(
        f"{environ.get('CARTOGRAPHER_BASEURL')}/api/maps/?modified_since={int(from_date.timestamp())}")
    resp.raise_for_status()
    maps = resp.json()['results']
    for idx, map in enumerate(maps):
        map_data = requests.get(
            f"{environ.get('CARTOGRAPHER_BASEURL')}{map['ref']}").json()
        maps[idx]['uri'] = map_data['children'][0]['archivesspace_uri']
    return maps


def no_results():
    """Returns a formatted TextBlock for cases when there are no newly published collections."""
    return {
        "type": "TextBlock",
        "text": "No newly published collections for this period.",
        "wrap": True}


def get_aspace_previously_published(client):
    """Gets a list of previously published collections from an AWS bucket."""
    object = client.get_object(
        Bucket=environ.get('AWS_BUCKET_NAME'),
        Key=environ.get('PREVIOUS_RESULTS_KEY'))
    return json.loads(object['Body'].read())
    # or json.load(object['Body'])


def update_aspace_previously_published(results, client):
    """Updates a list of previously published collections in an AWS bucket."""
    client.put_object(
        Bucket=environ.get('AWS_BUCKET_NAME'),
        Key=environ.get('PREVIOUS_RESULTS_KEY'),
        Body=results)


if __name__ == "__main__":
    main()
