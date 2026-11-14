from __future__ import annotations

import enum


class Role(enum.StrEnum):
    ADMIN = "ADMIN"
    COACH = "COACH"
    STUDENT = "STUDENT"


class Level(enum.StrEnum):
    BEGINNER = "BEGINNER"
    INTERMEDIATE = "INTERMEDIATE"
    ADVANCED = "ADVANCED"


class TableStatus(enum.StrEnum):
    ACTIVE = "ACTIVE"
    MAINTENANCE = "MAINTENANCE"
    OUT_OF_SERVICE = "OUT_OF_SERVICE"


class ReservationStatus(enum.StrEnum):
    CONFIRMED = "CONFIRMED"
    CANCELLED = "CANCELLED"
    COMPLETED = "COMPLETED"
    NO_SHOW = "NO_SHOW"


class ClassStatus(enum.StrEnum):
    DRAFT = "DRAFT"
    PUBLISHED = "PUBLISHED"
    CANCELLED = "CANCELLED"


class EnrollmentStatus(enum.StrEnum):
    ENROLLED = "ENROLLED"
    WITHDRAWN = "WITHDRAWN"


class AttendanceStatus(enum.StrEnum):
    PRESENT = "PRESENT"
    ABSENT = "ABSENT"
    JUSTIFIED = "JUSTIFIED"


class TournamentStatus(enum.StrEnum):
    OPEN = "OPEN"
    CLOSED = "CLOSED"
    FINISHED = "FINISHED"
    CANCELLED = "CANCELLED"


class Modality(enum.StrEnum):
    SINGLES = "SINGLES"
    DOUBLES = "DOUBLES"
