from os import PathLike
from pathlib import Path
from typing import Optional, Union

from database.db import init_db

PathInput = Optional[Union[str, PathLike[str], Path]]


def run_migrations(db_path: PathInput = None) -> None:
    init_db(db_path)
