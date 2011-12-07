import serial, string, threading

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

def checksum(data):
	chksm = 0
	for d in data:
		chksm = chksm ^ ord(d)
	return chksm

class Status(object):
	COLDBOOT          = (1<<7)
	ANY_ERROR         = (1<<6)
	RX_ERROR          = (1<<5)
	SFI_ERROR         = (1<<4)
	OUTPUTSTAGE_ERROR = (1<<3)
	INITIATOR_MINUS   = (1<<2)
	INITIATOR_PLUS    = (1<<1)
	RUNNING           = (1<<0)
	def __init__(self, status):
		if isinstance(status, Status):
			self.coldboot  = status.coldboot
			self.any_error = status.any_error
			self.rx_error  = status.rx_error
			self.SFI_error = status.SFI_error
			self.outputstage_error = status.outputstage_error
			self.initiator_plus  = status.initiator_plus
			self.initiator_minus = status.initiator_minus
			self.running = status.running
		if isinstance(status, int):
			bitvector = status
			self.coldboot          = bool(bitvector & Status.COLDBOOT)
			self.any_error         = bool(bitvector & Status.ANY_ERROR)
			self.rx_error          = bool(bitvector & Status.RX_ERROR)
			self.SFI_error         = bool(bitvector & Status.SFI_ERROR)
			self.outputstage_error = bool(bitvector & Status.OUTPUTSTAGE_ERROR)
			self.initiator_minus   = bool(bitvector & Status.INITIATOR_MINUS)
			self.initiator_plus    = bool(bitvector & Status.INITIATOR_PLUS)
			self.running           = bool(bitvector & Status.RUNNING)
	
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

class ExtendedStatus(Status):
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
	def __init__(self, bitvector, simplestatus):
		super(ExtendedStatus, self).__init__(simplestatus)
		self.checksum_error    = bool(bitvector & ExtendedStatus.CHECKSUM_ERROR)
		self.rxbuffer_overrun  = bool(bitvector & ExtendedStatus.RXBUFFER_OVERRUN)
		self.not_now           = bool(bitvector & ExtendedStatus.NOT_NOW)
		self.unknown_command   = bool(bitvector & ExtendedStatus.UNKNOWN_COMMAND)
		self.bad_value         = bool(bitvector & ExtendedStatus.BAD_VALUE)
		self.parameter_limits  = bool(bitvector & ExtendedStatus.PARAMETER_LIMITS)
		self.no_system         = bool(bitvector & ExtendedStatus.NO_SYSTEM)
		self.no_ramps          = bool(bitvector & ExtendedStatus.NO_RAMPS)
		self.parameter_changed = bool(bitvector & ExtendedStatus.PARAMETER_CHANGED)
		self.busy              = bool(bitvector & ExtendedStatus.BUSY)
		self.programing_error  = bool(bitvector & ExtendedStatus.PROGRAMING_ERROR)
		self.high_temperature  = bool(bitvector & ExtendedStatus.HIGH_TEMPERATURE)
		self.initiator_error   = bool(bitvector & ExtendedStatus.INITIATOR_ERROR)
		self.internal_error    = bool(bitvector & ExtendedStatus.INTERNAL_ERROR)
		self.driver_error      = bool(bitvector & ExtendedStatus.DRIVER_ERROR)
		self.wait_for_sync     = bool(bitvector & ExtendedStatus.WAIT_FOR_SYNC)
		self.linear_axis       = bool(bitvector & ExtendedStatus.LINEAR_AXIS)
		self.free_running      = bool(bitvector & ExtendedStatus.FREE_RUNNING)
		self.initialized       = bool(bitvector & ExtendedStatus.INITIALIZED)
		self.hw_disable        = bool(bitvector & ExtendedStatus.HW_DISABLE)
		self.initializing      = bool(bitvector & ExtendedStatus.INITIALIZING)

	def __str__(self):
		status = list()
		simplestatus_str = Status.__str__(self)[1:-1]
		if self.checksum_error:
			status += ["Checksum Error"]
		if self.rxbuffer_overrun:
			status += ["RX Buffer Overrun"]
		if self.not_now:
			status += ["Not Now"]
		if self.unknown_command:
			status += ["Unknown Command"]
		if self.bad_value:
			status += ["Bad Value"]
		if self.parameter_limits:
			status += ["Parameter Limits"]
		if self.no_system:
			status += ["Mo System"]
		if self.no_ramps:
			status += ["No Ramps"]
		if self.parameter_changed:
			status += ["Parameter Changed"]
		if self.busy:
			status += ["Busy"]
		if self.programing_error:
			status += ["Programming Error"]
		if self.high_temperature:
			status += ["High Temperature"]
		if self.initiator_error:
			status += ["Initiator Error"]
		if self.driver_error:
			status += ["Driver Error"]
		if self.wait_for_sync:
			status += ["Wait For Sync"]
		if self.linear_axis:
			status += ["Linear Axis"]
		if self.free_running:
			status += ["Free Running"]
		if self.initialized:
			status += ["Initialized"]
		if self.hw_disable:
			status += ["HW Disable"]
		if self.initializing:
			status += ["Initialzing"]
		return '{' + '|'.join((simplestatus_str, '|'.join(status))) +'}'
		
class ReceiveData:
	def __init__(self, ID, status, data):
		self.ID = ID
		self.status = status
		self.data = data

class Axis(object):
	"""
	Abstraction for a IPCOMM Axis
	Phytron IPCOMM devices are addressable by a 4 bit ID (i.e. range 0x0 = 0 ... 0xf = 15).
	This allows for up to 16 IPCOMM devices being connected to a single communication bus.
	Each device is a strict master/slave communication endpoint ultimately driving an
	actuator. This is referred to as an Axis.
	"""
	def __init__(self, ipcomm, ID, name = None):
		"""
		ipcomm: a instance of Phytron.IPCOMM class, encapsulating a communication bus
		name: The human readable name given to the axis (served not purpose in this class at the moment)
		"""
		self.ipcomm = ipcomm
		self.ID = ID
		self.name = name

	def execute(self, cmd):
		"""
		Execute a command on the axis.
		"""
		result = self.ipcomm.execute(self.ID, cmd)
		assert result.ID == self.ID
		self.status = result.status
		if isinstance(result.data, ExtendedStatus):
			self.extended_status = result.data
		return result

	def getFullStatus(self):
		return self.execute("IS?").data
	
	def gotoAbsolute(self, position):
		return self.execute("GA%d" % position).status
	gotoAbs = gotoAbsolute
	
	def gotoRelative(self, offset):
		return self.execute("GR%d" % offset).status
	gotoRel = gotoRelative
	
	def runForward(self):
		return self.execute("GF+").status
	def runBackward(self):
		return self.execute("GF-").status
	
	def stepForward(self):
		return self.execute("GS+").status
	def stepBackward(self):
		return self.execute("GS-").status

	def initializePlus(self):
		return self.execute("GI+").status
	def initializeMinus(self):
		return self.execute("GI-").status

	def syncstartCommence(self):
		return self.execute("GW").status
	def syncstartAbort(self):
		return self.execute("GB").status

	def halt(self):
		return self.execute("H").status

	def stop(self):
		return self.execute("B").status

	def setRunCurrent(self, current):
		return self.execute("PR%1.1f" % current)
	def getRunCurrent(self):
		return float(self.execute("PR??").data)
	run_current = property(getRunCurrent, setRunCurrent)

	def setBoostCurrent(self, current):
		return self.execute("PA%1.1f" % current)
	def getBoostCurrent(self):
		return float(self.execute("PA??").data)
	boost_current = property(getBoostCurrent, setBoostCurrent)

	def setBoostDuration(self, duration):
		return self.execute("PT%d" % int(duration * 1e3)).status
	def getBoostDuration(self):
		return float(self.execute("PT?").data) * 1e-3
	boost_duration = property(getBoostDuration, setBoostDuration)
	
	def setHaltCurrent(self, current):
		return self.execute("PS%1.1f" % current)
	def getHaltCurrent(self):
		return float(self.execute("PS??").data)
	halt_current = property(getHaltCurrent, setHaltCurrent)
	
	def setPosition(self, position):
		return self.execute("PC%d" % position).status
	def getPosition(self):
		return int(self.execute("PC?").data)
	position = property(getPosition, setPosition)

	def setRunFrequency(self, freq):
		return self.execute("PF%d" % freq).status
	def getRunFrequency(self):
		return int(self.execute("PF?").data)
	run_frequency = property(getRunFrequency, setRunFrequency)
	
	def getMaxFrequency(self):
		return int(self.execute("IF?").data)
	max_frequency = property(getMaxFrequency)

	def setOffsetFrequency(self, freq):
		return self.execute("PO%d" % freq).status
	def getOffsetFrequency(self):
		return int(self.execute("PO?").data)
	offset_frequency = property(getOffsetFrequency, setOffsetFrequency)
	
	def setRunLimit(self, limit):
		if not limit:
			limit = 0xffffffff
		return self.execute("PG%d" % limit).status
	def getRunLimit(self, position):
		return int(self.execute("PG?").data)
	run_limit = property(getRunLimit, setRunLimit)

	def setOffsetMinus(self, offset):
		return self.execute("PM%d" % offset).status
	def getOffsetMinus(self):
		return int(self.execute("PM?").data)
	offset_minus = property(getOffsetMinus, setOffsetMinus)

	def setOffsetPlus(self, offset):
		return self.execute("PP%d" % offset).status
	def getOffsetPlus(self):
		return int(self.execute("PP?").data)
	offset_plus = property(getOffsetPlus, setOffsetPlus)

	def setLimited(self, limited):
		if limited:
			limited = 1
		else:
			limited = 0
		return self.execute("PL%d" % limited).status
	def getLimited(self):
		return bool(int(self.execute("PL?").data))
	limited = property(getLimited, setLimited)

	def setDeltaZero(self, deltazero):
		return self.execute("IZ%d" % deltazero).status
	def getDeltaZero(self):
		return int(self.execute("IZ?"))
	delta_zero = property(getDeltaZero, setDeltaZero)

	def setOutputs(self, outputstate):
		outputs = 0
		if isinstance(outputstate, list):
			for i,s in enumerate(outputstate):
				if outputstate[i]:
					outputs |= 1<<i
		else:
			outputs = outputstate
		return self.execute("IO%x" % (outputs & 0xf) ).status
	def getOutputs(self):
		outputstate = string.atoi(self.execute("IO?").data, 0x10)
		outputs = [True if outputstate & 1<<i else False for i in range(4)]
		return outputs
	outputs = property(getOutputs, setOutputs)

	def getInputs(self):
		inputstate = string.atoi(self.execute("II?").data, 0x10)
		inputs = [True if inputstate & 1<<i else False for i in range(8)]
		return inputs
	inputs = property(getInputs)

	def clearDriverError():
		return self.execute("CA").status
	def clearInitiatorError():
		return self.execute("CI").status
	def clearOutputError():
		return self.execute("CO").status

	def resetHW():
		return self.execute("CR").status
	def resetSFI():
		return self.execute("CS").status

	def getDriverTemperature():
		return int(self.execute("SA?").data)
	driver_temperature = property(getDriverTemperature)

	def getDriverCurrent():
		return int(self.execute("SC?").data)
	driver_current = property(getDriverCurrent)

	def getDriverVoltage():
		return int(self.execute("SU?").data)
	driver_voltage = property(getDriverVoltage)

class IPCOMM(object):
	MAX_RETRY_COUNT = 5
	def __init__(self, url, baudrate = 38400, axes = 0x10, axisnames = None):
		self.rlock = threading.RLock()
		self.conn = serial.serial_for_url(url)
		self.conn.baudrate = baudrate
		self.conn.parity = serial.PARITY_NONE
		self.conn.rtscts = False
		self.conn.dsrdtr = False
		self.conn.xonxoff = False
		self.conn.timeout = 0.5
		self.axisByID = dict()
		self.axisByName = dict()
		self.enumerate(axes, axisnames)
		self.max_retry_count = IPCOMM.MAX_RETRY_COUNT

	def axis(self, nameOrID):
		if isinstance(nameOrID, str) and nameOrID.isalpha():
			return self.axisByName[nameOrID]
		return self.axisByID[int(nameOrID)]

	def __len__(self):	
		return len(self.axisByID.keys())
	
	def __iter__(self):
		return self.axisByID.itervalues()

	def __getitem__(self, key):
		try:
			return self.axis(key)
		except KeyError:
			raise IndexError(key)
	
	def __contains__(self, item):
		return item in self.axisByName.keys() or item in self.axisByID.keys()

	def enumerate(self, axes=0x10, names=None):
		if isinstance(axes, int):
			axes = range(axes)
		# Use a only short timeout for enumeration.
		oldtimeout = self.conn.timeout
		self.conn.timeout = 0.05
		self.axisByID.clear()
		self.axisByName.clear()
		try:
			for i,ID in enumerate(axes):
				try:
					if self.execute(ID, 'IS?').ID == ID:
						if ((isinstance(names, dict) and names.haskey(ID)) or (isinstance(names, list) and i < len(names))) and names[i].isalpha():
							if isinstance(names, dict):
								axisname = names[ID]
							else:
								axisname = names[i]
							axis = self.axisByName[str(axisname)] = Axis(self, ID, axisname)
						else:
							axis = Axis(self, ID)
						self.axisByID[ID] = axis
				except ReceiveTimeout:
					continue
		finally:
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

		recv_data = None

		with self.rlock:
			self.conn.flushInput()
			self.send( ('%X' % ID) + cmd )

			retry_count = 0
			while not recv_data and retry_count < self.max_retry_count:
				try:
					recv_data = self.recv()
				except ReceiveChecksumError:
					self.send( ('%X' % ID) + 'R')
					retry_count += 1

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
		to query the status for further processing, this method must be
		used instead to avoid infinite loops.

		If the extended status can not be requested, None is returned.
		"""
		recv_data = None

		with self.rlock:
			self.conn.flushInput()
			self.send( ('%X' % ID) + 'IS?' )

			try:
				recv_data = self.recv()
			except ReceiveChecksumError:
				return None

			if recv_data:
				recv_data.data = ExtendedStatus(string.atoi(recv_data.data, 0x10), recv_data.status)
			else:
				recv_data = None

		return recv_data
	
	def syncstartCommence(self):
		self.broadcast("GW")
	def syncstartExecute(self):
		self.broadcast("GX")
	def syncstartAbort(self):
		self.broadcast("GB")
