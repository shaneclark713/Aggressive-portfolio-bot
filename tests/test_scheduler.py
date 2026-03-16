from core.scheduler import build_scheduler

def test_build_scheduler(): assert build_scheduler('America/Phoenix') is not None
