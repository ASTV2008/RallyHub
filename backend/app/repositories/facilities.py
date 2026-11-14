from __future__ import annotations

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import joinedload

from app.models import ClassSession, Facility, GameTable, MaintenanceBlock, Reservation
from app.models.enums import ClassStatus, ReservationStatus, TableStatus
from app.repositories.base import BaseRepository, apply_sort, like_pattern


class FacilityRepository(BaseRepository[Facility]):
    model = Facility

    SORTABLE = {"name": Facility.name, "created_at": Facility.created_at}

    def by_name(self, name: str) -> Facility | None:
        return self.db.scalar(select(Facility).where(Facility.name == name))

    def search(self, *, q, is_active, sort_by, order, limit, offset):
        stmt = select(Facility)
        if q:
            stmt = stmt.where(Facility.name.ilike(like_pattern(q), escape="\\"))
        if is_active is not None:
            stmt = stmt.where(Facility.is_active == is_active)
        stmt = apply_sort(stmt, self.SORTABLE, sort_by, order, "name", Facility.id)
        return self.paginate(stmt, limit, offset)


class TableRepository(BaseRepository[GameTable]):
    model = GameTable

    SORTABLE = {"code": GameTable.code, "status": GameTable.status,
                "created_at": GameTable.created_at}

    def get_full(self, table_id: int) -> GameTable | None:
        return self.db.scalar(
            select(GameTable).options(joinedload(GameTable.facility))
            .where(GameTable.id == table_id)
        )

    def get_for_update(self, table_id: int) -> GameTable | None:
        """Bloquea la fila de la mesa (SELECT ... FOR UPDATE) hasta el fin de la transacción.

        Es la sección crítica que serializa reservas/clases sobre la misma mesa.
        Sin JOINs: así solo se bloquea la fila de `tables`.
        """
        return self.db.scalar(
            select(GameTable).where(GameTable.id == table_id).with_for_update()
        )

    def by_code(self, facility_id: int, code: str) -> GameTable | None:
        return self.db.scalar(
            select(GameTable).where(GameTable.facility_id == facility_id, GameTable.code == code)
        )

    def search(self, *, facility_id, status, q, sort_by, order, limit, offset):
        stmt = select(GameTable).options(joinedload(GameTable.facility))
        if facility_id is not None:
            stmt = stmt.where(GameTable.facility_id == facility_id)
        if status:
            stmt = stmt.where(GameTable.status == status)
        if q:
            stmt = stmt.where(GameTable.code.ilike(like_pattern(q), escape="\\"))
        stmt = apply_sort(stmt, self.SORTABLE, sort_by, order, "code", GameTable.id)
        return self.paginate(stmt, limit, offset)

    def bookable_tables(self, facility_id: int | None) -> list[GameTable]:
        stmt = (select(GameTable).join(GameTable.facility).options(joinedload(GameTable.facility))
                .where(GameTable.status == TableStatus.ACTIVE, Facility.is_active.is_(True))
                .order_by(Facility.name, GameTable.code))
        if facility_id is not None:
            stmt = stmt.where(GameTable.facility_id == facility_id)
        return list(self.db.scalars(stmt).unique().all())

    # --- agenda de una mesa ------------------------------------------------------------------
    def busy_slots(self, table_ids: list[int], start: datetime, end: datetime, *,
                   exclude_class_id: int | None = None
                   ) -> list[tuple[int, str, datetime, datetime]]:
        """Intervalos ocupados (mesa, tipo, inicio, fin) que se solapan con [start, end).

        Condición de solapamiento: existing_start < new_end AND existing_end > new_start.
        Se consultan tres fuentes: reservas no canceladas, clases no canceladas y
        bloqueos de mantenimiento. Una consulta por fuente (no por mesa).
        """
        if not table_ids:
            return []
        out: list[tuple[int, str, datetime, datetime]] = []
        res = self.db.execute(
            select(Reservation.table_id, Reservation.starts_at, Reservation.ends_at).where(
                Reservation.table_id.in_(table_ids),
                Reservation.status != ReservationStatus.CANCELLED,
                Reservation.starts_at < end,
                Reservation.ends_at > start,
            )
        )
        out += [(t, "RESERVATION", s, e) for t, s, e in res]
        cls_stmt = select(ClassSession.table_id, ClassSession.starts_at, ClassSession.ends_at).where(
            ClassSession.table_id.in_(table_ids),
            ClassSession.status != ClassStatus.CANCELLED,
            ClassSession.starts_at < end,
            ClassSession.ends_at > start,
        )
        if exclude_class_id is not None:
            cls_stmt = cls_stmt.where(ClassSession.id != exclude_class_id)
        out += [(t, "CLASS", s, e) for t, s, e in self.db.execute(cls_stmt)]
        mnt = self.db.execute(
            select(MaintenanceBlock.table_id, MaintenanceBlock.starts_at,
                   MaintenanceBlock.ends_at).where(
                MaintenanceBlock.table_id.in_(table_ids),
                MaintenanceBlock.starts_at < end,
                MaintenanceBlock.ends_at > start,
            )
        )
        out += [(t, "MAINTENANCE", s, e) for t, s, e in mnt]
        return out

    def maintenance_for(self, table_id: int) -> list[MaintenanceBlock]:
        return list(self.db.scalars(
            select(MaintenanceBlock).where(MaintenanceBlock.table_id == table_id)
            .order_by(MaintenanceBlock.starts_at.desc())
        ))

    def reservations_overlapping(self, table_ids: list[int], start: datetime, end: datetime
                                 ) -> list[Reservation]:
        """Reservas no canceladas que se solapan con [start, end) (para mantenimiento)."""
        if not table_ids:
            return []
        return list(self.db.scalars(
            select(Reservation).where(
                Reservation.table_id.in_(table_ids),
                Reservation.status != ReservationStatus.CANCELLED,
                Reservation.starts_at < end,
                Reservation.ends_at > start,
            ).order_by(Reservation.starts_at)
        ))

    def future_confirmed_reservations(self, table_ids: list[int], now: datetime
                                      ) -> list[Reservation]:
        """Reservas CONFIRMED que aún no terminaron (las afectadas si la mesa deja de servir)."""
        if not table_ids:
            return []
        return list(self.db.scalars(
            select(Reservation).where(
                Reservation.table_id.in_(table_ids),
                Reservation.status == ReservationStatus.CONFIRMED,
                Reservation.ends_at > now,
            ).order_by(Reservation.starts_at)
        ))

    def future_classes(self, table_ids: list[int], now: datetime) -> list[ClassSession]:
        """Clases no canceladas que aún no terminaron en esas mesas."""
        if not table_ids:
            return []
        return list(self.db.scalars(
            select(ClassSession).where(
                ClassSession.table_id.in_(table_ids),
                ClassSession.status != ClassStatus.CANCELLED,
                ClassSession.ends_at > now,
            ).order_by(ClassSession.starts_at)
        ))
