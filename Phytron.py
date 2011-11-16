import serial, string

class ReceiveTimeout(Exception):
	pass

class ReceiveChecksumError(Exception):
	def __init__(self, expected, received):
		self.expected = expected
		self.received = received
		self.message = "Checksum Error: expected %x, got %x" % (expected, received)

class RXBufferOverrunError(EnvironmentError):
	pass

class NotNowWarning(UserWarning):
	pass

class UnknownCommand(Exception):
	pass

class BadValueError(Exception):
	pass

class ParameterLimitsError(ValueError):
	pass

class Axis:
	def __init__(self, ipcomm, ID, name = None):
		self.ipcomm = ipcomm
		self.ID = ID
		self.name = name

	def execute(self, cmd):
		result = self.ipcomm.execute(self.ID, cmd)
		assert result.ID == self.ID
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
	COLDBOOT          = (1<<7)
	ANY_ERROR         = (1<<6)
	RX_ERROR          = (1<<5)
	SFI_ERROR         = (1<<4)
	OUTPUTSTAGE_ERROR = (1<<3)
	INITIATOR_MINUS   = (1<<2)
	INITIATOR_PLUS    = (1<<1)
	RUNNING           = (1<<0)
	def __init__(self, bitvector):
		self.coldboot          = not not (bitvector & Status.COLDBOOT)
		self.any_error         = not not (bitvector & Status.ANY_ERROR)
		self.rx_error          = not not (bitvector & Status.RX_ERROR)
		self.SFI_error         = not not (bitvector & Status.SFI_ERROR)
		self.outputstage_error = not not (bitvector & Status.OUTPUTSTAGE_ERROR)
		self.initiator_minus   = not not (bitvector & Status.INITIATOR_MINUS)
		self.initiator_plus    = not not (bitvector & Status.INITIATOR_PLUS)
		self.running           = not not (bitvector & Status.RUNNING)
	
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
		if self.initiator_minus:
			status += ['Initiator -']
		if self.initiator_plus:
			status += ['Initiator +']
		if self.running:
			status += ['Running']
		return '{'+ ('|'.join(status)) + '}'

class ExtendedStatus:
	CHECKSUM_ERROR   = (1<<23)
	                 # (1<<22)
	RXBUFFER_OVERRUN = (1<<21)
	NOT_NOW          = (1<<20)
	UNKNOWN_COMMAND  = (1<<19)
	BAD_VALUE        = (1<<18)
	PARAMETER_LIMITS = (1<<17)
	                 # (1<<16)
	NO_SYSTEM         = (1<<15)
	NO_RAMPS          = (1<<14)
	PARAMETER_CHANGED = (1<<13)
	BUSY              = (1<<12)
	PROGRAMING_ERROR  = (1<<11)
	HIGH_TEMPERATURE  = (1<<10)
	INITIATOR_ERROR   = (1<< 9)
	INTERNAL_ERROR    = (1<< 8)
	DRIVER_ERROR  = (1<< 7)
	              # (1<< 6)
	WAIT_FOR_SYNC = (1<< 5)
	LINEAR_AXIS   = (1<< 4)
	FREE_RUNNING  = (1<< 3)
	INITIALIZED   = (1<< 2)
	HW_DISABLE    = (1<< 1)
	INITIALIZING  = (1<< 0)
	def __init__(self, bitvector):
		self.checksum_error    = not not (bitvector & ExtendedStatus.CHECKSUM_ERROR)
		self.rxbuffer_overrun  = not not (bitvector & ExtendedStatus.RXBUFFER_OVERRUN)
		self.not_now           = not not (bitvector & ExtendedStatus.NOT_NOW)
		self.unknown_command   = not not (bitvector & ExtendedStatus.UNKNOWN_COMMAND)
		self.bad_value         = not not (bitvector & ExtendedStatus.BAD_VALUE)
		self.parameter_limits  = not not (bitvector & ExtendedStatus.PARAMETER_LIMITS)
		self.no_system         = not not (bitvector & ExtendedStatus.NO_SYSTEM)
		self.no_ramps          = not not (bitvector & ExtendedStatus.NO_RAMPS)
		self.parameter_changed = not not (bitvector & ExtendedStatus.PARAMETER_CHANGED)
		self.busy              = not not (bitvector & ExtendedStatus.BUSY)
		self.programing_error  = not not (bitvector & ExtendedStatus.PROGRAMING_ERROR)
		self.high_temperature  = not not (bitvector & ExtendedStatus.HIGH_TEMPERATURE)
		self.initiator_error   = not not (bitvector & ExtendedStatus.INITIATOR_ERROR)
		self.internal_error    = not not (bitvector & ExtendedStatus.INTERNAL_ERROR)
		self.driver_error      = not not (bitvector & ExtendedStatus.DRIVER_ERROR)
		self.wait_for_sync     = not not (bitvector & ExtendedStatus.WAIT_FOR_SYNC)
		self.linear_axis       = not not (bitvector & ExtendedStatus.LINEAR_AXIS)
		self.free_running      = not not (bitvector & ExtendedStatus.FREE_RUNNING)
		self.initialized       = not not (bitvector & ExtendedStatus.INITIALIZED)
		self.hw_disable        = not not (bitvector & ExtendedStatus.HW_DISABLE)
		self.initializing      = not not (bitvector & ExtendedStatus.INITIALIZING)

class ReceiveData:
	def __init__(self, ID, status, data):
		self.ID = ID
		self.status = status
		self.data = data

class IPCOMM:
	def __init__(self, url, baudrate = 38400, axisnames = None):
		self.conn = serial.serial_for_url(url)
		self.conn.baudrate = baudrate
		self.conn.parity = serial.PARITY_NONE
		self.conn.rtscts = False
		self.conn.dsrdtr = False
		self.conn.xonxoff = False
		self.conn.timeout = 0.5
		self.axisByID = dict()
		self.axisByName = dict()
		self.enumerate(axisnames)

	def axis(self, nameOrID):
		if isinstance(nameOrID, str) and nameOrID.isalpha():
			return self.axisByName[nameOrID]
		return self.axisByID[int(nameOrID)]

	def enumerate(self, names=None):
		# Use a only short timeout for enumeration.
		oldtimeout = self.conn.timeout
		self.conn.timeout = 0.05
		self.axisByID.clear()
		self.axisByName.clear()
		for ID in range(0x10):
			try:
				if self.execute(ID, 'IS?').ID == ID:
					if ((isinstance(names, dict) and names.haskey(ID)) or (isinstance(names, list) and ID < len(names))) and names[ID].isalpha():
						axis = self.axisByName[str(names[ID])] = Axis(self, ID, names[ID])
					else:
						axis = Axis(self, ID)
					self.axisByID[ID] = axis
			except ReceiveTimeout:
				continue
		self.conn.timeout = oldtimeout

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
				raise ReceiveTimeout()

		c = None
		while c != '\x03':
			c = self.conn.read(1)
			if not c:
				raise ReceiveTimeout()
			buf += c

		status, data, chksm = buf[:-1].split(':')
		expected_chksm = checksum(status + ':' + data + ':')
		chksm = string.atoi(chksm, 0x10)
		if expected_chksm != chksm:
			raise ReceiveChecksumError(expected_chksm, chksm)

		return ReceiveData( ID = string.atoi(status[0], 0x10),
		                    status = Status(string.atoi(status[1:], 0x10)), 
		                    data = data )

	def broadcast(self, cmd):
		self.conn.flushInput()
		self.send( '@' + cmd )
	
	def execute(self, ID, cmd):
		if cmd == 'IS?':
			return self.queryextendedstatus(ID)

		self.conn.flushInput()
		self.send( ('%X' % ID) + cmd )

		recv_data = None
		while not recv_data:
			try:
				recv_data = self.recv()
			except ReceiveChecksumError:
				self.send( ('%X' % ID) + 'R')

			if recv_data.status.rx_error:
				extended_status = self.queryextendedstatus(ID).data

				if extended_status.checksum_error:
					self.conn.flushInput()
					self.send( ('%X' % ID) + cmd )
					recv_data = None
					continue

				if extended_status.rxbuffer_overrun:
					raise RXBufferOverrunError()

				if extended_status.not_now:
					raise NotNowWarning()

				if extended_status.unknown_command:
					raise UnknownCommand()

				if extended_status.bad_value:
					raise BadValueError()

				if extended_status.parameter_limits:
					raise ParameterLimitsError()


		return recv_data

	def queryextendedstatus(self, ID):
		"""
		Special function for querying the extended status.
		Same basic structure like execute, with the following exceptions:
		* does not take a command (always issued a IS?)
		* will not resend query if status rx_error is reported
		* will not request reply retransmission
		* will not raise status related exceptions

		Since regular execute will raise exceptions based on IS? status
		to query the status for further processing, this method must be used.

		If the extended status can not be requested, None is returned.
		"""
		self.conn.flushInput()
		self.send( ('%X' % ID) + 'IS?' )

		recv_data = None
		try:
			recv_data = self.recv()
		except ReceiveChecksumError:
			return None

		if recv_data:
			recv_data.data = ExtendedStatus(string.atoi(recv_data.data, 0x10))
		else:
			recv_data = None

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
	
