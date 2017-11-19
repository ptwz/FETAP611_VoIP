import linphone.Wrapper
import time

w=linphone.Wrapper.Wrapper()

def ring():
	print "RING!!!"

def calling():
	print "Calling.."

def remote_hup():
	print "On Hook"

def local_hup():
	print "Local hook"

w.StartLinphone()
w.SipRegister("2304837e0", "sipgate.de",  "VPCMZE")
w.RegisterCallbacks(
	OnIncomingCall = ring,
	OnOutgoingCall = calling, 
	OnRemoteHungupCall = remote_hup,
	OnSelfHungupCall = local_hup
)

w.start()

time.sleep(5)

w.SipCall("017621181302")


