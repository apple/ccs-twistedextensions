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

from itertools import chain

import ldap
from mockldap import MockLdap

from mockldap.filter import (
    Test as MockLDAPFilterTest,
    UnsupportedOp as MockLDAPUnsupportedOp,
)

from twisted.python.constants import NamedConstant, ValueConstant
from twisted.python.filepath import FilePath
from twisted.internet.defer import inlineCallbacks
from twisted.cred.credentials import UsernamePassword
from twisted.trial import unittest

from ...idirectory import QueryNotSupportedError, FieldName as BaseFieldName
from .._service import (
    DEFAULT_FIELDNAME_ATTRIBUTE_MAP, DEFAULT_RECORDTYPE_SCHEMAS,
    LDAPBindAuthError,
    DirectoryService, DirectoryRecord,
)

from ...test import test_directory
from ...test.test_xml import (
    xmlService,
    BaseTest as XMLBaseTest, QueryMixIn,
    DirectoryServiceConvenienceTestMixIn
    as BaseDirectoryServiceConvenienceTestMixIn,
    DirectoryServiceRealmTestMixIn,
    DirectoryServiceQueryTestMixIn as BaseDirectoryServiceQueryTestMixIn,
)



TEST_FIELDNAME_MAP = dict(DEFAULT_FIELDNAME_ATTRIBUTE_MAP)
TEST_FIELDNAME_MAP[BaseFieldName.uid] = (u"__who_uid__",)



class TestService(DirectoryService, QueryMixIn):
    pass



class BaseTestCase(XMLBaseTest):
    """
    Tests for L{DirectoryService}.
    """

    url = "ldap://localhost/"
    baseDN = u"dc=calendarserver,dc=org"
    realmName = unicode(url)


    def setUp(self):
        def parse_expression(
            self, upcall=MockLDAPFilterTest._parse_expression
        ):
            try:
                # Try the stock implementation first.
                return upcall(self)

            except MockLDAPUnsupportedOp as e:
                if (
                    len(e.args) == 1 and
                    e.args[0].startswith(u"Wildcard matches are not supported")
                ):
                    return mockldap_parse_wildcard_expression(self)

                raise

        def matches(self, dn, attrs, upcall=MockLDAPFilterTest.matches):
            if upcall(self, dn, attrs):
                return True
            else:
                return mockldap_matches(self, dn, attrs)


        self.patch(MockLDAPFilterTest, "_parse_expression", parse_expression)
        self.patch(MockLDAPFilterTest, "matches", matches)

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
        return TestService(
            url=self.url,
            baseDN=self.baseDN,
            fieldNameToAttributesMap=TEST_FIELDNAME_MAP,
            **kwargs
        )



class DirectoryServiceConvenienceTestMixIn(
    BaseDirectoryServiceConvenienceTestMixIn
):
    def test_recordsWithRecordType_unknown(self):
        service = self.service()

        self.assertRaises(
            QueryNotSupportedError,
            service.recordsWithRecordType, object()
        )


class DirectoryServiceQueryTestMixIn(BaseDirectoryServiceQueryTestMixIn):
    def test_queryNot(self):
        return BaseDirectoryServiceQueryTestMixIn.test_queryNot(self)

    test_queryNot.todo = "?"


    def test_queryNotNoIndex(self):
        return BaseDirectoryServiceQueryTestMixIn.test_queryNotNoIndex(self)

    test_queryNotNoIndex.todo = "?"


    def test_queryCaseInsensitive(self):
        return (
            BaseDirectoryServiceQueryTestMixIn.test_queryCaseInsensitive(self)
        )

    test_queryCaseInsensitive.todo = "?"


    def test_queryCaseInsensitiveNoIndex(self):
        return (
            BaseDirectoryServiceQueryTestMixIn
            .test_queryCaseInsensitiveNoIndex(self)
        )

    test_queryCaseInsensitiveNoIndex.todo = "?"


    def test_queryStartsWithNot(self):
        return BaseDirectoryServiceQueryTestMixIn.test_queryStartsWithNot(self)

    test_queryStartsWithNot.todo = "?"


    def test_queryStartsWithNotAny(self):
        return (
            BaseDirectoryServiceQueryTestMixIn
            .test_queryStartsWithNotAny(self)
        )

    test_queryStartsWithNotAny.todo = "?"


    def test_queryStartsWithNotNoIndex(self):
        return (
            BaseDirectoryServiceQueryTestMixIn
            .test_queryStartsWithNotNoIndex(self)
        )

    test_queryStartsWithNotNoIndex.todo = "?"


    def test_queryStartsWithCaseInsensitive(self):
        return (
            BaseDirectoryServiceQueryTestMixIn
            .test_queryStartsWithCaseInsensitive(self)
        )

    test_queryStartsWithCaseInsensitive.todo = "?"


    def test_queryStartsWithCaseInsensitiveNoIndex(self):
        return (
            BaseDirectoryServiceQueryTestMixIn
            .test_queryStartsWithCaseInsensitiveNoIndex(self)
        )

    test_queryStartsWithCaseInsensitiveNoIndex.todo = "?"


    def test_queryContainsNot(self):
        return BaseDirectoryServiceQueryTestMixIn.test_queryContainsNot(self)

    test_queryContainsNot.todo = "?"


    def test_queryContainsNotNoIndex(self):
        return (
            BaseDirectoryServiceQueryTestMixIn
            .test_queryContainsNotNoIndex(self)
        )

    test_queryContainsNotNoIndex.todo = "?"


    def test_queryContainsCaseInsensitive(self):
        return (
            BaseDirectoryServiceQueryTestMixIn
            .test_queryContainsCaseInsensitive(self)
        )

    test_queryContainsCaseInsensitive.todo = "?"


    def test_queryContainsCaseInsensitiveNoIndex(self):
        return (
            BaseDirectoryServiceQueryTestMixIn
            .test_queryContainsCaseInsensitiveNoIndex(self)
        )

    test_queryContainsCaseInsensitiveNoIndex.todo = "?"



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
            u"uid=wsanchez,cn=user,{0}".format(self.baseDN),
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
            u"uid=wsanchez,cn=user,{0}".format(self.baseDN),
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
            _debug=True,
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
    DirectoryServiceRealmTestMixIn,
    DirectoryServiceQueryTestMixIn,
    DirectoryServiceConnectionTestMixIn,
    test_directory.BaseDirectoryServiceTest,
    unittest.TestCase,
):
    serviceClass = DirectoryService
    directoryRecordClass = DirectoryRecord


    def test_repr(self):
        service = self.service()

        self.assertEquals(repr(service), u"<TestService u'ldap://localhost/'>")



def mockDirectoryDataFromXMLService(service):
    dc0 = u"org"
    dc1 = u"calendarserver"

    data = {
        u"dc={dc0}".format(dc0=dc0): dict(dc=dc0),
        u"dc={dc1},dc={dc0}".format(dc1=dc1, dc0=dc0): dict(dc=[dc1, dc0]),
    }

    def toUnicode(obj):
        if isinstance(obj, (NamedConstant, ValueConstant)):
            return obj.name

        if isinstance(obj, (tuple, list)):
            return [unicode(x) for x in obj]

        return unicode(obj)

    def tuplify(record, fieldName):
        fieldValue = record.fields[fieldName]

        if fieldName is BaseFieldName.recordType:
            schema = DEFAULT_RECORDTYPE_SCHEMAS[fieldValue]

            return schema.attributes

        else:
            value = toUnicode(fieldValue)

            return (
                (name, value)
                for name in TEST_FIELDNAME_MAP.get(
                    fieldName, (u"__" + fieldName.name,)
                )
            )

    for records in service.index[service.fieldName.uid].itervalues():
        for record in records:
            dn = u"uid={uid},cn={cn},dc={dc1},dc={dc0}".format(
                uid=record.shortNames[0],
                cn=record.recordType.name,
                dc1=dc1, dc0=dc0
            )

            recordData = dict(chain(*(
                list(tuplify(record, fieldName))
                for fieldName in service.fieldName.iterconstants()
                if fieldName in record.fields
            )))

            data[dn] = recordData

    return data



#
# mockldap patches
#

class WildcardExpression(object):
    first = None
    middle = []
    last = None


def mockldap_parse_wildcard_expression(self):
    match = self.TEST_RE.match(self.content)

    if match is None:
        raise ldap.FILTER_ERROR(
            u"Failed to parse filter item %r at pos %d"
            % (self.content, self.start)
        )

    self.attr, self.op, valueExpression = match.groups()

    if self.op != "=":
        raise MockLDAPUnsupportedOp(
            u"Operation %r is not supported" % (self.op,)
        )

    if (u"*" not in valueExpression):
        raise NotImplementedError(u"I only deal with wild cards")

    values = []

    for value in valueExpression.split(u"*"):
        # Resolve all escaped characters
        values.append(self.UNESCAPE_RE.sub(
            lambda m: chr(int(m.group(1), 16)),
            value
        ))

    exp = WildcardExpression()

    if not valueExpression.startswith(u"*"):
        exp.first = values.pop(0)

    if not valueExpression.endswith(u"*"):
        exp.last = values.pop(-1)

    exp.middle = values

    self.value = exp


def mockldap_matches(self, dn, attrs):
    exp = self.value

    if not isinstance(exp, WildcardExpression):
        return False

    values = attrs.get(self.attr)

    if values is None:
        return False

    for value in values:
        start = 0
        end = len(value)

        if exp.first is not None:
            if not value.startswith(exp.first):
                continue
            start = len(exp.first)

        if exp.last is not None:
            if not value[start:].endswith(exp.last):
                continue
            end -= len(exp.last)

        if exp.middle:
            if not match_substrings_in_order(exp.middle, value, start, end):
                continue

        return True

    return False


def match_substrings_in_order(substrings, value, start, end):
    for substring in substrings:
        if not substring:
            continue

        i = value.find(substring, start, end)
        if i == -1:
            # Match fails for this substring
            return False

        # Move start up past this substring substring before testing the next
        start = i + len(substring)

    # No mismatches
    return True
