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

#
# Run:
#     twistd -n web --path twext/who/test
#
# And open this URL:
#     http://localhost:8080/auth_resource.rpy
#

cache()

from tempfile import NamedTemporaryFile
from textwrap import dedent

from twisted.cred.portal import Portal
from twisted.web.resource import IResource
from twisted.web.guard import (
    HTTPAuthSessionWrapper,
    BasicCredentialFactory,
    DigestCredentialFactory,
)
from twisted.web.static import Data

from twext.who.directory import DirectoryRecord
from twext.who.test.test_xml import xmlService as XMLDirectoryService
# from twext.who.opendirectory import (
#     DirectoryService as OpenDirectoryDirectoryService,
#     NoQOPDigestCredentialFactory,
# )
from twext.who.checker import UsernamePasswordCredentialChecker
from twext.who.checker import HTTPDigestCredentialChecker



class Realm(object):
    @staticmethod
    def hello(avatarId):
        message = ["Hello, {0!r}!".format(avatarId)]

        if isinstance(avatarId, DirectoryRecord):
            message.append(avatarId.description().encode("utf-8"))

        return "\n\n".join(message)


    def requestAvatar(self, avatarId, mind, *interfaces):
        if IResource in interfaces:
            interface = IResource
            resource = Data(self.hello(avatarId), "text/plain")
        else:
            interface = None
            resource = None

        return interface, resource, lambda: None



realm = Realm()

rootResource = Data(
    data=dedent(
        """
        <html>
         <head>
          <title>Authentication tests</title>
         </head>
         <body>
          <ul>
           <li>XML Directory Service</li>
           <ul>
            <li><a href="auth_resource.rpy/XMLBasic" >Basic </a></li>
            <li><a href="auth_resource.rpy/XMLDigest">Digest</a></li>
           </ul>
          </ul>
         </body>
        </html>
        """[1:]
    ),
    type="text/html",
)

xmlFileBasic = NamedTemporaryFile(delete=True)
rootResource.putChild(
    "XMLBasic",
    HTTPAuthSessionWrapper(
        Portal(
            realm,
            [
                UsernamePasswordCredentialChecker(
                    XMLDirectoryService(xmlFileBasic.name)
                )
            ]
        ),
        [BasicCredentialFactory("XML Basic Realm")]
    )
)

xmlFileDigest = NamedTemporaryFile(delete=True)
rootResource.putChild(
    "XMLDigest",
    HTTPAuthSessionWrapper(
        Portal(
            realm,
            [
                HTTPDigestCredentialChecker(
                    XMLDirectoryService(xmlFileDigest.name)
                )
            ]
        ),
        [DigestCredentialFactory("md5", "XML Digest Realm")]
    )
)

resource = rootResource
