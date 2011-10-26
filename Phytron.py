import serial, string, exceptions

class ReceiveTimeout(exceptions.Exception):
	pass

class ReceiveChecksumError(exceptions.Exception):
	def __init__(self, expected, received):
		self.expected = expected
		self.received = received
		self.message = "Checksum Error: expected %x, got %x" % (expected, received)

class Axis:
	def __init__(self, ipcomm, ID):
		self.ipcomm = ipcomm
		self.ID = ID

	def execute(self, cmd):
		result = self.ipcomm.execute(self.ID, cmd)
		assert result['ID'] == self.ID
		del result['ID']
		return result
	
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

class Status:
	def __init__(self, bitvector):
		self.coldboot          = not not (bitvector & (1<<7))
		self.any_error         = not not (bitvector & (1<<6))
		self.rx_error          = not not (bitvector & (1<<5))
		self.SFI_error         = not not (bitvector & (1<<4))
		self.outputstage_error = not not (bitvector & (1<<3))
		self.initiator_m       = not not (bitvector & (1<<2))
		self.initiator_p       = not not (bitvector & (1<<1))
		self.running           = not not (bitvector & (1<<0))
	
	def __str__(self):
		status = list()
		if self.coldboot:
			status += ['Cold Boot']
		if self.any_error:
			status += ['Any Error']
		if self.rx_error:
			status += ['RX Error']
		if self.SFI_error:
			status += ['SFI Error']
		if self.outputstage_error:
			status += ['Output Stage Error']
		if self.initiator_m:
			status += ['Initiator -']
		if self.initiator_p:
			status += ['Initiator +']
		if self.running:
			status += ['Running']
		return '{'+ ('|'.join(status)) + '}'

class IPCOMM:
	def __init__(self, url, baudrate = 38400, axisnames = None):
		self.conn = serial.serial_for_url(url)
		self.conn.baudrate = baudrate
		self.conn.parity = serial.PARITY_NONE
		self.conn.rtscts = False
		self.conn.dsrdtr = False
		self.conn.xonxoff = False
		self.conn.timeout = 0.1
		self.axisByID = dict()
		self.axisByName = dict()
		self.enumerate(axisnames)

	def axis(self, nameOrID):
		if isinstance(nameOrID, str) and nameOrID.isalpha():
			return self.axisByName[nameOrID]
		return self.axisByID[int(nameOrID)]

	def enumerate(self, names=None):
		self.axisByID.clear()
		self.axisByName.clear()
		for ID in range(0x10):
			try:
				assert self.execute(ID, 'IS?')['ID'] == ID
				axis = Axis(self, ID)
				self.axisByID[ID] = axis

				if (isinstance(names, dict) and names.haskey(ID)) or (isinstance(names, list) and ID < len(names)):
					assert names[ID].isalpha()
					self.axisByName[str(names[ID])] = axis

			except ReceiveTimeout:
				continue

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

		return {'ID': string.atoi(status[0], 0x10), 
			'status': Status(string.atoi(status[1:], 0x10)), 
			'data': data}

	def broadcast(self, cmd):
		self.conn.flushInput()
		self.send( '@' + cmd )
	
	def execute(self, ID, cmd):
		self.conn.flushInput()
		self.send( ('%X' % ID) + cmd )

		recv_data = None
		while not recv_data:
			try:
				recv_data = self.recv()
			except ReceiveChecksumError:
				self.send( ('%X' % ID) + 'R')
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
	
