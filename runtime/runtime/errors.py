class RuntimeErrorBase(Exception):
    pass


class PermanentBotError(RuntimeErrorBase):
    pass


class InvalidTokenError(PermanentBotError):
    pass


class MissingIntentsError(PermanentBotError):
    pass


class SupervisorCapacityError(RuntimeErrorBase):
    pass


class FlowExecutionError(RuntimeErrorBase):
    pass


class FlowTimeoutError(FlowExecutionError):
    pass


class FlowLimitError(FlowExecutionError):
    pass


class ValidationError(RuntimeErrorBase):
    pass


class TemplateError(ValidationError):
    pass


class ConfigError(ValidationError):
    pass
