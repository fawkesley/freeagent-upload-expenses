#!/bin/bash -eux

. credentials.sh

./refresh_token.py

. credentials.sh

set +x
echo "Now:"
echo "$ source credentials.sh"
echo "$ ./freeagentbanking/explain_card_transactions.py"
echo "$ ./freeagentbanking/upload_expenses.py"
