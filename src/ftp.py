# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.

"""
An example FTP server with minimal user authentication.
"""

from twisted.cred.checkers import AllowAnonymousAccess, FilePasswordDB
from twisted.cred.portal import Portal
from twisted.internet import reactor
from twisted.protocols.ftp import FTPFactory, FTPRealm

#
# First, set up a portal (twisted.cred.portal.Portal). This will be used
# to authenticate user logins, including anonymous logins.
#
# Part of this will be to establish the "realm" of the server - the most
# important task in this case is to establish where anonymous users will
# have default access to. In a real world scenario this would typically
# point to something like '/pub' but for this example it is pointed at the
# current working directory.
#
# The other important part of the portal setup is to point it to a list of
# credential checkers. In this case, the first of these is used to grant
# access to anonymous users and is relatively simple; the second is a very
# primitive password checker.  This example uses a plain text password file
# that has one username:password pair per line. This checker *does* provide
# a hashing interface, and one would normally want to use it instead of
# plain text storage for anything remotely resembling a 'live' network. In
# this case, the file "pass.dat" is used, and stored in the same directory
# as the server. BAD.
#
# Create a pass.dat file which looks like this:
#
# =====================
#   jeff:bozo
#   grimmtooth:bozo2
# =====================
#
p = Portal(FTPRealm("./"), [AllowAnonymousAccess(), FilePasswordDB("pass.dat")])

#
# Once the portal is set up, start up the FTPFactory and pass the portal to
# it on startup. FTPFactory will start up a twisted.protocols.ftp.FTP()
# handler for each incoming OPEN request. Business as usual in Twisted land.
#
f = FTPFactory(p)

#
# You know this part. Point the reactor to port 21 coupled with the above factory,
# and start the event loop.
#
reactor.listenTCP(21, f)
reactor.run()

# Copyright (c) Twisted Matrix Laboratories.
# See LICENSE for details.


"""
An example of using the FTP client
"""
# Standard library imports
from io import BytesIO

from twisted.internet import reactor
from twisted.internet.protocol import ClientCreator, Protocol

# Twisted imports
from twisted.protocols.ftp import FTPClient, FTPFileListProtocol
from twisted.python import usage


class FTPBufferingProtocol(Protocol):
    """Simple utility class that holds all data written to it in a buffer."""

    def __init__(self):
        self.buffer = BytesIO()

    def dataReceived(self, data):
        self.buffer.write(data)


# Define some callbacks


def success(response):
    print("Success!  Got response:")
    print("---")
    if response is None:
        print(None)
    else:
        print("\n".join(response))
    print("---")


def fail(error):
    print("Failed.  Error was:")
    print(error)


def showFiles(result, fileListProtocol):
    print("Processed file listing:")
    for file in fileListProtocol.files:
        print(
            "    {}: {} bytes, {}".format(file["filename"], file["size"], file["date"])
        )
    print(f"Total: {len(fileListProtocol.files)} files")


def showBuffer(result, bufferProtocol):
    print("Got data:")
    print(bufferProtocol.buffer.getvalue())


class Options(usage.Options):
    optParameters = [
        ["host", "h", "localhost"],
        ["port", "p", 21],
        ["username", "u", "anonymous"],
        ["password", None, "twisted@"],
        ["passive", None, 0],
        ["debug", "d", 1],
    ]


def run():
    # Get config
    config = Options()
    config.parseOptions()
    config.opts["port"] = int(config.opts["port"])
    config.opts["passive"] = int(config.opts["passive"])
    config.opts["debug"] = int(config.opts["debug"])

    # Create the client
    FTPClient.debug = config.opts["debug"]
    creator = ClientCreator(
        reactor,
        FTPClient,
        config.opts["username"],
        config.opts["password"],
        passive=config.opts["passive"],
    )
    creator.connectTCP(config.opts["host"], config.opts["port"]).addCallback(
        connectionMade
    ).addErrback(connectionFailed)
    reactor.run()


def connectionFailed(f):
    print("Connection Failed:", f)
    reactor.stop()


def connectionMade(ftpClient):
    # Get the current working directory
    ftpClient.pwd().addCallbacks(success, fail)

    # Get a detailed listing of the current directory
    fileList = FTPFileListProtocol()
    d = ftpClient.list(".", fileList)
    d.addCallbacks(showFiles, fail, callbackArgs=(fileList,))

    # Change to the parent directory
    ftpClient.cdup().addCallbacks(success, fail)

    # Create a buffer
    proto = FTPBufferingProtocol()

    # Get short listing of current directory, and quit when done
    d = ftpClient.nlst(".", proto)
    d.addCallbacks(showBuffer, fail, callbackArgs=(proto,))
    d.addCallback(lambda result: reactor.stop())


# this only runs if the module was *not* imported
if __name__ == "__main__":
    run()
