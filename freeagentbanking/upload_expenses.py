#!/usr/bin/env python

"""
- List a directory of scanned receipts, parsing the description & amount
- From the FreeAgent API, download a list of expenses already created

"""

import json
import os
import logging
import sys

from decimal import Decimal

import requests

from utils import (
    get_receipts_in_directory, parse_iso_date, get_freeagent_headers,
    archive_receipt
)
from receipt import Receipt

USER_URL = os.environ['FREEAGENT_USER_URL']
PROJECT_URL = os.environ['FREEAGENT_PROJECT_URL']


DESCRIPTION_REPLACEMENTS = [
    ('liverpool', 'Liverpool'),
    ('london', 'London'),
]


def main():
    process_directory(os.environ['PERSONAL_CARD_RECEIPTS_DIR'])
    return 0


def process_directory(directory):
    local_receipts = set(get_receipts_in_directory(directory))

    if not local_receipts:
        LOG.info('No local receipts, nothing to do.')
        return

    remote_receipts = download_freeagent_expenses(
        from_date=get_earliest_receipt(local_receipts).date
    )

    receipts_already_uploaded = remote_receipts.intersection(local_receipts)

    for receipt in receipts_already_uploaded:
        LOG.info('Already uploaded, archiving: "{}"'.format(
            receipt.description))
        archive_receipt(receipt)

    receipts_not_uploaded = local_receipts - remote_receipts

    print('{} local receipts, {} remote receipts, {} to upload'.format(
        len(local_receipts), len(remote_receipts), len(receipts_not_uploaded)))

    for receipt in sorted(receipts_not_uploaded):
        print('\n{date}\n{description}\n£{amount}'.format(
            date=receipt.date,
            description=receipt.description,
            amount=receipt.amount))

        response = input('\nUpload now? [y/n]')

        if response != 'y':
            continue

        try:
            upload_expenses_receipt(receipt)
        except Exception as e:
            LOG.exception(e)
        else:
            archive_receipt(receipt)


def get_earliest_receipt(receipts):
    if len(receipts) == 0:
        raise RuntimeError("Can't get earliest receipt from empty list.")

    earliest_receipt = sorted(receipts, key=lambda r: r.date)[0]
    LOG.info('Earliest local receipt: {}'.format(earliest_receipt))
    return earliest_receipt


def upload_expenses_receipt(receipt):
    LOG.debug('Uploading {}'.format(receipt))
    serialized = receipt.serialize_as_expense(
        user_url=USER_URL, project_url=PROJECT_URL)

    response = requests.post(
        'https://api.freeagent.com/v2/expenses/',
        headers=get_freeagent_headers(),
        data=json.dumps(serialized))
    print('Response: {}'.format(response.content))
    response.raise_for_status()


def download_freeagent_expenses(from_date):
    page = 1
    combined_set = set()
    while True:
        url = (
            'https://api.freeagent.com/v2/expenses/'
            '?from_date={}&page={}').format(from_date, page)
        LOG.info(url)

        response = requests.get(url, headers=get_freeagent_headers())
        response.raise_for_status()
        page_set = parse_freeagent_expenses(response.text)
        if len(page_set):
            combined_set.update(page_set)
            page += 1
        else:
            break

    return combined_set


def parse_freeagent_expenses(expenses_string):
    receipts = set()
    for expense in json.loads(expenses_string)['expenses']:
        try:
            filename = expense['attachment']['file_name']
        except KeyError:
            filename = None

        receipts.add(
            Receipt(
                description=expense['description'],
                date=parse_iso_date(expense['dated_on']),
                amount=0 - Decimal(expense['gross_value']),
                filename=filename,
            )
        )
    return receipts


if __name__ == '__main__':
    logging.basicConfig(level=logging.INFO)
    LOG = logging.getLogger('')
    sys.exit(main())
else:
    LOG = logging.getLogger('')
