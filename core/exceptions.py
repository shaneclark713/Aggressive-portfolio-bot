class BotError(Exception): pass
class ConfigurationError(BotError): pass
class BrokerError(BotError): pass
class ValidationError(BotError): pass
