#!/bin/bash

rm -rf ../schema2rest/src/server_generic_files
mkdir -p ../schema2rest/src/server_generic_files

mkdir -p ../schema2rest/src/server_generic_files/config
cp mongo.json ../schema2rest/src/server_generic_files/config
cp es.json ../schema2rest/src/server_generic_files/config
cp sqlite.json ../schema2rest/src/server_generic_files/config
cp postgres.json ../schema2rest/src/server_generic_files/config

# base infrastructure files
cp Makefile ../schema2rest/src/server_generic_files
cp requirements.txt ../schema2rest/src/server_generic_files

# base app files - main.py is generated so don't store it
cp app/*.py ../schema2rest/src/server_generic_files
rm ../schema2rest/src/server_generic_files/main.py

# mcp files
cp -r app/mcp ../schema2rest/src/server_generic_files

# db, services, core and routers
cp -r app/db ../schema2rest/src/server_generic_files
cp -r app/routers ../schema2rest/src/server_generic_files
cp -r app/core ../schema2rest/src/server_generic_files
cp -r app/services ../schema2rest/src/server_generic_files

# test framework
cp -r validate/app-src ../schema2rest/src/server_generic_files/validate

# cleanup pycache
find ../schema2rest/src/server_generic_files -name '__pycache__' -exec rm -rf {} \;

# ls the files
ls ../schema2rest/src/server_generic_files
ls ../schema2rest/src/server_generic_files/db
ls ../schema2rest/src/server_generic_files/routers
ls ../schema2rest/src/server_generic_files/services
#ls ../schema2rest/src/server_generic_files/models

# show tree of the files
tree ../schema2rest/src/server_generic_files
