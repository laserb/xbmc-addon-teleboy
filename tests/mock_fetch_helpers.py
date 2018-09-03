import sys
import simplejson
import os
from mock import Mock

fetch_mock = Mock()

test_dir = os.path.dirname(os.path.abspath(__file__))
RECORDINGS_FILE = os.path.join(test_dir, "recordings.dat")
RECORDINGS_BROADCASTS_FILE = os.path.join(test_dir,
                                          "recordings_broadcasts.dat")

with open(RECORDINGS_FILE, 'r') as f:
    s = f.read()
    recordings = simplejson.loads(s)

with open(RECORDINGS_BROADCASTS_FILE, 'r') as f:
    s = f.read()
    broadcasts = simplejson.loads(s)

fetch_mock.get_records.return_value = broadcasts, recordings


sys.modules['fetch_helpers'] = fetch_mock


def reset():
    fetch_mock.reset_mock()
