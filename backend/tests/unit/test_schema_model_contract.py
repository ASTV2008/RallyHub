"""Contrato esquemas <-> modelos (análisis estático con `ast`; no requiere SQLAlchemy ni FastAPI).

Detecta el defecto típico de "el esquema de respuesta exige un campo que el modelo ORM no expone",
que en ejecución se manifestaría como un error 500 al serializar (from_attributes).
"""
import ast
from pathlib import Path

import pytest

APP = Path(__file__).resolve().parents[2] / "app"

# esquema de lectura -> modelo ORM que lo alimenta
PAIRS = {
    "UserRead": "User", "StudentRead": "Student", "CoachRead": "Coach",
    "FacilityRead": "Facility", "TableRead": "GameTable", "MaintenanceRead": "MaintenanceBlock",
    "ReservationRead": "Reservation", "ClassRead": "ClassSession", "EnrollmentRead": "ClassEnrollment",
    "AttendanceRead": "Attendance", "ProgressRead": "ProgressRecord", "TournamentRead": "Tournament",
    "ParticipantRead": "TournamentParticipant", "MatchRead": "TournamentMatch", "AuditRead": "AuditLog",
}


def _classes(folder: str) -> dict[str, ast.ClassDef]:
    out = {}
    for path in (APP / folder).glob("*.py"):
        for node in ast.parse(path.read_text(encoding="utf-8")).body:
            if isinstance(node, ast.ClassDef):
                out[node.name] = node
    return out


def _model_members(cls: ast.ClassDef) -> set[str]:
    names = set()
    for n in cls.body:
        if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name):
            names.add(n.target.id)
        elif isinstance(n, ast.FunctionDef):
            names.add(n.name)
    return names


def _required_fields(cls: ast.ClassDef) -> set[str]:
    return {n.target.id for n in cls.body
            if isinstance(n, ast.AnnAssign) and isinstance(n.target, ast.Name) and n.value is None}


MODELS = _classes("models")
SCHEMAS = _classes("schemas")


@pytest.mark.parametrize(("schema", "model"), PAIRS.items())
def test_read_schema_fields_exist_on_model(schema, model):
    assert schema in SCHEMAS, f"{schema} no existe"
    assert model in MODELS, f"{model} no existe"
    missing = _required_fields(SCHEMAS[schema]) - _model_members(MODELS[model])
    assert not missing, f"{schema} exige {sorted(missing)} pero {model} no los expone"
