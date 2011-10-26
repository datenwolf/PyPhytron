import serial, string, exceptions

class ReceiveTimeout(exceptions.Exception):
	pass

class ReceiveChecksumError(exceptions.Exception):
	def __init__(self, expected, received):
		self.expected = expected
		self.received = received
		self.message = "Checksum Error: expected %x, got %x" % (expected, received)

class Axis:
	def __init__(self, ipcomm, address):
		self.ipcomm = ipcomm
		self.address = address

	def goToAbs(self, position):
		pass
	
	def goToRelative(self, offset):
		pass
	
	def goFree(self, direction):
		pass

	def setAccelerationCurrent(self, current):
		pass
	def getAccelerationCurrent(self, current):
		pass
	
	def setPosition(self, position):
		pass
	def getPosition(self, position):
		pass

def checksum(data):
	chksm = 0
	for d in data:
		chksm = chksm ^ ord(d)
	return chksm

class IPCOMM:
	def __init__(self, url, baudrate = 38400):
		self.conn = serial.serial_for_url(url)
		self.conn.baudrate = baudrate
		self.conn.parity = serial.PARITY_NONE
		self.conn.rtscts = False
		self.conn.dsrdtr = False
		self.conn.xonxoff = False
		self.conn.timeout = 0.1

	def enumerate(self, names):
		for n in range(0x10):
			try:
				address = self.execute(n, 'IS?')[0]
				assert address == n
			except ReceiveTimeout:
				continue
			print("Axis %d found" % n)

	def send(self, data):
		self.conn.write('\x02' + data + ':' + ('%02X' % checksum(data + ':')) + '\x03')
		self.conn.flush()
		return self
	
	def recv(self):
		buf = ''

		c = None
		while c != '\x02':
			c = self.conn.read(1)
			if not c:
				raise ReceiveTimeout

		c = None
		while c != '\x03':
			c = self.conn.read(1)
			if not c:
				raise ReceiveTimeout
			buf += c

		status, data, chksm = buf[:-1].split(':')
		expected_chksm = checksum(status + ':' + data + ':')
		chksm = string.atoi(chksm, 0x10)
		if expected_chksm != chksm:
			raise ReceiveChecksumError(expected_chksm, chksm)

		return string.atoi(status[0], 0x10), string.atoi(status[1:], 0x10), data

	def broadcast(self, cmd):
		self.conn.flushInput()
		self.send( '@' + cmd )
	
	def execute(self, address, cmd):
		self.conn.flushInput()
		self.send( ('%X' % address) + cmd )

		recv_data = None
		while not recv_data:
			try:
				recv_data = self.recv()
			except ReceiveChecksumError:
				self.send( ('%X' % address) + 'R')
		# self.parseStatus(recv_status)
		return recv_data
	
	def goToAbs(self, positions):
		pass
	
	def goToRelative(self, offset):
		pass
	
	def goFree(self, direction):
		pass

	def setAccelerationCurrent(self, currents):
		pass
	
	def setPosition(self, positions):
		pass
	
