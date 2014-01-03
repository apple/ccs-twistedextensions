##
# Copyright (c) 2013 Apple Inc. All rights reserved.
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

cache()

from twisted.cred.portal import Portal
from twisted.web.resource import IResource
from twisted.web.guard import (
    HTTPAuthSessionWrapper,
    BasicCredentialFactory,
    # DigestCredentialFactory,
)
from twisted.web.static import Data

# from twext.who.test.test_xml import xmlService as DirectoryService
from twext.who.opendirectory import DirectoryService
from twext.who.opendirectory import NoQOPDigestCredentialFactory as DigestCredentialFactory
from twext.who.checker import UsernamePasswordCredentialChecker
from twext.who.checker import HTTPDigestCredentialChecker



class Realm(object):
    def requestAvatar(self, avatarId, mind, *interfaces):
        resource = Data(
            "Hello, {0!r}!".format(avatarId),
            "text/plain"
        )

        return IResource, resource, lambda: None



# directory = DirectoryService("/tmp/auth.xml")
directory = DirectoryService()

checkers = [
    HTTPDigestCredentialChecker(directory),
    # UsernamePasswordCredentialChecker(directory),
]

realm = Realm()

portal = Portal(realm, checkers)

factories = [
    DigestCredentialFactory("md5", "Digest Realm"),
    # BasicCredentialFactory("Basic Realm"),
]

resource = HTTPAuthSessionWrapper(portal, factories)
