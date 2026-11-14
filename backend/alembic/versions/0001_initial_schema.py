"""Esquema inicial de RallyHub.

Revision ID: 0001
Revises:
"""
import sqlalchemy as sa
from alembic import op

revision = "0001"
down_revision = None
branch_labels = None
depends_on = None


def enum(name: str, *values: str) -> sa.Enum:
    return sa.Enum(*values, name=name, native_enum=False, length=20, create_constraint=True)


def pk() -> sa.Column:
    return sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True)


def created(name: str = "created_at") -> sa.Column:
    return sa.Column(name, sa.DateTime(), nullable=False)


LEVEL = ("BEGINNER", "INTERMEDIATE", "ADVANCED")


def upgrade() -> None:
    op.create_table(
        "users", pk(),
        sa.Column("email", sa.String(254), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("role", enum("user_role", "ADMIN", "COACH", "STUDENT"), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        sa.Column("token_version", sa.Integer(), nullable=False),
        created(),
        sa.UniqueConstraint("email"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_table(
        "students", pk(),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("last_name", sa.String(80), nullable=False),
        sa.Column("birth_date", sa.Date()),
        sa.Column("phone", sa.String(30)),
        sa.Column("guardian_name", sa.String(120)),
        sa.Column("level", enum("student_level", *LEVEL), nullable=False),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        created(),
        sa.UniqueConstraint("user_id"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_table(
        "coaches", pk(),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id"), nullable=False),
        sa.Column("first_name", sa.String(80), nullable=False),
        sa.Column("last_name", sa.String(80), nullable=False),
        sa.Column("specialty", sa.String(120)),
        sa.Column("bio", sa.Text()),
        sa.Column("phone", sa.String(30)),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        created(),
        sa.UniqueConstraint("user_id"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_table(
        "facilities", pk(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("address", sa.String(200)),
        sa.Column("description", sa.Text()),
        sa.Column("is_active", sa.Boolean(), nullable=False),
        created(),
        sa.UniqueConstraint("name"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_table(
        "tables", pk(),
        sa.Column("facility_id", sa.Integer(), sa.ForeignKey("facilities.id"), nullable=False),
        sa.Column("code", sa.String(30), nullable=False),
        sa.Column("table_type", sa.String(60)),
        sa.Column("description", sa.Text()),
        sa.Column("status", enum("table_status", "ACTIVE", "MAINTENANCE", "OUT_OF_SERVICE"),
                  nullable=False),
        created(),
        sa.UniqueConstraint("facility_id", "code", name="uq_tables_facility_code"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_tables_facility_id", "tables", ["facility_id"])
    op.create_table(
        "maintenance_blocks", pk(),
        sa.Column("table_id", sa.Integer(), sa.ForeignKey("tables.id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("reason", sa.String(200)),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        created(),
        sa.CheckConstraint("ends_at > starts_at", name="range"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_maintenance_blocks_table_range", "maintenance_blocks",
                    ["table_id", "starts_at", "ends_at"])
    op.create_table(
        "reservations", pk(),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("table_id", sa.Integer(), sa.ForeignKey("tables.id"), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("status", enum("reservation_status", "CONFIRMED", "CANCELLED", "COMPLETED",
                                 "NO_SHOW"), nullable=False),
        sa.Column("notes", sa.String(300)),
        sa.Column("created_by", sa.Integer(), sa.ForeignKey("users.id")),
        created(),
        sa.Column("cancelled_at", sa.DateTime()),
        sa.CheckConstraint("ends_at > starts_at", name="range"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_reservations_table_range", "reservations",
                    ["table_id", "starts_at", "ends_at"])
    op.create_index("ix_reservations_student_start", "reservations", ["student_id", "starts_at"])
    op.create_table(
        "classes", pk(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("coach_id", sa.Integer(), sa.ForeignKey("coaches.id"), nullable=False),
        sa.Column("table_id", sa.Integer(), sa.ForeignKey("tables.id")),
        sa.Column("level", enum("class_level", *LEVEL), nullable=False),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("starts_at", sa.DateTime(), nullable=False),
        sa.Column("ends_at", sa.DateTime(), nullable=False),
        sa.Column("status", enum("class_status", "DRAFT", "PUBLISHED", "CANCELLED"),
                  nullable=False),
        created(),
        sa.CheckConstraint("ends_at > starts_at", name="range"),
        sa.CheckConstraint("capacity >= 1", name="capacity"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_classes_coach_range", "classes", ["coach_id", "starts_at", "ends_at"])
    op.create_index("ix_classes_table_range", "classes", ["table_id", "starts_at", "ends_at"])
    op.create_table(
        "class_enrollments", pk(),
        sa.Column("class_id", sa.Integer(), sa.ForeignKey("classes.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("status", enum("enrollment_status", "ENROLLED", "WITHDRAWN"), nullable=False),
        created("enrolled_at"),
        sa.UniqueConstraint("class_id", "student_id", name="uq_class_enrollments_class_student"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_class_enrollments_class_id", "class_enrollments", ["class_id"])
    op.create_index("ix_class_enrollments_student_id", "class_enrollments", ["student_id"])
    op.create_table(
        "attendances", pk(),
        sa.Column("enrollment_id", sa.Integer(), sa.ForeignKey("class_enrollments.id"),
                  nullable=False),
        sa.Column("status", enum("attendance_status", "PRESENT", "ABSENT", "JUSTIFIED"),
                  nullable=False),
        sa.Column("notes", sa.String(300)),
        sa.Column("recorded_by", sa.Integer(), sa.ForeignKey("users.id")),
        created("recorded_at"),
        sa.Column("updated_at", sa.DateTime()),
        sa.UniqueConstraint("enrollment_id"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    skills = ("serve", "receive", "ball_control", "movement", "strategy")
    op.create_table(
        "progress_records", pk(),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        sa.Column("coach_id", sa.Integer(), sa.ForeignKey("coaches.id"), nullable=False),
        sa.Column("recorded_on", sa.Date(), nullable=False),
        *(sa.Column(s, sa.SmallInteger(), nullable=False) for s in skills),
        sa.Column("notes", sa.String(500)),
        created(),
        *(sa.CheckConstraint(f"{s} BETWEEN 1 AND 5", name=s) for s in skills),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_progress_records_student_date", "progress_records",
                    ["student_id", "recorded_on"])
    op.create_table(
        "tournaments", pk(),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("category", sa.String(60)),
        sa.Column("modality", enum("tournament_modality", "SINGLES", "DOUBLES"), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("location", sa.String(200)),
        sa.Column("capacity", sa.Integer(), nullable=False),
        sa.Column("status", enum("tournament_status", "OPEN", "CLOSED", "FINISHED", "CANCELLED"),
                  nullable=False),
        created(),
        sa.CheckConstraint("ends_on >= starts_on", name="range"),
        sa.CheckConstraint("capacity >= 2", name="capacity"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_table(
        "tournament_participants", pk(),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id"), nullable=False),
        sa.Column("student_id", sa.Integer(), sa.ForeignKey("students.id"), nullable=False),
        created("registered_at"),
        sa.UniqueConstraint("tournament_id", "student_id",
                            name="uq_tournament_participants_tournament_student"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_tournament_participants_tournament_id", "tournament_participants",
                    ["tournament_id"])
    op.create_index("ix_tournament_participants_student_id", "tournament_participants",
                    ["student_id"])
    op.create_table(
        "tournament_matches", pk(),
        sa.Column("tournament_id", sa.Integer(), sa.ForeignKey("tournaments.id"), nullable=False),
        sa.Column("round_name", sa.String(60), nullable=False),
        sa.Column("participant_a_id", sa.Integer(),
                  sa.ForeignKey("tournament_participants.id"), nullable=False),
        sa.Column("participant_b_id", sa.Integer(),
                  sa.ForeignKey("tournament_participants.id"), nullable=False),
        sa.Column("score_a", sa.SmallInteger(), nullable=False),
        sa.Column("score_b", sa.SmallInteger(), nullable=False),
        sa.Column("winner_id", sa.Integer(), sa.ForeignKey("tournament_participants.id")),
        created(),
        sa.CheckConstraint("participant_a_id <> participant_b_id", name="distinct_players"),
        sa.CheckConstraint("score_a >= 0 AND score_b >= 0", name="scores"),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_tournament_matches_tournament_id", "tournament_matches", ["tournament_id"])
    op.create_table(
        "audit_logs", pk(),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("users.id")),
        sa.Column("action", sa.String(60), nullable=False),
        sa.Column("entity", sa.String(60), nullable=False),
        sa.Column("entity_id", sa.Integer()),
        sa.Column("detail", sa.String(500)),
        created(),
        mysql_engine="InnoDB", mysql_charset="utf8mb4", mysql_collate="utf8mb4_unicode_ci",
    )
    op.create_index("ix_audit_logs_created", "audit_logs", ["created_at"])


def downgrade() -> None:
    """Elimina TODO el esquema (y por tanto todos los datos). Solo para entornos de desarrollo."""
    for table in (
        "audit_logs", "tournament_matches", "tournament_participants", "tournaments",
        "progress_records", "attendances", "class_enrollments", "classes", "reservations",
        "maintenance_blocks", "tables", "facilities", "coaches", "students", "users",
    ):
        op.drop_table(table)
