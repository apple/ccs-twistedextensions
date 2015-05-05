##
# Copyright (c) 2015 Apple Inc. All rights reserved.
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
Socket file implementation for MaxAccept
"""

__all__ = [
    "MaxAcceptSocketFileServer",
]


from twisted.application import service
from twisted.internet import endpoints
from twisted.internet.defer import succeed, inlineCallbacks

from twext.python.log import Logger

log = Logger()



# class MaxAcceptPortMixin(object):
#     """
#     Mixin for resetting maxAccepts.
#     """
#     def doRead(self):
#         self.numberAccepts = min(
#             self.factory.maxRequests - self.factory.outstandingRequests,
#             self.factory.maxAccepts
#         )
#         tcp.Port.doRead(self)



# class MaxAcceptTCPPort(MaxAcceptPortMixin, tcp.Port):
#     """
#     Use for non-inheriting tcp ports.
#     """







def _allConnectionsClosed(protocolFactory):
    """
    Check to see if protocolFactory implements allConnectionsClosed( ) and
    if so, call it.  Otherwise, return immediately.
    This allows graceful shutdown by waiting for all requests to be completed.

    @param protocolFactory: (usually) an HTTPFactory implementing
        allConnectionsClosed which returns a Deferred which fires when all
        connections are closed.

    @return: A Deferred firing None when all connections are closed, or
        immediately if the given factory does not track its connections (e.g.
        InheritingProtocolFactory)
    """
    if hasattr(protocolFactory, "allConnectionsClosed"):
        return protocolFactory.allConnectionsClosed()
    return succeed(None)




class MaxAcceptSocketFileServer(service.Service):
    """
    Socket File server

    @ivar myPort: When running, this is set to the L{IListeningPort} being
        managed by this service.
    """

    def __init__(self, protocolFactory, address, backlog=None):
        self.protocolFactory = protocolFactory
        self.protocolFactory.myServer = self
        self.address = address
        self.backlog = backlog
        self.myPort = None


    @inlineCallbacks
    def startService(self):
        from twisted.internet import reactor
        endpoint = endpoints.UNIXServerEndpoint(
            reactor, self.address, backlog=self.backlog,
        )
        self.myPort = yield endpoint.listen(self.protocolFactory)


    @inlineCallbacks
    def stopService(self):
        """
        Wait for outstanding requests to finish

        @return: a Deferred which fires when all outstanding requests are
            complete
        """
        if self.myPort is not None:
            yield self.myPort.stopListening()
        yield _allConnectionsClosed(self.protocolFactory)
