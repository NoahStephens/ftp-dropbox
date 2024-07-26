from twisted.python import usage

DROPBOX_FOLDER = "scandocs"

FTP_PORT = 21

class FTPOptions(usage.Options):
    optParameters = [
        ["host", "h", "localhost"],
        ["port", "p", FTP_PORT],
        ["username", "u", "anonymous"],
        ["password", None, "twisted@"],
        ["passive", None, 0],
        ["debug", "d", 1],
    ]
