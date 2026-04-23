"""Enumeracje kontraktów zadań."""

from enum import Enum


class TaskType(str, Enum):
    """Typy zadań obsługiwanych przez orkiestrator."""

    CLASSIFICATION = "classification"
    EXTRACTION = "extraction"
    GENERATION = "generation"
    VALIDATION = "validation"
    SCORING = "scoring"


class TaskStatus(str, Enum):
    """Status wykonania zadania."""

    QUEUED = "queued"
    RUNNING = "running"
    SUCCEEDED = "succeeded"
    FAILED = "failed"
    ABSTAINED = "abstained"


class FinalOutcome(str, Enum):
    """Końcowy wynik semantyczny zadania."""

    SUCCESS = "success"
    PARTIAL_SUCCESS = "partial_success"
    FAILURE = "failure"
    ABSTAINED = "abstained"
