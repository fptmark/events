#!/bin/bash

# base infrastructure files
cp Makefile ../schema2rest/src/server_generic_files
cp requirements.txt ../schema2rest/src/server_generic_files

# base app files
cp app/*.py ../schema2rest/src/server_generic_files
rm ../schema2rest/src/server_generic_files/main.py

# db, services and router are app independent
cp -r app/db ../schema2rest/src/server_generic_files
cp -r app/routers ../schema2rest/src/server_generic_files
cp -r app/services ../schema2rest/src/server_generic_files

# model files that are app independend
cp -r app/models/utils.py ../schema2rest/src/server_generic_files/models

# cleanup pycache
find ../schema2rest/src/server_generic_files -name '__pycache__' -exec rm -rf {} \;

# ls the files
ls ../schema2rest/src/server_generic_files
ls ../schema2rest/src/server_generic_files/db
ls ../schema2rest/src/server_generic_files/routers
ls ../schema2rest/src/server_generic_files/services
ls ../schema2rest/src/server_generic_files/models

# show tree of the files
tree ../schema2rest/src/server_generic_files
