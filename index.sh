#!/bin/sh
if [ ! -f config.json ]; then
  echo "config.json not found"
  exit 1
fi
MONGO_URI=$(jq -r '.mongo_uri' config.json)
DB_NAME=$(jq -r '.db_name' config.json)


mongo $MONGO_URI/$DB_NAME --eval 'db.user.createIndex({"username": 1}, {unique:true})'


mongo $MONGO_URI/$DB_NAME --eval 'db.user.createIndex({"email": 1}, {unique:true})'


mongo $MONGO_URI/$DB_NAME --eval 'db.profile.createIndex({"name": 1, "userId": 1}, {unique:true})'


mongo $MONGO_URI/$DB_NAME --eval 'db.tagaffinity.createIndex({"profileId": 1, "tag": 1}, {unique:true})'

