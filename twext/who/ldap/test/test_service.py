##
# Copyright (c) 2013-2014 Apple Inc. All rights reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
##

"""
LDAP directory service tests.
"""

import ldap
from mockldap import MockLdap

from twisted.internet.defer import inlineCallbacks
from twisted.trial import unittest

# from ...expression import (
#     CompoundExpression, Operand, MatchExpression, MatchType, MatchFlags
# )
from .._service import DirectoryService, DirectoryRecord, DEFAULT_URL

from ...test import test_directory



class BaseTestCase(object):
    """
    Tests for L{DirectoryService}.
    """

    url = DEFAULT_URL
    realmName = unicode(DEFAULT_URL)


    def setUp(self):
        # super(BaseTestCase, self).setUp()
        self.mockLDAP = MockLdap(mockDirectoryData)
        self.mockLDAP.start()


    def tearDown(self):
        self.mockLDAP.stop()
        # super(BaseTestCase, self).tearDown()


    def service(self, subClass=None, xmlData=None):
        return DirectoryService()



class DirectoryServiceConvenienceTestMixIn(BaseTestCase):
    def _unimplemented(self):
        raise NotImplementedError()

    _unimplemented.todo = "unimplemented"


    test_recordWithUID = _unimplemented
    test_recordWithGUID = _unimplemented
    test_recordsWithRecordType = _unimplemented
    test_recordWithShortName = _unimplemented
    test_recordsWithEmailAddress = _unimplemented



class DirectoryServiceTest(
    DirectoryServiceConvenienceTestMixIn,
    test_directory.BaseDirectoryServiceTest,
    unittest.TestCase,
):
    serviceClass = DirectoryService
    directoryRecordClass = DirectoryRecord


    @inlineCallbacks
    def test_connect_defaults(self):
        """
        Connect with default arguments.
        """
        service = self.service()
        connection = yield service._connect()

        for option in (
            ldap.OPT_DEBUG_LEVEL,
            ldap.OPT_TIMEOUT,
            ldap.OPT_X_TLS_CACERTFILE,
            ldap.OPT_X_TLS_CACERTDIR,
        ):
            self.assertRaises(
                KeyError,
                connection.get_option, option
            )



mockDirectoryData = dict(
)
