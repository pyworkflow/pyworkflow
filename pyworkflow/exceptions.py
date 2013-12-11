class UnknownResourceException(Exception):
	pass

class UnknownProcessException(UnknownResourceException):
	pass

class UnknownActivityException(UnknownResourceException):
	pass

class UnknownDecisionException(UnknownResourceException):
	pass

class TimedOutException(Exception):
	pass