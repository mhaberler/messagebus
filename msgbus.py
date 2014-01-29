import zmq
import sys
import threading
import time

from optparse import OptionParser

parser = OptionParser()
parser.add_option("-v","--verbose", action="store_true", dest="verbose",
                  help="print actions as they happen")

(options, args) = parser.parse_args()


# ROUTER/XPUB pairs

# the command bus:
cmdinput = 'tcp://127.0.0.1:5570'
cmdoutput   = 'tcp://127.0.0.1:5571'

# the response bus:
responseinput = 'tcp://127.0.0.1:5572'
responseoutput = 'tcp://127.0.0.1:5573'


class MsgbusTask(threading.Thread):
    def __init__(self):
        threading.Thread.__init__ (self)
        self.kill_received = False

    def run(self):
        print('Msbus started')

        cmdsubs = dict()
        responsesubs = dict()
        context = zmq.Context()

        cmdin = context.socket(zmq.ROUTER)
        cmdin.bind(cmdinput)

        cmdout = context.socket(zmq.XPUB)
        cmdout.set(zmq.XPUB_VERBOSE,1)
        cmdout.bind(cmdoutput)

        responsein = context.socket(zmq.ROUTER)
        responsein.bind(responseinput)

        responseout = context.socket(zmq.XPUB)
        responseout.set(zmq.XPUB_VERBOSE,1)
        responseout.bind(responseoutput)

        poll = zmq.Poller()
        poll.register(cmdin,      zmq.POLLIN)
        poll.register(cmdout,     zmq.POLLIN)
        poll.register(responsein, zmq.POLLIN)
        poll.register(responseout,zmq.POLLIN)


        while not self.kill_received:
            s = dict(poll.poll(1000))
            if cmdin in s:
                msg = cmdin.recv_multipart()
                if options.verbose: print "---cmdin recv: ", msg

                dest = msg[1]
                if dest in cmdsubs:
                    msg[0], msg[1] = msg[1], msg[0]
                    cmdout.send_multipart(msg)
                else:
                    responseout.send_multipart([msg[0], "no destination: " + dest])
                    if options.verbose: print "no command destination:", dest

            if responsein in s:
                msg = responsein.recv_multipart()
                if options.verbose: print "---responsein recv: ", msg

                dest = msg[1]
                if dest in responsesubs:
                    msg[0], msg[1] = msg[1], msg[0]
                    responseout.send_multipart(msg)
                else:
                    responseout.send_multipart([msg[0], "no destination: " + dest])
                    if options.verbose: print "no destination:", dest

            if cmdout in s:
                submsg = cmdout.recv()
                sub = ord(submsg[0])
                topic = submsg[1:]

                if sub:
                    cmdsubs[topic] = True
                    if options.verbose: print "--- commandout subscribe: %s" % (topic)
                else:
                    if options.verbose: print "--- commandout unsubscribe: %s" % (topic)
                    del cmdsubs[topic]

            if responseout in s:
                submsg = responseout.recv()
                sub = ord(submsg[0])
                topic = submsg[1:]

                if sub:
                    responsesubs[topic] = True
                    if options.verbose: print "--- responseout subscribe: %s" % (topic)
                else:
                    if options.verbose: print "--- responseout unsubscribe: %s" % (topic)
                    del responsesubs[topic]

        context.destroy(linger=0)
        print('Msbus exited')

def main():
    try:
        bus = MsgbusTask()
        bus.start()
        while True: time.sleep(100)
    except (KeyboardInterrupt, SystemExit):
        bus.kill_received = True
        bus.join()

if __name__ == "__main__":
    main()



