import os
import psycopg2
from psycopg2.extensions import ISOLATION_LEVEL_AUTOCOMMIT
from psycopg2 import errors

# create connection
constr = "user='%s' host='%s' password='%s'" %(os.environ['POSTGRES_USER'], os.environ['POSTGRES_HOST'], os.environ['POSTGRES_PASSWORD'])
conn = psycopg2.connect(constr)

# can't create databases in a transaction
conn.set_isolation_level(ISOLATION_LEVEL_AUTOCOMMIT);
cur = conn.cursor()

# create database if it doesn't exist
try:
    cur.execute("CREATE DATABASE %s;" % (os.environ['POSTGRES_DB']))
except errors.DuplicateDatabase:
    pass  #exists
 
cur.close()
conn.close()
