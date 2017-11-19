import sys, os
import re
from subprocess import Popen, PIPE, STDOUT
import thread, threading

class Wrapper(threading.Thread):
    linphone = None
    linphone_cmd = ["linphonec"]

    sip_username = None
    sip_hostname = None
    sip_password = None

    def __init__(self):
        threading.Thread.__init__(self)
    
    def IsRunning(self):
        try:
            return True if self.linphone.poll() is None else False
        except AttributeError:
            return False

    def StartLinphone(self):
        if not self.IsRunning():
            self.linphone = Popen(self.linphone_cmd, stdin=PIPE, stdout=PIPE, stderr=STDOUT)

    def StopLinphone(self):
        if self.IsRunning():
            self.linphone.terminate()

    def RegisterCallbacks(self, OnIncomingCall, OnOutgoingCall, OnRemoteHungupCall, OnSelfHungupCall, OnRegisterFail, OnRegisterSuccess):
        self.OnIncomingCall = OnIncomingCall
        self.OnOutgoingCall = OnOutgoingCall
        self.OnRemoteHungupCall = OnRemoteHungupCall
        self.OnSelfHungupCall = OnSelfHungupCall
        self.OnRegisterFail = OnRegisterFail
        self.OnRegisterSuccess = OnRegisterSuccess

    def run(self):
        while self.IsRunning():
            line = self.linphone.stdout.readline().rstrip()
            print "[LINPHONE] %s" % line
            if line.find("is contacting you") != -1:
                self.OnIncomingCall()
            if re.search("Registration on .* successful", line):
                self.OnRegisterSuccess()
            if re.search("Registration on .* fail", line) or re.search("Network is unreachable", line):
                print("FAIL FAIL FAIL")
                self.OnRegisterFail()
            if line.find("Network is unreachable") != -1:
                print("FAIL FAIL FAIL")
                self.OnRegisterFail()
            if line.find("Call terminated") != -1:
                self.OnRemoteHungupCall()
            if line.find("Call ended") != -1:
                self.OnSelfHungupCall()

    def SendCmd(self, cmd):
        if self.IsRunning():
            self.linphone.stdin.write("".join([cmd, '\n']))

    def SipRegister(self, username, hostname, password):
        if self.IsRunning():
            self.sip_username = username
            self.sip_hostname = hostname
            self.sip_password = password
            self.SendCmd("register sip:%s@%s %s %s" % (username, hostname, hostname, password))
            #self.SendCmd("codec disable 4")
            #self.SendCmd("codec disable 5")

    def SipCall(self, number):
        if self.IsRunning():
            self.SendCmd("call sip:%s@%s" % (number, self.sip_hostname))

    def SipHangup(self):
        if self.IsRunning():
            self.SendCmd("terminate")

    def SipAnswer(self):
        if self.IsRunning():
            self.SendCmd("answer")

