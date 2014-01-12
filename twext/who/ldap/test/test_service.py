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

# from ...expression import (
#     CompoundExpression, Operand, MatchExpression, MatchType, MatchFlags
# )
from .._service import (
    DEFAULT_URL,
    LDAPBindAuthError,
    DirectoryService, DirectoryRecord,
)

from ...test import test_directory
from ...test.test_xml import xmlService


class BaseTestCase(object):
    """
    Tests for L{DirectoryService}.
    """

    url = DEFAULT_URL
    realmName = unicode(DEFAULT_URL)


    def setUp(self):
        self.mockLDAP = MockLdap(mockDirectoryDataFromXML(self.mktemp()))
        self.mockLDAP.start()


    def tearDown(self):
        self.mockLDAP.stop()


    def service(self, **kwargs):
        return DirectoryService(**kwargs)



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
            u"uid=wsanchez,cn=user,dc=calendarserver,dc=org",
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
            u"uid=wsanchez,cn=user,dc=calendarserver,dc=org",
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



def mockDirectoryDataFromXML(tmp):
    service = xmlService(tmp)

    o = u"org"
    ou = u"calendarserver"

    data = {
        u"o={o}".format(o=o): dict(o=o),
        u"ou={ou}".format(ou=ou): dict(ou=ou),
    }

    def toAttribute(fieldName):
        return unicode({
            service.fieldName.uid: u"recordid",
            service.fieldName.guid: u"guid",
            service.fieldName.recordType: u"objectclass",
            service.fieldName.shortNames: u"uid",
            service.fieldName.fullNames: u"cn",
            service.fieldName.emailAddresses: u"mail",
            service.fieldName.password: u"userPassword",
        }.get(fieldName, fieldName.name))

    def toUnicode(obj):
        if isinstance(obj, (NamedConstant, ValueConstant)):
            return obj.name

        if isinstance(obj, (tuple, list)):
            return [unicode(x) for x in obj]

        return unicode(obj)

    def tuplify(record, fieldName):
        name = toAttribute(fieldName)
        value = toUnicode(record.fields[fieldName])
        return (name, value)

    for records in service.index[service.fieldName.uid].itervalues():
        for record in records:
            dn = u"uid={uid},cn={cn},dc={ou},dc={o}".format(
                uid=record.shortNames[0], cn=record.recordType.name, ou=ou, o=o
            )

            recordData = dict(
                tuplify(record, fieldName)
                for fieldName in service.fieldName.iterconstants()
                if fieldName in record.fields
            )

            data[dn] = recordData

    # from pprint import pprint
    # print("")
    # print("-" * 80)
    # pprint(data)
    # print("-" * 80)

    return data
