import os
import sys
import threading
import time
import uuid

from sqlalchemy import create_engine, event, Column, String
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy.pool import StaticPool, QueuePool

Base = declarative_base()


class Item(Base):
    __tablename__ = "items"
    id = Column(String, primary_key=True)
    name = Column(String)


def make_engine(poolclass, db_path):
    kwargs = dict(connect_args={"check_same_thread": False, "timeout": 30})
    if poolclass is not None:
        kwargs["poolclass"] = poolclass
    engine = create_engine(f"sqlite:///{db_path}", echo=False, **kwargs)

    @event.listens_for(engine, "connect")
    def set_pragma(dbapi_connection, connection_record):
        cur = dbapi_connection.cursor()
        cur.execute("PRAGMA journal_mode=WAL")
        cur.execute("PRAGMA synchronous=NORMAL")
        cur.close()

    Base.metadata.create_all(engine)
    return engine


def run_trial(poolclass, label):
    db_path = f"_tmp_repro_{label}.db"
    for ext in ("", "-wal", "-shm"):
        p = db_path + ext
        if os.path.exists(p):
            os.remove(p)

    engine = make_engine(poolclass, db_path)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

    errors = []

    # Mimic app_controller's long-lived session: it flushes a pending row, does a
    # tiny bit of "work", then commits promptly -- like a normal UI-triggered save.
    long_lived = SessionLocal()

    def long_lived_cycle():
        for _ in range(20):
            long_lived.add(Item(id=str(uuid.uuid4()), name="main-session-row"))
            long_lived.flush()
            time.sleep(0.01)
            long_lived.commit()

    def worker():
        try:
            for _ in range(5):
                with SessionLocal() as session:
                    entity = Item(id=str(uuid.uuid4()), name="worker-message")
                    session.add(entity)
                    session.commit()
                    session.refresh(entity)
        except Exception as e:
            errors.append(repr(e))

    threads = [threading.Thread(target=worker) for _ in range(8)]
    threads.append(threading.Thread(target=long_lived_cycle))
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    long_lived.close()
    engine.dispose()

    for ext in ("", "-wal", "-shm"):
        p = db_path + ext
        if os.path.exists(p):
            os.remove(p)

    print(f"[{label}] errors: {len(errors)}/{len(threads)}")
    for e in errors[:3]:
        print(f"    {e}")
    return errors


print("=== StaticPool (old, buggy config) ===")
run_trial(StaticPool, "staticpool")

print("=== QueuePool (new, fixed config) ===")
run_trial(QueuePool, "queuepool")
