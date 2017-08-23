import datetime
from decimal import Decimal

from os.path import join as pjoin
from nose.tools import assert_equal


from freeagent_upload import parse_freeagent_expenses, Receipt


def test_parse_expenses_json():
    with open(pjoin('sample_data', '01_expenses.json'), 'r') as f:
        result = parse_freeagent_expenses(f.read())
    expected = set([
        Receipt(
            filename=None,
            date=datetime.date(2015, 6, 1),
            description='Domain purchase, gcalsms.com',
            amount=Decimal('7.36')
        ),
        Receipt(
            filename='2015-05-25 train Liverpool to kettering.pdf',
            date=datetime.date(2015, 5, 29),
            description='Train Liverpool to Kettering Return',
            amount=Decimal('55.7'),
        ),
        ])
    assert_equal(expected, result)
