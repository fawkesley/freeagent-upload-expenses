import json
import logging

from os.path import basename
from collections import namedtuple

from attachment import Attachment

LOG = logging.getLogger(__name__)

CATEGORY_KEYWORDS = [
    (365, set(['train', 'oyster', 'contactless', 'transport'])),  # Travel

    # Accom & meals
    (285, set(['lunch', 'dinner', 'breakfast', 'hotel', 'booking.com'])),
]

DEFAULT_CATEGORY = 285  # Default to "Accommodation and Meals"


class Receipt(namedtuple('Receipt', 'filename,date,description,amount')):
    def __eq__(self, other):
        result = (self.date == other.date and
                  self.amount == other.amount and
                  self.description.lower() == other.description.lower())
        if (self.date == other.date and self.amount == other.amount and
                not result):
            print('{} != {}'.format(self.description, other.description))

        return result

    def __hash__(self):
        return hash((self.date, self.amount))

    def __repr__(self):
        return 'Receipt(date={}, amount={}, filename={}'.format(
            self.date, self.amount, basename(self.filename))

    def serialize_as_expense(self, user_url, project_url):
        attachment = Attachment(self.filename)

        result = {
            'expense': {
                'user': user_url,  # Required
                'category': self.guessed_category,
                'gross_value': str(0 - self.amount),           # Required
                'currency': 'GBP',
                'description': self.description,    # Required
                'dated_on': self.date.isoformat(),  # Required
                'manual_sales_tax_amount': '0.00',
                'project': project_url,
                'rebill_type': None,
                'attachment': attachment.serialize(),

            }
        }
        return result

    def serialize_as_explanation(self, transaction_url, project_url):
        attachment = Attachment(self.filename)

        result = {
            'bank_transaction_explanation': {
                'bank_transaction': transaction_url,
                'description': self.description,
                'category': self.guessed_category,
                'gross_value': str(0 - self.amount),           # Required
                'project': project_url,
                'dated_on': self.date.isoformat(),
                'rebill_type': None,
                'attachment': attachment.serialize(),
            }
        }
        # LOG.info(json.dumps(result, indent=4))

        return result

    @property
    def guessed_category(self):
        def category_url(category_code):
            return 'https://api.freeagent.com/v2/categories/{}'.format(
                category_code)

        for category_code, keywords in CATEGORY_KEYWORDS:
            for keyword in keywords:
                if keyword in self.description.lower():
                    return category_url(category_code)

        LOG.warning('Failed to guess category for "{}" - defaulting to '
                    '"Accommodation and Meals"'.format(self.description))

        return category_url(DEFAULT_CATEGORY)
