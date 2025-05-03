class InvalidTransitionError(Exception):
    """Raised when an invalid state transition is attempted."""
    def __init__(self, from_state: str, to_state: str, message: str = ""):
        self.from_state = from_state
        self.to_state = to_state
        self.message = message or f"Transition from {from_state} to {to_state} is not allowed or justification is missing."
        super().__init__(self.message) 