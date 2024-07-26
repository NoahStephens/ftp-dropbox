from __future__ import print_function
import argparse
import contextlib
import datetime
import os
import six
import time
import unicodedata

import sys
import dropbox
import threading
from io import BytesIO
from twisted.cred.checkers import AllowAnonymousAccess, FilePasswordDB
from twisted.cred.portal import Portal
from twisted.internet import reactor
from twisted.protocols.ftp import FTPFactory, FTPRealm
from twisted.internet.protocol import ClientCreator, Protocol
from twisted.protocols.ftp import FTPClient, FTPFileListProtocol


from secrets import DROPBOX_TOKEN
from config import DROPBOX_FOLDER
from config import FTPOptions
from config import FTP_PORT




class DropboxService:
    def __init__(self, dropbox_folder_name : str) -> None:
        self._token = DROPBOX_TOKEN
        self.dropbox_client = dropbox.Dropbox(DROPBOX_TOKEN)


    @classmethod
    @contextlib.contextmanager
    def stopwatch(message):
        """Context manager to print how long a block of code took."""
        t0 = time.time()
        try:
            yield
        finally:
            t1 = time.time()
            print('Total elapsed time for %s: %.3f' % (message, t1 - t0))

    def upload(self, fullname, folder, name, overwrite=False):
        """Upload a file.

        Return the request response, or None in case of error.
        """
        path = '/%s/%s' % (folder, name)
        while '//' in path:
            path = path.replace('//', '/')
        mode = (dropbox.files.WriteMode.overwrite
                if overwrite
                else dropbox.files.WriteMode.add)
        mtime = os.path.getmtime(fullname)
        with open(fullname, 'rb') as f:
            data = f.read()

        with self.stopwatch('upload %d bytes' % len(data)):
            try:
                res = self.dropbox_client.files_upload(
                    data, path, mode,
                    client_modified=datetime.datetime(*time.gmtime(mtime)[:6]),
                    mute=True)
            except dropbox.exceptions.ApiError as err:
                print('*** API error', err)
                return None
        print('uploaded as', res.name.encode('utf8'))
        return res





class FTPServerService(threading.Thread):
    def __init__(self):
        threading.Thread.__init__(self)
        self._portal = Portal(FTPRealm("./"), [AllowAnonymousAccess()])
        self._ftp_factory = FTPFactory(self._portal)
        
        reactor.listenTCP(FTP_PORT, self._ftp_factory)
        print("started ftp server")

    def run(self):
        reactor.run()

class FTPBufferingProtocol(Protocol):
    """Simple utility class that holds all data written to it in a buffer."""

    def __init__(self):
        self.buffer = BytesIO()

    def dataReceived(self, data):
        self.buffer.write(data)


class FTPClientService(threading.Thread):
    def __init__(self) -> None:
        threading.Thread.__init__(self)
        self.upload_dropbox = lambda x : None

    def register_dropbox_file_handler(self, handler):
        self.upload_dropbox = handler
  
    def run(self):

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

        # run method
        config = FTPOptions()
        config.parseOptions()
        config.opts["port"] = int(config.opts["port"])
        config.opts["passive"] = int(config.opts["passive"])
        config.opts["debug"] = int(config.opts["debug"])

        # create client
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


if __name__ == "__main__":
    # dropbox_service = DropboxService(DROPBOX_FOLDER)
    
    # start ftp server
    ftp_server_service = FTPServerService()

    ftp_client_listener = FTPClientService()
    # ftp_client_listener.register_dropbox_file_handler(dropbox_service.upload)

    # TODO: handle shutdown commands

    try:
        while 1: continue

    except KeyboardInterrupt:
        sys.exit()

    finally:
        print("Bye")