#!/bin/bash
rm results.json
python tests/comprehensive_test.py --verbose --curl 
python tests/comprehensive_test.py --verbose --newdata-only  --config mongo.json
tests/curl.sh > results.json
python tests/comprehensive_test.py --verbose --curl results.json --config mongo.json
