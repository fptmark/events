#!/bin/bash
echo ' Server is only needed to run the script curl.sh'
rm results.json
python tests/comprehensive_test.py --verbose --curl 
tests/curl.sh > results.json
python tests/comprehensive_test.py --verbose --curl results.json --config mongo.json
