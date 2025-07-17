#!/bin/bash
cp Makefile ../schema2rest/src/server_generic_files

cp app/*.py ../schema2rest/src/server_generic_files
rm ../schema2rest/src/server_generic_files/main.py

cp -r app/db ../schema2rest/src/server_generic_files
cp -r app/routers ../schema2rest/src/server_generic_files

find ../schema2rest/src/server_generic_files -name '__pycache__' -exec rm -rf {} \;
ls ../schema2rest/src/server_generic_files
ls ../schema2rest/src/server_generic_files/db
ls ../schema2rest/src/server_generic_files/routers
tree ../schema2rest/src/server_generic_files
