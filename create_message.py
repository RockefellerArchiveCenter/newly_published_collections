#!/usr/bin/env python3

"""Post a list of newly published archival collections to a Microsoft Teams channel.

Requires the following encrypted environment variables to be set:
    - ACCESS_KEY_ID - an access key for an AWS IAM user that has permissions to
      write to the S3 bucket specified by `BUCKET_NAME`.
    - SECRET_ACCESS_KEY - a secret key for an AWS IAM user that has permissions to
      write to the S3 bucket specified by `BUCKET_NAME`.
    - BUCKET_NAME - an S3 bucket in which to store a list of published collections.
    - AS_BASEURL - base URL of the ArchivesSpace instance to check for newly
      published resource records.
    - AS_USERNAME - username for an ArchivesSpace user with access to the `search` endpoint.
    - AS_PASSWORD - password for an ArchivesSpace user with access to the `search` endpoint.
    - CARTOGRAPHER_BASEURL - base URL of the Cartographer instance to check for
      newly published arrangement maps.
    - TEAMS_URL - the webhook URL for a Teams channel in which newly published collections should be posted.
"""

import calendar
import json
from base64 import b64decode
from datetime import datetime
from os import environ

import boto3
import requests
import shortuuid
from asnake.aspace import ASpace

PREVIOUS_RESULTS_KEY = "results.json"


def main(event=None, context=None):
    url = decrypt_env_variable('TEAMS_URL')
    date_format_string = '%B %e, %Y'
    s3_client = boto3.client('s3',
                             aws_access_key_id=decrypt_env_variable('ACCESS_KEY_ID'),
                             aws_secret_access_key=decrypt_env_variable('SECRET_ACCESS_KEY'))

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
        day=calendar.monthrange(today.year, prev_month)[1],
        hour=0,
        minute=0,
        second=0)

    previous_as_results = get_aspace_previously_published(s3_client)
    new_updates = list(get_updated_archivesspace_resources())

    as_results = [format_result(n) for n in new_updates if n not in previous_as_results]
    cartographer_results = [format_result(r) for r in get_updated_cartographer_maps(from_date)]

    message = {
        "@context": "https://schema.org/extensions",
        "type": "MessageCard",
        "title": f"New collections and updated arrangement maps from {from_date.strftime(date_format_string)} through {to_date.strftime(date_format_string)}",
        "summary": "The following collections were recently updated or created.",
        "sections": [
            {
                "title": "## Newly Published Collections",
                "text": "   \n".join(as_results) if len(as_results) else "No new collections published during this period."
            },
            {
                "title": "## Updated Arrangement Maps",
                "text": "   \n".join(cartographer_results) if len(cartographer_results) else "No updated maps during this period."
            }
        ]
    }

    encoded_msg = json.dumps(message).encode('utf-8')
    requests.post(url, data=encoded_msg)

    update_aspace_previously_published(new_updates, s3_client)


def decrypt_env_variable(env_key):
    encrypted = environ.get(env_key)
    return boto3.client('kms').decrypt(
        CiphertextBlob=b64decode(encrypted),
        EncryptionContext={'LambdaFunctionName': environ['AWS_LAMBDA_FUNCTION_NAME']}
    )['Plaintext'].decode('utf-8')


def format_result(result):
    """Creates a formatted DIMES link from a result."""
    dimes_id = shortuuid.uuid(name=result['uri'])
    return f"[{result['title']}](https://dimes.rockarch.org/collections/{dimes_id})"


def get_updated_archivesspace_resources():
    """Gets updated resource records from ArchivesSpace."""
    client = ASpace(
        baseurl=decrypt_env_variable('AS_BASEURL'),
        username=decrypt_env_variable('AS_USERNAME'),
        password=decrypt_env_variable('AS_PASSWORD')).client
    return client.get_paged(
        "/search?q=publish:true&type[]=resource&fields[]=title,uri")


def get_updated_cartographer_maps(from_date):
    """Gets updated maps from Cartographer."""
    resp = requests.get(
        f"{decrypt_env_variable('CARTOGRAPHER_BASEURL')}/api/maps/?modified_since={int(from_date.timestamp())}")
    resp.raise_for_status()
    maps = resp.json()['results']
    for idx, map in enumerate(maps):
        map_data = requests.get(
            f"{decrypt_env_variable('CARTOGRAPHER_BASEURL')}{map['ref']}").json()
        maps[idx]['uri'] = map_data['children'][0]['archivesspace_uri']
    return maps


def get_aspace_previously_published(client):
    """Gets a list of previously published collections from an AWS bucket."""
    object = client.get_object(
        Bucket=decrypt_env_variable("BUCKET_NAME"),
        Key=PREVIOUS_RESULTS_KEY)
    return json.loads(object['Body'].read())


def update_aspace_previously_published(results, client):
    """Updates a list of previously published collections in an AWS bucket."""
    client.put_object(
        Bucket=decrypt_env_variable('BUCKET_NAME'),
        Key=PREVIOUS_RESULTS_KEY,
        Body=bytes(json.dumps(results), 'utf-8'))


if __name__ == "__main__":
    main()
