#!/bin/bash
# Generated curl commands from test execution
# Run: chmod +x curl.sh && ./curl.sh

echo "=== GET http://127.0.0.1:5500/api/user?page=0&pageSize=10 ==="
curl -X GET "http://127.0.0.1:5500/api/user?page=0&pageSize=10"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?filter=username:nonexistentuser12345 ==="
curl -X GET "http://127.0.0.1:5500/api/user?filter=username:nonexistentuser12345"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?page=2&pageSize=15 ==="
curl -X GET "http://127.0.0.1:5500/api/user?page=2&pageSize=15"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?sort=username&order=asc&pageSize=5 ==="
curl -X GET "http://127.0.0.1:5500/api/user?sort=username&order=asc&pageSize=5"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?filter=isAccountOwner:true&pageSize=10 ==="
curl -X GET "http://127.0.0.1:5500/api/user?filter=isAccountOwner:true&pageSize=10"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?filter=username:test&pageSize=10 ==="
curl -X GET "http://127.0.0.1:5500/api/user?filter=username:test&pageSize=10"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?filter=netWorth:range:[1000:50000]&pageSize=10 ==="
curl -X GET "http://127.0.0.1:5500/api/user?filter=netWorth:range:[1000:50000]&pageSize=10"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?filter=gender:male,isAccountOwner:true,netWorth:range:[1000:]&pageSize=5 ==="
curl -X GET "http://127.0.0.1:5500/api/user?filter=gender:male,isAccountOwner:true,netWorth:range:[1000:]&pageSize=5"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?filter=gender:male&page=1&pageSize=5 ==="
curl -X GET "http://127.0.0.1:5500/api/user?filter=gender:male&page=1&pageSize=5"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?filter=gender:male&page=2&pageSize=5 ==="
curl -X GET "http://127.0.0.1:5500/api/user?filter=gender:male&page=2&pageSize=5"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?view={"account":["createdAt"]}&pageSize=5 ==="
curl -X GET "http://127.0.0.1:5500/api/user?view=%7B%22account%22%3A%5B%22createdAt%22%5D%7D&pageSize=5"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?view={"account":["createdAt","updatedAt"]}&pageSize=3 ==="
curl -X GET "http://127.0.0.1:5500/api/user?view=%7B%22account%22%3A%5B%22createdAt%22%2C%22updatedAt%22%5D%7D&pageSize=3"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?view={"account":["createdAt"]}&page=1&pageSize=5 ==="
curl -X GET "http://127.0.0.1:5500/api/user?view=%7B%22account%22%3A%5B%22createdAt%22%5D%7D&page=1&pageSize=5"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?view={"account":["createdAt"]}&filter=gender:male&pageSize=5 ==="
curl -X GET "http://127.0.0.1:5500/api/user?view=%7B%22account%22%3A%5B%22createdAt%22%5D%7D&filter=gender:male&pageSize=5"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?view={"account":["createdAt"]}&sort=username&order=asc&pageSize=5 ==="
curl -X GET "http://127.0.0.1:5500/api/user?view=%7B%22account%22%3A%5B%22createdAt%22%5D%7D&sort=username&order=asc&pageSize=5"
echo ""

echo "=== GET http://127.0.0.1:5500/api/user?view={"account":["createdAt"]}&filter=gender:male&sort=username&order=desc&page=1&pageSize=3 ==="
curl -X GET "http://127.0.0.1:5500/api/user?view=%7B%22account%22%3A%5B%22createdAt%22%5D%7D&filter=gender:male&sort=username&order=desc&page=1&pageSize=3"
echo ""

