#!/bin/bash
# Update the package list and install prerequisites
apt-get update && apt-get install -y curl apt-transport-https gnupg2

# Add the Microsoft repository for the ODBC driver
curl https://packages.microsoft.com/keys/microsoft.asc | apt-key add -
curl https://packages.microsoft.com/config/ubuntu/$(lsb_release -rs)/prod.list | tee /etc/apt/sources.list.d/mssql-release.list

# Install the Microsoft ODBC Driver 18 for SQL Server
apt-get update && ACCEPT_EULA=Y apt-get install -y msodbcsql18 unixodbc-dev

# Clean up
apt-get clean
