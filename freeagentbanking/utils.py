#!/usr/bin/env python

"""
- List a directory of scanned receipts, parsing the description & amount
- From the FreeAgent API, download a list of expenses already created

"""

import datetime
import os
import logging
import re
import shutil

from decimal import Decimal
from os.path import join as pjoin

from receipt import Receipt

LOG = logging.getLogger(__name__)


DESCRIPTION_REPLACEMENTS = [
    ('liverpool', 'Liverpool'),
    ('london', 'London'),
]


FILENAME_PATTERN = re.compile(
    '(?P<year>\d{4})-(?P<month>\d{2})-(?P<day>\d{2}) '
    '(?P<description>.+) '
    '(?P<amount>\d{1,3}\.\d{2})'
    '.pdf'
)


def get_receipts_in_directory(directory):
    LOG.info('Looking in: {}'.format(directory))

    def only_files(partial_filename):
        return os.path.isfile(pjoin(directory, partial_filename))

    for filename_base in filter(only_files, os.listdir(directory)):
        match = match_filename(filename_base)
        if match is not None:
            yield Receipt(
                filename=pjoin(directory, filename_base),
                description=tidy_description(match.group('description')),
                date=reconstruct_date(match.groupdict()),
                amount=Decimal(match.group('amount'))
            )
        else:
            LOG.warning('Non-matching filename {}'.format(filename_base))


def tidy_description(description):
    description = description.capitalize()

    for replace, with_ in DESCRIPTION_REPLACEMENTS:
        description = description.replace(replace, with_)

    return description


def match_filename(filename_base):
    """
    >>> match_filename('2015-11-31 Lunch 2.50.pdf').groups()
    ('2015', '11', '31', 'Lunch', '2.50')

    >>> match_filename('2015-11-31 Two words 123.99.pdf').groups()
    ('2015', '11', '31', 'Two words', '123.99')
    """
    return FILENAME_PATTERN.match(filename_base)


def reconstruct_date(match_groups):
    return datetime.date(
        int(match_groups['year']),
        int(match_groups['month']),
        int(match_groups['day']))


def parse_iso_date(iso_date):
    """
    >>> parse_iso_date('2015-08-09')
    datetime.datetime(2015, 8, 9)
    """
    return datetime.date(*[int(part) for part in iso_date.split('-')])


def get_freeagent_headers():

    token = os.environ['FREEAGENT_ACCESS_TOKEN']

    headers = {
        'content-type': 'application/json',
        'Authorization': 'Bearer {}'.format(token),
    }
    return headers


def archive_receipt(receipt):
    directory, filename = os.path.split(receipt.filename)

    archive_filename = os.path.join(directory, 'uploaded', filename)
    LOG.info('OK, archiving receipt to: {}'.format(archive_filename))
    shutil.move(receipt.filename, archive_filename)
