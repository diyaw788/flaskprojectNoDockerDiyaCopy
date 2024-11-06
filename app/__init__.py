# -*- encoding: utf-8 -*-
"""
Copyright (c) 2019 - present AppSeed.us
"""

# Import core packages
import os

# Import Flask 
from flask import Flask
# import pymysql
import pyodbc

# Inject Flask magic
app = Flask(__name__)
app.secret_key = "12345678abcdefg"

# Connection details
server = 'peer-eval-db.cfse6cicm7dq.us-east-1.rds.amazonaws.com,1433'
database = 'peer-eval-db'
username = 'admin'
password = 'businessSeminar2025'
driver = '{ODBC Driver 18 for SQL Server}'


conn = pyodbc.connect(
    f'DRIVER={driver};SERVER={server};PORT=1433;DATABASE={database};UID={username};PWD={password};TrustServerCertificate=yes'
)

cursor=conn.cursor()


# dbConn = pymysql.connect(
#     host="office.scholars.bond",
#     port=3309,
#     user='bit4444group20',
#     password='CGw7f2[?4/mx',
#     database='bit4444group20',
#     cursorclass=pymysql.cursors.DictCursor
# )

# cursor=dbConn.cursor()


# Import routing to render the pages
from app import views
