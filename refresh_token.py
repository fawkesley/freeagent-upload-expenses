#!/usr/bin/env python

# curl -v -X POST \
#   --user "${APP_OAUTH_IDENTIFIER}:${APP_OAUTH_SECRET}"
#   --header "Content-Type: application/x-www-form-urlencoded;charset=UTF-8"
#   --data "grant_type=refresh_token&refresh_token=${FREEAGENT_REFRESH_TOKEN}"
#   https://api.freeagent.com/v2/token_endpoint

import os
import datetime
import tempfile

from os.path import dirname, join as pjoin

import requests


def main():
    token, expiry_datetime = refresh_token()
    print('Token: {} expires: {}'.format(token, expiry_datetime))

    rewrite_credentials_file(token, expiry_datetime)


def rewrite_credentials_file(token, expiry_datetime):
    """
    Replace this line with the new token:

    export FREEAGENT_ACCESS_TOKEN="1SfYNfN3r0EwwUneKVb7_3_zfsSJrCW7fKkGr6pbf"
    """
    credentials_filename = pjoin(dirname(__file__), 'credentials.sh')
    _, temp_filename = tempfile.mkstemp(prefix='tmp.credentials.sh.',
                                        dir=dirname(credentials_filename))

    have_written_token = False

    with open(credentials_filename, 'r') as f, open(temp_filename, 'w') as g:
        for line in f.readlines():
            if line.startswith('export FREEAGENT_ACCESS_TOKEN'):
                g.write('export FREEAGENT_ACCESS_TOKEN="{}" '
                        '# expires {}\n'.format(token, expiry_datetime))
                have_written_token = True
            else:
                g.write(line)

    if have_written_token:
        os.rename(temp_filename, credentials_filename)
        print('OK, updated {}'.format(credentials_filename))
    else:
        raise RuntimeError('Failed to find line to replace in {}'.format(
            credentials_filename))
        os.unlink(temp_filename)


def refresh_token():
    headers = {
        "Content-Type": "application/x-www-form-urlencoded;charset=UTF-8",
    }

    post_data = {
        "grant_type": "refresh_token",
        "refresh_token": os.environ['FREEAGENT_REFRESH_TOKEN']
    }

    response = requests.post(
        'https://api.freeagent.com/v2/token_endpoint',
        auth=requests.auth.HTTPBasicAuth(
            os.environ['APP_OAUTH_IDENTIFIER'],
            os.environ['APP_OAUTH_SECRET']),
        headers=headers,
        data=post_data,
    )

    response.raise_for_status()
    token = response.json()['access_token']
    expiry_datetime = (
        datetime.datetime.utcnow() +
        datetime.timedelta(seconds=response.json()['expires_in']))

    return token, expiry_datetime


if __name__ == '__main__':
    main()
