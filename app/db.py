import sqlite3, threading, time
from . import config

_local = threading.local()
SCHEMA = """
CREATE TABLE IF NOT EXISTS owners(id INTEGER PRIMARY KEY, email TEXT UNIQUE NOT NULL, pw_hash TEXT NOT NULL, created REAL);
CREATE TABLE IF NOT EXISTS hooqs(id INTEGER PRIMARY KEY, owner_id INTEGER NOT NULL, url TEXT NOT NULL, name TEXT, slug TEXT UNIQUE,
  template TEXT DEFAULT 'v7', status TEXT DEFAULT 'queued', step INTEGER DEFAULT 0, steps INTEGER DEFAULT 0, step_label TEXT,
  error TEXT, cost_p REAL DEFAULT 0, booking_url TEXT, published INTEGER DEFAULT 0, created REAL, started REAL, finished REAL, kind TEXT DEFAULT 'build');
CREATE TABLE IF NOT EXISTS leads(id INTEGER PRIMARY KEY, hooq_id INTEGER NOT NULL, created REAL, name TEXT, phone TEXT, email TEXT,
  postcode TEXT, job TEXT, price TEXT, brief TEXT, answers TEXT, action TEXT, action_detail TEXT, emailed INTEGER DEFAULT 0);
CREATE TABLE IF NOT EXISTS checkout_interest(id INTEGER PRIMARY KEY, hooq_id INTEGER NOT NULL, owner_id INTEGER NOT NULL, url TEXT, created REAL);
"""


def conn():
    c = getattr(_local, "c", None)
    if c is None:
        c = sqlite3.connect(config.DATA / "hooqed.db", timeout=30)
        c.row_factory = sqlite3.Row
        c.execute("PRAGMA journal_mode=WAL")
        c.executescript(SCHEMA)
        _local.c = c
    return c


def q(sql, *a):
    return conn().execute(sql, a).fetchall()


def one(sql, *a):
    return conn().execute(sql, a).fetchone()


def run(sql, *a):
    c = conn(); cur = c.execute(sql, a); c.commit(); return cur.lastrowid


def now():
    return time.time()
