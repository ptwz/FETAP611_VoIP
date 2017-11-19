import time

en = open('/sys/class/gpio/gpio17/value','w')

clk = open('/sys/class/gpio/gpio18/value','w')

en.write("1");
en.flush()
for x in range(100):
	time.sleep(1./(30.*2.))
	if (x & 1):
		clk.write("1")
	else:
		clk.write("0")
	clk.flush()
en.write("0");
en.flush()
