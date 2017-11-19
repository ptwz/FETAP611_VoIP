from __future__ import print_function
import time
import subprocess
import linphone.Wrapper
import thread
import select

class Phone(object):
    NSA = 3
    NSP = 4
    OH = 2
    DIAL_TIMEOUT = 10

    RING_VOLUME = 23
    PHONE_VOLUME = 8

    def __init__(self, user, host, passwd):
        self.user = user
        self.host = host
        self.passwd = passwd
        self.state = self.NO_LINE
        self.timeout = time.time()
        self.count = 0

        self.get_input = self.get_input_native
        self.dial_number = ""
        self.ziffer = 0
        self.backend = linphone.Wrapper.Wrapper()
        self.backend.StartLinphone()

        self.backend.start()
        self.player = None
        self.alive = True
        self.backend.RegisterCallbacks(
            OnIncomingCall = self.onIncoming,
            OnOutgoingCall = self.stub,
            OnSelfHungupCall = self.stub,
            OnRemoteHungupCall = self.onRemoteHUP,
            OnRegisterFail = self.onRegisterFail,
            OnRegisterSuccess = self.onRegisterSuccess)

        self.fds={}
        thread.start_new_thread(self.gpio_edge_thread, ())
        thread.start_new_thread(self.gpio_ring_thread, ())
        self.oh = False
        self.nsa = False
        self.nsp = False
        self.ring = False

    def run(self):
        self.count += 1
        print ("oh={} nsa={} nsp={}".format(self.oh, self.nsa, self.nsp))
        self.state(self.oh, self.nsa, self.nsp)
        self.old_nsa = self.nsa
        self.old_nsp = self.nsp
        self.old_oh = self.oh

    def shutdown(self):
        self.alive = False

    ########## INTERFACES #####################
    def get_input_native(self, num):
        fn = "/sys/class/gpio/gpio{}/value".format(num)
        self.fds[fn] = open(fn, "r+")
        l = self.fds[fn].readline().strip()
        return int(l)

    def gpio_edge_thread(self):
        to_watch = [self.NSA, self.OH, self.NSP]
        watch_names = [ "/sys/class/gpio/gpio{}/value".format(num) for num in to_watch ]

        while self.alive:
            states = [ self.get_input(x) for x in to_watch ]
            for x,n in zip(states, to_watch):
                if n == self.NSA:
                        self.nsa = not bool(x)
                elif n == self.NSP:
                        self.nsp = bool(x)
                elif n == self.OH:
                        self.oh = not bool(x)
            # Setup edge detect
            for num,state in zip(to_watch,states):
                fn = "/sys/class/gpio/gpio{}/edge".format(num)
		print(fn)
                with open(fn,"w") as f:
                    if state:
                        f.write("falling\n")
                    else:
                        f.write("rising\n")
            # Now wait for edges
            fds = [ self.fds[n] for n in watch_names ]
            poll = select.epoll()
            [poll.register(x, (select.EPOLLPRI)) for x in fds]
            r = poll.poll(2000)
            print("poll end:{}".format(r))
            if len(r)>0:
                # Wake up main program upon change
                self.run()

    def gpio_ring_thread(self):
        while self.alive:
            time.sleep(.5)
            if self.ring:
                self.enable_bell()
                with open('/sys/class/gpio/gpio18/value','w') as clk:

                        for x in range(100):
                            time.sleep(1./(30.*2.))
                            if (x & 1):
                                clk.write("1")
                            else:
                                clk.write("0")
                            clk.flush()
                self.disable_bell()
        
    def set_volume(self, level):
        subprocess.call(["amixer", "sset", "Headphone", "{}".format(level)])

    def start_play(self, filename):
        self.set_volume(3)
        self.player = subprocess.Popen(["play", filename])

    def end_play(self):
        if self.player is not None:
            self.player.terminate()
        self.player = None

    def enable_bell(self):
        fn = "/sys/class/gpio/gpio17/value"
        with open(fn, "w") as f:
            f.write("1")

    def disable_bell(self):
        fn = "/sys/class/gpio/gpio17/value"
        with open(fn, "w") as f:
            f.write("0")

    def stub(self):
        '''
        Stub to ignore events we don't care about (yet)
        '''
        pass

    def onIncoming(self):
        self.set_volume(self.RING_VOLUME)
        if self.state in (self.FREI, self.ZIFFER, self.IDLE):
            self.state = self.RUF
        else:
            print("Why did I get here ?! Got ring while in state {}".format(self.state))

    def onRemoteHUP(self):
        if self.state in (self.GESPR, self.RUF):
            self.state = self.IDLE
        else:
            print("Why did I get here ?! Got remote hangup while in state {}".format(self.state))

    def onRegisterFail(self):
        self.state = self.NO_LINE
        self.end_play()

    def onRegisterSuccess(self):
        if self.state not in (self.GESPR, self.FREI, self.ZIFFER):
            self.state = self.IDLE

    ########## STATES #########################
    def NO_LINE(self, oh, nsa, nsp):
        print("NO_LINE", end="\r")
        if self.timeout < time.time():
            self.backend.SipRegister(self.user, self.host, self.passwd)
            self.timeout = time.time() + 30

    def IDLE(self, oh, nsa, nsp):
        print("IDLE", end="\r")
        self.disable_bell()
        self.dial_number = ""
        self.ziffer = 0
        self.ring = False
        self.end_play()
        if oh:
            self.state = self.FREI
            self.set_volume(self.PHONE_VOLUME)
            self.timeout = time.time() + self.DIAL_TIMEOUT
            self.start_play("440Hz.wav")

    def RUF(self, oh, nsa, nsp):
        print("RUF", end="\r")
        self.ring = True
        if oh:
            self.ring = False
            self.disable_bell()
            self.set_volume(self.PHONE_VOLUME)
            self.backend.SipAnswer()
            self.state = self.GESPR

    def FREI(self, oh, nsa, nsp):
        print("FREI {}".format(self.dial_number), end="\r")
        if not oh:
            self.state = self.IDLE
            return

        if self.ziffer != 0:
            self.dial_number += str(self.ziffer % 10)
            self.ziffer = 0

        if nsa:
            self.state = self.ZIFFER
            self.ziffer = 0
            self.timeout = time.time() + self.DIAL_TIMEOUT
            return
        if self.timeout <= time.time():
            if len(self.dial_number)==0:
                self.state = self.IDLE
            else:
                self.state = self.WAHL
                self.end_play()
                self.backend.SipCall(self.dial_number)

    def ZIFFER(self, oh, nsa, nsp):
        if not nsa:
            self.state = self.FREI
        if self.old_nsp != nsp and nsp:
            self.ziffer += 1
        print("ZIFFER {}".format(self.ziffer), end="\r")
    
    def WAHL(self, oh, nsa, nsp):
        print("WAHL", end="\r")
        if not oh:
            self.state = self.IDLE
            return
        if True:
            self.state = self.GESPR

    def GESPR(self, oh, nsa, nsp):
        print("GESPR", end="\r")
        if not oh:
            self.backend.SipHangup()
            self.state = self.IDLE

