import os
import zmq
from optparse import OptionParser

parser = OptionParser()

parser.add_option("-C", "--cmdout", dest="cmdoutput", default="tcp://127.0.0.1:5570",
                  help="URI to submit commands to")

parser.add_option("-c", "--cmdin", dest="cmdinput", default="tcp://127.0.0.1:5571",
                  help="URI to fetch commands from")

parser.add_option("-r", "--responsein", dest="responseinput", 
                  default="tcp://127.0.0.1:5573",
                  help="URI to fetch responses from")

parser.add_option("-R", "--responseout", dest="responseoutput",
                  default="tcp://127.0.0.1:5572",
                  help="URI to submit responses to")

parser.add_option("-n", "--name", dest="actor", default="actor",
                  help="use this as actor name")

parser.add_option("-s", "--subactor", dest="subactors", default=[],
                  action="append", help="invoke subactor(s) before completion")

parser.add_option("-v", "--verbose", action="store_true", dest="verbose",
                  help="print actions as they happen")

(options, args) = parser.parse_args()


me = options.actor

context = zmq.Context()

cmdin = context.socket(zmq.SUB)
cmdin.connect(options.cmdinput)
cmdin.setsockopt(zmq.SUBSCRIBE, me)

cmdout = context.socket(zmq.DEALER)
cmdout.setsockopt(zmq.IDENTITY, me)
cmdout.connect(options.cmdoutput)

responsein = context.socket(zmq.SUB)
responsein.connect(options.responseinput)
responsein.setsockopt(zmq.SUBSCRIBE, me)

responseout = context.socket(zmq.DEALER)
responseout.setsockopt(zmq.IDENTITY, me)
responseout.connect(options.responseoutput)

i = 0
while True:
   i += 1

   msg = cmdin.recv_multipart()
   # asser(msg[0] == me)
   sender = msg[1]
   payload = str(msg[2:])
   if options.verbose:
      print "--- %s fetched: sender=%s payload=%s " % (me, sender, payload)

   subresult = ""
   if i % 2 == 0:
      # every other command, pass a subjob to other actors
      for actor in options.subactors:
         if options.verbose:
            print "---%s invoke %s" % (me, actor)
         cmdout.send_multipart([actor, "a job for " + actor])

      # collect responses
      for actor in options.subactors:
          reply = responsein.recv_multipart()
          if options.verbose:
             print "---%s got reply from %s" % (me, reply[1])
          subresult += " " + reply[2]

      if options.subactors and options.verbose:
         print "---%s all responses in: %s" % (me, subresult)

   result = payload + " processed by " + me + "  " + subresult
   responseout.send_multipart([sender, result])
