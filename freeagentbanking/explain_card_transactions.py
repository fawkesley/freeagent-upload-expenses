#!/usr/bin/env python

import os
import sys
import json
import logging

from collections import defaultdict, OrderedDict
from datetime import timedelta
from decimal import Decimal
from pprint import pformat

import requests

from utils import (
    get_receipts_in_directory, parse_iso_date, archive_receipt,
    get_freeagent_headers)


FREEAGENT_ACCESS_TOKEN = os.environ['FREEAGENT_ACCESS_TOKEN']
BANK_ACCOUNT = os.environ['FREEAGENT_BANK_ACCOUNT_ID']
COMPANY_CARD_RECEIPTS_DIR = os.environ['COMPANY_CARD_RECEIPTS_DIR']
PROJECT_URL = os.environ['FREEAGENT_PROJECT_URL']


class Transaction(object):
    def __init__(self, api_object):
        self.date = parse_iso_date(api_object['dated_on'])
        self.amount = Decimal(api_object['amount'])
        self.unexplained_amount = Decimal(api_object['unexplained_amount'])
        self.full_description = api_object['full_description']
        self.is_manual = api_object['is_manual']
        self.url = api_object['url']

    def __repr__(self):
        return 'Transaction(date={}, amount={}, "{}")'.format(
            self.date, self.amount, self.full_description)

    @property
    def is_automatic(self):
        return not self.is_manual

    @property
    def is_outgoing(self):
        # Negative amount means money out of bank
        return self.amount < 0


def main(argv):
    logging.basicConfig(level=logging.DEBUG)
    global LOG
    LOG = logging.getLogger('')

    if len(argv) > 1:
        api_response = load_from_sample_data(argv[1])

    else:
        api_response = download_unexplained_transactions()

    all_transactions = parse_transactions(api_response)

    transactions_to_explain = filter_needs_explaining(all_transactions)
    all_receipts = load_receipts()

    LOG.info('Transactions to explain:\n{}'.format(
        pformat(transactions_to_explain)))

    LOG.info('Receipts:\n {}'.format(pformat(all_receipts)))

    LOG.info('{} unexplained transactions, {} unfiled local receipts'.format(
        len(transactions_to_explain), len(all_receipts)))

    matched, unmatched = match_transactions_to_receipts(
        transactions_to_explain, all_receipts)

    for transaction, receipt in matched.items():
        prompt_and_upload(transaction, receipt)

    for transaction, potential_receipts in unmatched.items():
        LOG.info('Failed to match receipt for {}'.format(transaction))

        for receipt in potential_receipts:
            LOG.info(' ?? {}\n'.format(receipt))


def prompt_and_upload(transaction, receipt):
    print('\n{}'.format(transaction))
    print(' -> {}'.format(receipt))
    response = input('\nLink receipt to this bank transaction? [y/n]')

    if response != 'y':
        return

    response = input('\nLink to currnet project? [y/n]')

    linked_project = PROJECT_URL if response == 'y' else None

    LOG.info('Uploading explanation.')
    if explain_transaction(transaction, receipt, linked_project):
        archive_receipt(receipt)


def explain_transaction(transaction, receipt, project_url):
    def bank_account_url(account):
        return 'https://api.freeagent.com/v2/bank_accounts/{}'.format(account)

    LOG.debug('Uploading {}'.format(receipt))
    serialized = receipt.serialize_as_explanation(
        transaction_url=transaction.url,
        project_url=project_url)

    response = requests.post(
        'https://api.freeagent.com/v2/bank_transaction_explanations/',
        headers=get_freeagent_headers(),
        data=json.dumps(serialized))
    print('Response: {}'.format(response.content))
    response.raise_for_status()
    return True


def load_from_sample_data(json_filename):
    with open(json_filename, 'r') as f:
        return json.load(f)


def download_unexplained_transactions():
    response = requests.get(
        "https://api.freeagent.com/v2/bank_transactions"
        '?bank_account={}'
        '&view=unexplained'.format(BANK_ACCOUNT),
        headers={'Authorization': 'Bearer {}'.format(FREEAGENT_ACCESS_TOKEN)}
    )

    response.raise_for_status()
    return response.json()


def parse_transactions(api_response):
    return map(Transaction, api_response['bank_transactions'])


def filter_needs_explaining(transactions):
    def filter_only_outgoing(t):
        return t.is_outgoing

    def filter_only_automatic(t):
        return t.is_automatic

    def filter_fully_unexplained(t):
        return t.amount == t.unexplained_amount

    transactions = filter(filter_only_outgoing, transactions)
    transactions = filter(filter_only_automatic, transactions)
    transactions = filter(filter_fully_unexplained, transactions)

    return list(transactions)


def load_receipts():
    return list(get_receipts_in_directory(COMPANY_CARD_RECEIPTS_DIR))


def match_transactions_to_receipts(transactions, receipts):
    potential_matches = {t: find_matching_receipts_for(t, receipts)
                         for t in transactions}

    matched = OrderedDict()
    unmatched = defaultdict(list)

    for transaction, potential_receipts in potential_matches.items():
        if len(potential_receipts) == 1:
            matched[transaction] = potential_receipts[0]
        else:
            if len(potential_receipts) > 1:
                LOG.warning('CAREFUL: found several plausible matches '
                            'for: {}'.format(transaction))

            unmatched[transaction].extend(potential_receipts)

    return matched, unmatched


def find_matching_receipts_for(transaction, receipts):
    def is_matching_amount(receipt):
        return transaction.amount == -receipt.amount

    def is_plausible_date(receipt):
        # The transaction date is generally 0-5 days *after* the receipt.
        # I guess this is banking weirdness.

        delta = transaction.date - receipt.date
        return timedelta(2) <= delta <= timedelta(days=5)

    receipts = filter(is_matching_amount, receipts)
    receipts = filter(is_plausible_date, receipts)
    return list(receipts)


if __name__ == '__main__':
    main(sys.argv)
