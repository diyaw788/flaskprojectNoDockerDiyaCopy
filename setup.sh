#!/bin/bash

# Update package manager and install dependencies
apt-get update
apt-get install -y curl apt-transport-https gnupg2 unixodbc unixodbc-dev build-essential gcc g++

# Add Microsoft SQL Server ODBC driver repository
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/20.04/prod.list > /etc/apt/sources.list.d/mssql-release.list

# Install Microsoft ODBC Driver 18 for SQL Server
ACCEPT_EULA=Y apt-get update
ACCEPT_EULA=Y apt-get install -y msodbcsql18
