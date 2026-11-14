"""Excepciones de dominio.

Cada excepción declara el código HTTP con el que la capa API debe responder.
La capa de dominio no importa FastAPI: solo expone `status_code` y `code`.
"""


class DomainError(Exception):
    status_code: int = 400
    code: str = "domain_error"

    def __init__(self, message: str) -> None:
        super().__init__(message)
        self.message = message


class InvalidInterval(DomainError):
    code = "invalid_interval"


class DurationOutOfRange(DomainError):
    code = "duration_out_of_range"


class OutsideOperatingHours(DomainError):
    code = "outside_operating_hours"


class PastDateError(DomainError):
    code = "past_date"


class AdvanceLimitExceeded(DomainError):
    code = "advance_limit_exceeded"


class AuthenticationError(DomainError):
    status_code = 401
    code = "not_authenticated"


class InvalidCurrentPassword(DomainError):
    """La contraseña actual no coincide. Es 400 (no 401) para que la interfaz no cierre la sesión."""

    code = "invalid_current_password"


class ForbiddenError(DomainError):
    status_code = 403
    code = "forbidden"


class NotFoundError(DomainError):
    status_code = 404
    code = "not_found"


class ConflictError(DomainError):
    status_code = 409
    code = "conflict"


class ReservationConflict(ConflictError):
    code = "reservation_conflict"


class ResourceUnavailable(ConflictError):
    code = "resource_unavailable"


class CapacityExceeded(ConflictError):
    code = "capacity_exceeded"


class DuplicateError(ConflictError):
    code = "duplicate"


class FutureReservationsExist(ConflictError):
    """La operación dejaría reservas confirmadas sobre una mesa que ya no estará disponible."""

    code = "has_future_reservations"


class CancellationNotAllowed(ConflictError):
    code = "cancellation_not_allowed"


class TooManyRequests(DomainError):
    status_code = 429
    code = "too_many_requests"
