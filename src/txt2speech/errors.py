class InputError(Exception):
    pass


class EngineError(Exception):
    pass


class ResourceExhausted(EngineError):  # noqa: N818
    pass
