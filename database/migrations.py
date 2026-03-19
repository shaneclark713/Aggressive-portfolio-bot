from typing import Optional
from database.db import init_db


def run_migrations(db_path: Optional[str] = None) -> None:
    init_db(db_path)
