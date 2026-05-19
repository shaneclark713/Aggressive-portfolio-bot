# database/ecosystem_state_repository.py

from __future__ import annotations
import json
from datetime import datetime


def record_ecosystem_state(conn, payload, source="spy_0dte"):
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO ecosystem_state (
            created_at,
            source,
            payload
        )
        VALUES (?, ?, ?)
        """,
        (
            datetime.utcnow().isoformat(),
            source,
            json.dumps(payload, default=str),
        ),
    )

    conn.commit()
