# dependency tasks
Post a list of newly published archival collections to a Microsoft Teams channel.

## Dependencies
- Python 3 (tested on 3.9)
- [ArchivesSnake](https://pypi.org/project/boto3/)
- [boto3](https://pypi.org/project/ArchivesSnake/)
- [requests](https://pypi.org/project/requests/)
- [shortuuid](https://pypi.org/project/shortuuid/)

## Usage
The following environment variables are required:
- AWS_ACCESS_KEY_ID - an access key for an AWS IAM user that has permissions to
  write to the S3 bucket specified by `AWS_BUCKET_NAME`.
- AWS_SECRET_ACCESS_KEY - a secret key for an AWS IAM user that has permissions to
  write to the S3 bucket specified by `AWS_BUCKET_NAME`.
- BUCKET_NAME - an S3 bucket in which to store a list of published collections.
- AS_BASEURL - base URL of the ArchivesSpace instance to check for newly
  published resource records.
- AS_USERNAME - username for an ArchivesSpace user with access to the `search` endpoint.
- AS_PASSWORD - password for an ArchivesSpace user with access to the `search` endpoint.
- CARTOGRAPHER_BASEURL - base URL of the Cartographer instance to check for
  newly published arrangement maps.
- TEAMS_URL - the webhook URL for a Teams channel in which newly published collections should be posted.

This source code is intended to be run as a [container image in AWS Lambda](https://docs.aws.amazon.com/lambda/latest/dg/python-image.html).

## License
The code in this repository is released under an MIT License.
