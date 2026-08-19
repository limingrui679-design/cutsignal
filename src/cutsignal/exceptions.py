"""Domain-specific exceptions surfaced by CutSignal."""


class CutSignalError(Exception):
    """Base exception for expected CutSignal failures."""


class DataValidationError(CutSignalError):
    """Raised when an input file is structurally valid but semantically unsafe."""


class InsufficientDataError(CutSignalError):
    """Raised when a method cannot return a defensible estimate."""


class OptimizationInfeasibleError(CutSignalError):
    """Raised when diet constraints cannot be satisfied."""
