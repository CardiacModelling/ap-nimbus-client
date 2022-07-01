import os

import psycopg2
from psycopg2 import errors
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


# create connection
vars = os.environ['PGUSER'], os.environ['PGHOST'], os.environ['PGPASSWORD']
constr = "user='%s' host='%s' password='%s'" % vars
conn = psycopg2.connect(constr)

# can't create databases in a transaction
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

# create database if it doesn't exist
try:
    cur.execute("CREATE DATABASE %s;" % (os.environ['POSTGRES_PASSWORD']))
except errors.DuplicateDatabase:
    pass  # exists

cur.close()
conn.close()
