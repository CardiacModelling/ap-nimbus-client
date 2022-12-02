import os

import psycopg2
from psycopg2 import errors
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT


# create connection
conn = psycopg2.connect(database='postgres',
                        user=os.environ['PGUSER'],
                        password=os.environ['PGPASSWORD'],
                        host=os.environ['PGHOST'],
                        port=os.environ['PGPORT'])

# can't create databases in a transaction
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT)
cur = conn.cursor()

# create database if it doesn't exist
try:
    cur.execute("CREATE DATABASE %s;" % (os.environ['PGDATABASE']))
except errors.DuplicateDatabase:
    pass  # exists

cur.close()
conn.close()