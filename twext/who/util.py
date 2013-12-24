# -*- test-case-name: twext.who.test.test_util -*-
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

"""
Directory service module utilities.
"""

__all__ = [
    "ConstantsContainer",
    "uniqueResult",
    "describe",
    "iterFlags",
]

from twisted.python.constants import (
    Names, Values, Flags, NamedConstant, ValueConstant, FlagConstant,
)

from .idirectory import DirectoryServiceError



class ConstantsContainer(object):
    """
    A container for constants.
    """
    def __init__(self, sources):
        self._constants = {}
        self._methods = {}

        for source in sources:
            if issubclass(type(source), type):
                if issubclass(source, CONTAINER_CLASSES):
                    self._addConstants(source.iterconstants())
                    self._addMethods(source)
                else:
                    raise TypeError(
                        "Unknown constants type: {0}".format(source)
                    )

            elif isinstance(source, CONSTANT_CLASSES):
                self._addConstants((source,))

            else:
                self._addConstants(source)


    def _addConstants(self, constants):
        for constant in constants:
            if hasattr(self, "_constantsClass"):
                if constant.__class__ != self._constantsClass:
                    raise TypeError(
                        "Can't mix constants classes in the "
                        "same constants container: {0} != {1}"
                        .format(constant.__class__, self._constantsClass)
                    )
            else:
                self._constantsClass = constant.__class__

            if constant.name in self._constants:
                raise ValueError("Name conflict: {0}".format(constant.name))

            self._constants[constant.name] = constant


    def _addMethods(self, container):
        for name, value in container.__dict__.iteritems():
            if type(value) is staticmethod:
                if name in self._constants or name in self._methods:
                    raise ValueError("Name conflict: {0}".format(name))

                self._methods[name] = getattr(container, name)


    def __getattr__(self, name):
        attr = self._constants.get(name, None)
        if attr is not None:
            return attr

        attr = self._methods.get(name, None)
        if attr is not None:
            return attr

        raise AttributeError(name)


    def iterconstants(self):
        return self._constants.itervalues()


    def lookupByName(self, name):
        try:
            return self._constants[name]
        except KeyError:
            raise ValueError(name)



def uniqueResult(values):
    result = None
    for value in values:
        if result is None:
            result = value
        else:
            raise DirectoryServiceError(
                "Multiple values found where one expected."
            )
    return result



def describe(constant):
    if isinstance(constant, FlagConstant):
        parts = []
        for flag in iterFlags(constant):
            parts.append(getattr(flag, "description", flag.name))
        return "|".join(parts)
    else:
        return getattr(constant, "description", constant.name)



def iterFlags(flags):
    if hasattr(flags, "__iter__"):
        return flags
    else:
        # Work around http://twistedmatrix.com/trac/ticket/6302
        # FIXME: This depends on a private attribute (flags._container)
        return (flags._container.lookupByName(name) for name in flags.names)



CONTAINER_CLASSES = (ConstantsContainer, Names, Values, Flags)
CONSTANT_CLASSES = (NamedConstant, ValueConstant, FlagConstant)
