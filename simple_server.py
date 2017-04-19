from gc import disable
from sys import argv
from time import sleep

from twisted.protocols.basic import LineOnlyReceiver
from twisted.internet.defer import Deferred
from twisted.internet.task import react
from twisted.internet.protocol import Factory
from twisted.internet.endpoints import serverFromString


disable()


def compare(a, b):
    if len(a) != len(b):
        print("length mismatch")
        return False
    for i in range(len(a)):
        sleep(0.0)
        if a[i] != b[i]:
            return False
    return True


class PasswordCompare(LineOnlyReceiver):
    password = b"this is very secret you cannot guess"

    responses = [
        b"denied",
        b"ok",
    ]

    def lineReceived(self, line):
        self.sendLine(self.responses[compare(line, self.password)])



def main(reactor, listen_address):
    serverFromString(
        reactor, listen_address
    ).listen(
        Factory.forProtocol(PasswordCompare)
    )
    return Deferred()



react(main, argv[1:])
