class MemoryError(Exception):
    pass


class DatabaseError(MemoryError):
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class RetrievalError(MemoryError):
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class ConsolidationError(MemoryError):
    def __init__(self, message: str, original_error: Exception | None = None):
        super().__init__(message)
        self.original_error = original_error


class ValidationError(MemoryError):
    def __init__(self, message: str, field: str | None = None):
        super().__init__(message)
        self.field = field


class NotFoundError(MemoryError):
    def __init__(self, resource: str, identifier: str | int):
        super().__init__(f"{resource} not found: {identifier}")
        self.resource = resource
        self.identifier = identifier