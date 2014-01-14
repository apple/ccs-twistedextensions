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

from __future__ import print_function

"""
LDAP directory service tests.
"""

import ldap
from mockldap import MockLdap

from twisted.python.constants import NamedConstant, ValueConstant
from twisted.python.filepath import FilePath
from twisted.internet.defer import inlineCallbacks
from twisted.cred.credentials import UsernamePassword
from twisted.trial import unittest

from ...idirectory import QueryNotSupportedError, FieldName as BaseFieldName
# from ...expression import (
#     CompoundExpression, Operand, MatchExpression, MatchType, MatchFlags
# )
from .._service import (
    DEFAULT_FIELDNAME_MAP, DEFAULT_RECORDTYPE_MAP,
    LDAPBindAuthError,
    DirectoryService, DirectoryRecord,
)

from ...test import test_directory
from ...test.test_xml import (
    xmlService,
    DirectoryServiceConvenienceTestMixIn
    as BaseDirectoryServiceConvenienceTestMixIn,
)


class BaseTestCase(object):
    """
    Tests for L{DirectoryService}.
    """

    url = "ldap://localhost/"
    baseDN = u"ou=calendarserver,o=org"
    realmName = unicode(url)


    def setUp(self):
        self.xmlSeedService = xmlService(self.mktemp())
        self.mockData = mockDirectoryDataFromXMLService(self.xmlSeedService)

        if False:
            from pprint import pprint
            print("")
            print("-" * 80)
            pprint(self.mockData)
            print("-" * 80)

        self.mockLDAP = MockLdap(self.mockData)
        self.mockLDAP.start()


    def tearDown(self):
        self.mockLDAP.stop()


    def service(self, **kwargs):
        return DirectoryService(url=self.url, baseDN=self.baseDN, **kwargs)



class DirectoryServiceConvenienceTestMixIn(
    BaseDirectoryServiceConvenienceTestMixIn
):
    def test_recordsWithRecordType_unknown(self):
        service = self.service()

        self.assertRaises(
            QueryNotSupportedError,
            service.recordsWithRecordType, object()
        )



class DirectoryServiceConnectionTestMixIn(object):
    @inlineCallbacks
    def test_connect_defaults(self):
        """
        Connect with default arguments.
        """
        service = self.service()
        connection = yield service._connect()

        self.assertEquals(connection.methods_called(), ["initialize"])

        for option in (
            ldap.OPT_TIMEOUT,
            ldap.OPT_X_TLS_CACERTFILE,
            ldap.OPT_X_TLS_CACERTDIR,
            ldap.OPT_DEBUG_LEVEL,
        ):
            self.assertRaises(KeyError, connection.get_option, option)

        self.assertFalse(connection.tls_enabled)


    def test_connect_withUsernamePassword_invalid(self):
        """
        Connect with UsernamePassword credentials.
        """
        credentials = UsernamePassword(
            u"uid=wsanchez,cn=user,ou=calendarserver,o=org",
            u"__password__"
        )
        service = self.service(credentials=credentials)
        self.assertFailure(service._connect(), LDAPBindAuthError)


    @inlineCallbacks
    def test_connect_withUsernamePassword_valid(self):
        """
        Connect with UsernamePassword credentials.
        """
        credentials = UsernamePassword(
            u"uid=wsanchez,cn=user,ou=calendarserver,o=org",
            u"zehcnasw"
        )
        service = self.service(credentials=credentials)
        connection = yield service._connect()

        self.assertEquals(
            connection.methods_called(),
            ["initialize", "simple_bind_s"]
        )


    @inlineCallbacks
    def test_connect_withOptions(self):
        """
        Connect with default arguments.
        """
        service = self.service(
            timeout=18,
            tlsCACertificateFile=FilePath("/path/to/cert"),
            tlsCACertificateDirectory=FilePath("/path/to/certdir"),
            debug=True,
        )
        connection = yield service._connect()

        self.assertEquals(
            connection.methods_called(),
            [
                "initialize",
                "set_option", "set_option", "set_option", "set_option",
            ]
        )

        opt = lambda k: connection.get_option(k)

        self.assertEquals(opt(ldap.OPT_TIMEOUT), 18)
        self.assertEquals(opt(ldap.OPT_X_TLS_CACERTFILE), "/path/to/cert")
        self.assertEquals(opt(ldap.OPT_X_TLS_CACERTDIR), "/path/to/certdir")
        self.assertEquals(opt(ldap.OPT_DEBUG_LEVEL), 255)

        # Tested in test_connect_defaults, but test again here since we're
        # setting SSL options and we want to be sure they don't somehow enable
        # SSL implicitly.
        self.assertFalse(connection.tls_enabled)


    @inlineCallbacks
    def test_connect_withTLS(self):
        """
        Connect with TLS enabled.
        """
        service = self.service(useTLS=True)
        connection = yield service._connect()

        self.assertEquals(
            connection.methods_called(),
            ["initialize", "start_tls_s"]
        )

        self.assertTrue(connection.tls_enabled)



class DirectoryServiceTest(
    BaseTestCase,
    DirectoryServiceConvenienceTestMixIn,
    DirectoryServiceConnectionTestMixIn,
    test_directory.BaseDirectoryServiceTest,
    unittest.TestCase,
):
    serviceClass = DirectoryService
    directoryRecordClass = DirectoryRecord



def mockDirectoryDataFromXMLService(service):
    o = u"org"
    ou = u"calendarserver"

    data = {
        u"o={o}".format(o=o): dict(o=o),
        u"ou={ou},o={o}".format(ou=ou, o=o): dict(ou=ou),
    }

    def toUnicode(obj):
        if isinstance(obj, (NamedConstant, ValueConstant)):
            return obj.name

        if isinstance(obj, (tuple, list)):
            return [unicode(x) for x in obj]

        return unicode(obj)

    def tuplify(record, fieldName):
        name = DEFAULT_FIELDNAME_MAP.get(fieldName, fieldName.name)

        if fieldName is BaseFieldName.recordType:
            value = DEFAULT_RECORDTYPE_MAP[record.fields[fieldName]]
        else:
            value = toUnicode(record.fields[fieldName])

        return (name, value)

    for records in service.index[service.fieldName.uid].itervalues():
        for record in records:
            dn = u"uid={uid},cn={cn},ou={ou},o={o}".format(
                uid=record.shortNames[0], cn=record.recordType.name, ou=ou, o=o
            )

            recordData = dict(
                tuplify(record, fieldName)
                for fieldName in service.fieldName.iterconstants()
                if fieldName in record.fields
            )

            data[dn] = recordData

    return data
