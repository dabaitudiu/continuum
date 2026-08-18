class RuntimeDomainError(Exception):
    """A stable runtime error suitable for API and event boundaries."""

    def __init__(self, code: str, message: str) -> None:
        self.code = code
        self.message = message
        super().__init__(f"{code}: {message}")
