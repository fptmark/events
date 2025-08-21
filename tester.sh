#!/bin/bash
if [ $# -eq 0 ]; then
   echo "must specify es or mongo"
   exit 2
fi

echo ' Server is only needed to run the script curl.sh'
rm results.json
python tests/comprehensive_test.py --verbose --curl 
tests/curl.sh > results.json
python tests/comprehensive_test.py --verbose --curl results.json --config $1.json

