#!/usr/bin/env python
#
# Public Domain 2014-present MongoDB, Inc.
# Public Domain 2008-2014 WiredTiger, Inc.
#
# This is free and unencumbered software released into the public domain.
#
# Anyone is free to copy, modify, publish, use, compile, sell, or
# distribute this software, either in source code form or as a compiled
# binary, for any purpose, commercial or non-commercial, and by any
# means.
#
# In jurisdictions that recognize copyright laws, the author or authors
# of this software dedicate any and all copyright interest in the
# software to the public domain. We make this dedication for the benefit
# of the public at large and to the detriment of our heirs and
# successors. We intend this dedication to be an overt act of
# relinquishment in perpetuity of all present and future rights to this
# software under copyright law.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND,
# EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.
# IN NO EVENT SHALL THE AUTHORS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.

import wiredtiger, wttest
from wtscenario import make_scenarios

class test_prepare17(wttest.WiredTigerTestCase):
    session_config = 'isolation=snapshot'
    uri= 'table:test_prepare17'

    key_format_values = [
        ('integer-row', dict(key_format='i')),
        ('column', dict(key_format='r')),
    ]
    update = [
        ('non-prepared', dict(non_prepared=True)),
        ('prepared', dict(non_prepared=False)),
    ]
    scenarios = make_scenarios(key_format_values, update)

    def test_prepare(self):
        create_params = 'key_format={},value_format=S'.format(self.key_format)
        self.session.create(self.uri, create_params)
        cursor = self.session.open_cursor(self.uri)

        # Transaction one
        self.session.begin_transaction()
        cursor[1] = 'a' 
        self.session.prepare_transaction('prepare_timestamp=' + self.timestamp_str(2))
        self.session.commit_transaction('commit_timestamp=' + self.timestamp_str(3)+ ',durable_timestamp=' + self.timestamp_str(6))

        # In the case below, the commit timestamp lies between the previous commit and durable timestamps.
        # Internally, WiredTiger changes the durable timestamp of Transaction one, i.e. 6 to the commit timestamp 
        # of the transaction below, i.e, 4.
        # As per the time window validation the commit timestamp cannot be in between any previous commit and 
        # durable timestamps.
        #
        # Note: The scenario where commit timestamp lies between the previous commit and durable timestamps
        # is not expected from MongoDB, but WiredTiger API can allow it.
        if self.non_prepared:
            self.session.begin_transaction()
            cursor[1] = 'c'
            self.session.commit_transaction('commit_timestamp=' + self.timestamp_str(4))
        else: 
            self.session.begin_transaction()
            cursor[1] = 'c'
            self.session.prepare_transaction('prepare_timestamp=' + self.timestamp_str(3))
            self.session.commit_transaction('commit_timestamp=' + self.timestamp_str(4) + ',durable_timestamp=' + self.timestamp_str(7))

        # Time window validation occurs as part of checkpoint.
        self.session.checkpoint()
