#!/bin/bash
# Generated curl commands from comprehensive test execution
# Run: chmod +x tests/curl.sh && ./tests/curl.sh

# 12:41:45.776 - Request #1
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456"
echo ""

# 12:41:45.798 - Request #2
echo "=== GET http://localhost:5500/api/user/bad_enum_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_enum_user_123456"
echo ""

# 12:41:45.803 - Request #3
echo "=== GET http://localhost:5500/api/user/bad_currency_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_currency_user_123456"
echo ""

# 12:41:45.808 - Request #4
echo "=== GET http://localhost:5500/api/user/bad_fk_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_fk_user_123456"
echo ""

# 12:41:45.817 - Request #5
echo "=== GET http://localhost:5500/api/user/multiple_errors_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/multiple_errors_user_123456"
echo ""

# 12:41:45.821 - Request #6
echo "=== GET http://localhost:5500/api/user/nonexistent_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/nonexistent_user_123456"
echo ""

# 12:41:45.831 - Request #7
echo "=== GET http://localhost:5500/api/user ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user"
echo ""

# 12:41:45.886 - Request #8
echo "=== GET http://localhost:5500/api/user?pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3"
echo ""

# 12:41:48.906 - Request #9
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:41:48.922 - Request #10
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["id","createdAt","expiredAt"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D"
echo ""

# 12:41:48.936 - Request #11
echo "=== GET http://localhost:5500/api/user/bad_fk_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_fk_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:41:48.947 - Request #12
echo "=== GET http://localhost:5500/api/user/multiple_errors_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/multiple_errors_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:41:48.960 - Request #13
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["nonexistent_field"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22nonexistent_field%22%5D%7D"
echo ""

# 12:41:48.969 - Request #14
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:41:49.107 - Request #15
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt","expiredAt"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D"
echo ""

# 12:41:49.165 - Request #16
echo "=== GET http://localhost:5500/api/user?pageSize=3&view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3&view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:41:52.194 - Request #17
echo "=== GET http://localhost:5500/api/user ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user"
echo ""

# 12:41:52.321 - Request #18
echo "=== GET http://localhost:5500/api/user?pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3"
echo ""

# 12:41:52.349 - Request #19
echo "=== GET http://localhost:5500/api/user?page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=1&pageSize=5"
echo ""

# 12:41:52.376 - Request #20
echo "=== GET http://localhost:5500/api/user?page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=2&pageSize=3"
echo ""

# 12:41:52.395 - Request #21
echo "=== GET http://localhost:5500/api/user?page=0&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=0&pageSize=5"
echo ""

# 12:41:52.415 - Request #22
echo "=== GET http://localhost:5500/api/user?pageSize=1000 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=1000"
echo ""

# 12:41:53.471 - Request #23
echo "=== GET http://localhost:5500/api/user?page=999&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=999&pageSize=5"
echo ""

# 12:41:53.479 - Request #24
echo "=== GET http://localhost:5500/api/user?pageSize=0 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=0"
echo ""

# 12:41:53.564 - Request #25
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456"
echo ""

# 12:41:53.571 - Request #26
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?page=2&pageSize=10 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?page=2&pageSize=10"
echo ""

# 12:41:56.591 - Request #27
echo "=== GET http://localhost:5500/api/user?sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username"
echo ""

# 12:41:56.744 - Request #28
echo "=== GET http://localhost:5500/api/user?sort=-username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-username"
echo ""

# 12:41:56.859 - Request #29
echo "=== GET http://localhost:5500/api/user?sort=createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=createdAt"
echo ""

# 12:41:56.954 - Request #30
echo "=== GET http://localhost:5500/api/user?sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt"
echo ""

# 12:41:57.042 - Request #31
echo "=== GET http://localhost:5500/api/user?sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName,lastName"
echo ""

# 12:41:57.154 - Request #32
echo "=== GET http://localhost:5500/api/user?sort=firstName,-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName,-createdAt"
echo ""

# 12:41:57.284 - Request #33
echo "=== GET http://localhost:5500/api/user?sort=-lastName,firstName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-lastName,firstName"
echo ""

# 12:41:57.400 - Request #34
echo "=== GET http://localhost:5500/api/user?sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username&pageSize=3"
echo ""

# 12:41:57.427 - Request #35
echo "=== GET http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:41:57.450 - Request #36
echo "=== GET http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3"
echo ""

# 12:41:57.476 - Request #37
echo "=== GET http://localhost:5500/api/user?sort=nonexistentfield ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=nonexistentfield"
echo ""

# 12:41:57.496 - Request #38
echo "=== GET http://localhost:5500/api/user?sort= ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort="
echo ""

# 12:41:57.615 - Request #39
echo "=== GET http://localhost:5500/api/user?sort=- ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-"
echo ""

# 12:41:57.749 - Request #40
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?sort=username"
echo ""

# 12:41:57.755 - Request #41
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?sort=-createdAt,firstName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?sort=-createdAt,firstName"
echo ""

# 12:42:00.771 - Request #42
echo "=== GET http://localhost:5500/api/user?filter=gender:male ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male"
echo ""

# 12:42:00.888 - Request #43
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true"
echo ""

# 12:42:01.016 - Request #44
echo "=== GET http://localhost:5500/api/user?filter=username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=username:valid_all_user_123456"
echo ""

# 12:42:01.035 - Request #45
echo "=== GET http://localhost:5500/api/user?filter=username:nonexistent_user_12345 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=username:nonexistent_user_12345"
echo ""

# 12:42:01.047 - Request #46
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:true"
echo ""

# 12:42:01.139 - Request #47
echo "=== GET http://localhost:5500/api/user?filter=gender:female,isAccountOwner:false ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:female,isAccountOwner:false"
echo ""

# 12:42:01.260 - Request #48
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true,username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true,username:valid_all_user_123456"
echo ""

# 12:42:01.274 - Request #49
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3"
echo ""

# 12:42:01.292 - Request #50
echo "=== GET http://localhost:5500/api/user?filter=gender:male&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male&page=1&pageSize=5"
echo ""

# 12:42:01.329 - Request #51
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3"
echo ""

# 12:42:01.355 - Request #52
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username"
echo ""

# 12:42:01.492 - Request #53
echo "=== GET http://localhost:5500/api/user?filter=gender:male&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male&sort=-createdAt"
echo ""

# 12:42:01.621 - Request #54
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName"
echo ""

# 12:42:01.755 - Request #55
echo "=== GET http://localhost:5500/api/user?filter=nonexistentfield:value ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=nonexistentfield:value"
echo ""

# 12:42:01.769 - Request #56
echo "=== GET http://localhost:5500/api/user?filter=invalidformat ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=invalidformat"
echo ""

# 12:42:01.906 - Request #57
echo "=== GET http://localhost:5500/api/user?filter= ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter="
echo ""

# 12:42:02.034 - Request #58
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male"
echo ""

# 12:42:02.046 - Request #59
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male,isAccountOwner:true"
echo ""

# 12:42:05.066 - Request #60
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&pageSize=3"
echo ""

# 12:42:05.102 - Request #61
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&page=1&pageSize=5"
echo ""

# 12:42:05.143 - Request #62
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&page=2&pageSize=3"
echo ""

# 12:42:05.165 - Request #63
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=username"
echo ""

# 12:42:05.291 - Request #64
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&sort=-createdAt"
echo ""

# 12:42:05.412 - Request #65
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=firstName,lastName"
echo ""

# 12:42:05.545 - Request #66
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true"
echo ""

# 12:42:05.618 - Request #67
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male,isAccountOwner:true"
echo ""

# 12:42:05.682 - Request #68
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=username:valid_all_user_123456"
echo ""

# 12:42:05.692 - Request #69
echo "=== GET http://localhost:5500/api/user?sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username&pageSize=3"
echo ""

# 12:42:05.706 - Request #70
echo "=== GET http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:42:05.718 - Request #71
echo "=== GET http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3"
echo ""

# 12:42:05.733 - Request #72
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3"
echo ""

# 12:42:05.745 - Request #73
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&page=1&pageSize=5"
echo ""

# 12:42:05.753 - Request #74
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3"
echo ""

# 12:42:05.765 - Request #75
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username"
echo ""

# 12:42:05.819 - Request #76
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&sort=-createdAt"
echo ""

# 12:42:05.825 - Request #77
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName"
echo ""

# 12:42:05.865 - Request #78
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=isAccountOwner:true&sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true&sort=username&pageSize=3"
echo ""

# 12:42:05.875 - Request #79
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&filter=gender:male&sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male&sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:42:05.885 - Request #80
echo "=== GET http://localhost:5500/api/user?view={"account":["id","expiredAt"]}&filter=isAccountOwner:false,gender:female&sort=firstName,lastName&page=1&pageSize=10 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22expiredAt%22%5D%7D&filter=isAccountOwner:false,gender:female&sort=firstName,lastName&page=1&pageSize=10"
echo ""

# 12:42:18.222 - Request #81
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456"
echo ""

# 12:42:18.238 - Request #82
echo "=== GET http://localhost:5500/api/user/bad_enum_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_enum_user_123456"
echo ""

# 12:42:18.244 - Request #83
echo "=== GET http://localhost:5500/api/user/bad_currency_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_currency_user_123456"
echo ""

# 12:42:18.250 - Request #84
echo "=== GET http://localhost:5500/api/user/bad_fk_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_fk_user_123456"
echo ""

# 12:42:18.261 - Request #85
echo "=== GET http://localhost:5500/api/user/multiple_errors_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/multiple_errors_user_123456"
echo ""

# 12:42:18.267 - Request #86
echo "=== GET http://localhost:5500/api/user/nonexistent_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/nonexistent_user_123456"
echo ""

# 12:42:18.286 - Request #87
echo "=== GET http://localhost:5500/api/user ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user"
echo ""

# 12:42:18.340 - Request #88
echo "=== GET http://localhost:5500/api/user?pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3"
echo ""

# 12:42:21.358 - Request #89
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:42:21.367 - Request #90
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["id","createdAt","expiredAt"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D"
echo ""

# 12:42:21.377 - Request #91
echo "=== GET http://localhost:5500/api/user/bad_fk_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_fk_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:42:21.389 - Request #92
echo "=== GET http://localhost:5500/api/user/multiple_errors_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/multiple_errors_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:42:21.401 - Request #93
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["nonexistent_field"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22nonexistent_field%22%5D%7D"
echo ""

# 12:42:21.411 - Request #94
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:42:21.559 - Request #95
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt","expiredAt"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D"
echo ""

# 12:42:21.699 - Request #96
echo "=== GET http://localhost:5500/api/user?pageSize=3&view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3&view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:42:24.729 - Request #97
echo "=== GET http://localhost:5500/api/user ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user"
echo ""

# 12:42:24.875 - Request #98
echo "=== GET http://localhost:5500/api/user?pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3"
echo ""

# 12:42:24.899 - Request #99
echo "=== GET http://localhost:5500/api/user?page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=1&pageSize=5"
echo ""

# 12:42:24.932 - Request #100
echo "=== GET http://localhost:5500/api/user?page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=2&pageSize=3"
echo ""

# 12:42:24.953 - Request #101
echo "=== GET http://localhost:5500/api/user?page=0&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=0&pageSize=5"
echo ""

# 12:42:24.984 - Request #102
echo "=== GET http://localhost:5500/api/user?pageSize=1000 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=1000"
echo ""

# 12:42:26.248 - Request #103
echo "=== GET http://localhost:5500/api/user?page=999&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=999&pageSize=5"
echo ""

# 12:42:26.255 - Request #104
echo "=== GET http://localhost:5500/api/user?pageSize=0 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=0"
echo ""

# 12:42:26.344 - Request #105
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456"
echo ""

# 12:42:26.353 - Request #106
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?page=2&pageSize=10 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?page=2&pageSize=10"
echo ""

# 12:42:29.374 - Request #107
echo "=== GET http://localhost:5500/api/user?sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username"
echo ""

# 12:42:29.482 - Request #108
echo "=== GET http://localhost:5500/api/user?sort=-username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-username"
echo ""

# 12:42:29.610 - Request #109
echo "=== GET http://localhost:5500/api/user?sort=createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=createdAt"
echo ""

# 12:42:29.679 - Request #110
echo "=== GET http://localhost:5500/api/user?sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt"
echo ""

# 12:42:29.725 - Request #111
echo "=== GET http://localhost:5500/api/user?sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName,lastName"
echo ""

# 12:42:29.825 - Request #112
echo "=== GET http://localhost:5500/api/user?sort=firstName,-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName,-createdAt"
echo ""

# 12:42:29.924 - Request #113
echo "=== GET http://localhost:5500/api/user?sort=-lastName,firstName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-lastName,firstName"
echo ""

# 12:42:30.037 - Request #114
echo "=== GET http://localhost:5500/api/user?sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username&pageSize=3"
echo ""

# 12:42:30.058 - Request #115
echo "=== GET http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:42:30.085 - Request #116
echo "=== GET http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3"
echo ""

# 12:42:30.113 - Request #117
echo "=== GET http://localhost:5500/api/user?sort=nonexistentfield ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=nonexistentfield"
echo ""

# 12:42:30.126 - Request #118
echo "=== GET http://localhost:5500/api/user?sort= ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort="
echo ""

# 12:42:30.222 - Request #119
echo "=== GET http://localhost:5500/api/user?sort=- ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-"
echo ""

# 12:42:30.352 - Request #120
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?sort=username"
echo ""

# 12:42:30.362 - Request #121
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?sort=-createdAt,firstName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?sort=-createdAt,firstName"
echo ""

# 12:42:33.378 - Request #122
echo "=== GET http://localhost:5500/api/user?filter=gender:male ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male"
echo ""

# 12:42:33.514 - Request #123
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true"
echo ""

# 12:42:33.652 - Request #124
echo "=== GET http://localhost:5500/api/user?filter=username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=username:valid_all_user_123456"
echo ""

# 12:42:33.664 - Request #125
echo "=== GET http://localhost:5500/api/user?filter=username:nonexistent_user_12345 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=username:nonexistent_user_12345"
echo ""

# 12:42:33.675 - Request #126
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:true"
echo ""

# 12:42:33.778 - Request #127
echo "=== GET http://localhost:5500/api/user?filter=gender:female,isAccountOwner:false ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:female,isAccountOwner:false"
echo ""

# 12:42:33.900 - Request #128
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true,username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true,username:valid_all_user_123456"
echo ""

# 12:42:33.911 - Request #129
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3"
echo ""

# 12:42:33.926 - Request #130
echo "=== GET http://localhost:5500/api/user?filter=gender:male&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male&page=1&pageSize=5"
echo ""

# 12:42:33.938 - Request #131
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3"
echo ""

# 12:42:33.949 - Request #132
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username"
echo ""

# 12:42:34.004 - Request #133
echo "=== GET http://localhost:5500/api/user?filter=gender:male&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male&sort=-createdAt"
echo ""

# 12:42:34.056 - Request #134
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName"
echo ""

# 12:42:34.109 - Request #135
echo "=== GET http://localhost:5500/api/user?filter=nonexistentfield:value ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=nonexistentfield:value"
echo ""

# 12:42:34.115 - Request #136
echo "=== GET http://localhost:5500/api/user?filter=invalidformat ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=invalidformat"
echo ""

# 12:42:34.163 - Request #137
echo "=== GET http://localhost:5500/api/user?filter= ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter="
echo ""

# 12:42:34.207 - Request #138
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male"
echo ""

# 12:42:34.214 - Request #139
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male,isAccountOwner:true"
echo ""

# 12:42:37.230 - Request #140
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&pageSize=3"
echo ""

# 12:42:37.254 - Request #141
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&page=1&pageSize=5"
echo ""

# 12:42:37.284 - Request #142
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&page=2&pageSize=3"
echo ""

# 12:42:37.306 - Request #143
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=username"
echo ""

# 12:42:37.430 - Request #144
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&sort=-createdAt"
echo ""

# 12:42:37.546 - Request #145
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=firstName,lastName"
echo ""

# 12:42:37.682 - Request #146
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true"
echo ""

# 12:42:37.811 - Request #147
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male,isAccountOwner:true"
echo ""

# 12:42:37.871 - Request #148
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=username:valid_all_user_123456"
echo ""

# 12:42:37.881 - Request #149
echo "=== GET http://localhost:5500/api/user?sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username&pageSize=3"
echo ""

# 12:42:37.894 - Request #150
echo "=== GET http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:42:37.907 - Request #151
echo "=== GET http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3"
echo ""

# 12:42:37.916 - Request #152
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3"
echo ""

# 12:42:37.928 - Request #153
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&page=1&pageSize=5"
echo ""

# 12:42:37.935 - Request #154
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3"
echo ""

# 12:42:37.950 - Request #155
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username"
echo ""

# 12:42:38.122 - Request #156
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&sort=-createdAt"
echo ""

# 12:42:38.130 - Request #157
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName"
echo ""

# 12:42:38.198 - Request #158
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=isAccountOwner:true&sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true&sort=username&pageSize=3"
echo ""

# 12:42:38.214 - Request #159
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&filter=gender:male&sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male&sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:42:38.229 - Request #160
echo "=== GET http://localhost:5500/api/user?view={"account":["id","expiredAt"]}&filter=isAccountOwner:false,gender:female&sort=firstName,lastName&page=1&pageSize=10 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22expiredAt%22%5D%7D&filter=isAccountOwner:false,gender:female&sort=firstName,lastName&page=1&pageSize=10"
echo ""

# 12:42:49.973 - Request #161
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456"
echo ""

# 12:42:49.978 - Request #162
echo "=== GET http://localhost:5500/api/user/bad_enum_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_enum_user_123456"
echo ""

# 12:42:49.980 - Request #163
echo "=== GET http://localhost:5500/api/user/bad_currency_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_currency_user_123456"
echo ""

# 12:42:49.982 - Request #164
echo "=== GET http://localhost:5500/api/user/bad_fk_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_fk_user_123456"
echo ""

# 12:42:49.985 - Request #165
echo "=== GET http://localhost:5500/api/user/multiple_errors_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/multiple_errors_user_123456"
echo ""

# 12:42:49.987 - Request #166
echo "=== GET http://localhost:5500/api/user/nonexistent_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/nonexistent_user_123456"
echo ""

# 12:42:49.992 - Request #167
echo "=== GET http://localhost:5500/api/user ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user"
echo ""

# 12:42:50.016 - Request #168
echo "=== GET http://localhost:5500/api/user?pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3"
echo ""

# 12:42:53.029 - Request #169
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:42:53.041 - Request #170
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["id","createdAt","expiredAt"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D"
echo ""

# 12:42:53.053 - Request #171
echo "=== GET http://localhost:5500/api/user/bad_fk_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_fk_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:42:53.063 - Request #172
echo "=== GET http://localhost:5500/api/user/multiple_errors_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/multiple_errors_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:42:53.070 - Request #173
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["nonexistent_field"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22nonexistent_field%22%5D%7D"
echo ""

# 12:42:53.076 - Request #174
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:42:53.195 - Request #175
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt","expiredAt"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D"
echo ""

# 12:42:53.310 - Request #176
echo "=== GET http://localhost:5500/api/user?pageSize=3&view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3&view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:42:56.348 - Request #177
echo "=== GET http://localhost:5500/api/user ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user"
echo ""

# 12:42:56.485 - Request #178
echo "=== GET http://localhost:5500/api/user?pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3"
echo ""

# 12:42:56.512 - Request #179
echo "=== GET http://localhost:5500/api/user?page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=1&pageSize=5"
echo ""

# 12:42:56.545 - Request #180
echo "=== GET http://localhost:5500/api/user?page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=2&pageSize=3"
echo ""

# 12:42:56.570 - Request #181
echo "=== GET http://localhost:5500/api/user?page=0&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=0&pageSize=5"
echo ""

# 12:42:56.606 - Request #182
echo "=== GET http://localhost:5500/api/user?pageSize=1000 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=1000"
echo ""

# 12:42:57.212 - Request #183
echo "=== GET http://localhost:5500/api/user?page=999&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=999&pageSize=5"
echo ""

# 12:42:57.216 - Request #184
echo "=== GET http://localhost:5500/api/user?pageSize=0 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=0"
echo ""

# 12:42:57.240 - Request #185
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456"
echo ""

# 12:42:57.244 - Request #186
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?page=2&pageSize=10 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?page=2&pageSize=10"
echo ""

# 12:43:00.253 - Request #187
echo "=== GET http://localhost:5500/api/user?sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username"
echo ""

# 12:43:00.356 - Request #188
echo "=== GET http://localhost:5500/api/user?sort=-username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-username"
echo ""

# 12:43:00.457 - Request #189
echo "=== GET http://localhost:5500/api/user?sort=createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=createdAt"
echo ""

# 12:43:00.563 - Request #190
echo "=== GET http://localhost:5500/api/user?sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt"
echo ""

# 12:43:00.602 - Request #191
echo "=== GET http://localhost:5500/api/user?sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName,lastName"
echo ""

# 12:43:00.641 - Request #192
echo "=== GET http://localhost:5500/api/user?sort=firstName,-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName,-createdAt"
echo ""

# 12:43:00.699 - Request #193
echo "=== GET http://localhost:5500/api/user?sort=-lastName,firstName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-lastName,firstName"
echo ""

# 12:43:00.736 - Request #194
echo "=== GET http://localhost:5500/api/user?sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username&pageSize=3"
echo ""

# 12:43:00.759 - Request #195
echo "=== GET http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:43:00.773 - Request #196
echo "=== GET http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3"
echo ""

# 12:43:00.787 - Request #197
echo "=== GET http://localhost:5500/api/user?sort=nonexistentfield ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=nonexistentfield"
echo ""

# 12:43:00.796 - Request #198
echo "=== GET http://localhost:5500/api/user?sort= ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort="
echo ""

# 12:43:00.843 - Request #199
echo "=== GET http://localhost:5500/api/user?sort=- ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-"
echo ""

# 12:43:00.949 - Request #200
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?sort=username"
echo ""

# 12:43:00.952 - Request #201
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?sort=-createdAt,firstName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?sort=-createdAt,firstName"
echo ""

# 12:43:03.965 - Request #202
echo "=== GET http://localhost:5500/api/user?filter=gender:male ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male"
echo ""

# 12:43:04.051 - Request #203
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true"
echo ""

# 12:43:04.109 - Request #204
echo "=== GET http://localhost:5500/api/user?filter=username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=username:valid_all_user_123456"
echo ""

# 12:43:04.116 - Request #205
echo "=== GET http://localhost:5500/api/user?filter=username:nonexistent_user_12345 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=username:nonexistent_user_12345"
echo ""

# 12:43:04.122 - Request #206
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:true"
echo ""

# 12:43:04.162 - Request #207
echo "=== GET http://localhost:5500/api/user?filter=gender:female,isAccountOwner:false ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:female,isAccountOwner:false"
echo ""

# 12:43:04.198 - Request #208
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true,username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true,username:valid_all_user_123456"
echo ""

# 12:43:04.203 - Request #209
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3"
echo ""

# 12:43:04.209 - Request #210
echo "=== GET http://localhost:5500/api/user?filter=gender:male&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male&page=1&pageSize=5"
echo ""

# 12:43:04.215 - Request #211
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3"
echo ""

# 12:43:04.220 - Request #212
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username"
echo ""

# 12:43:04.249 - Request #213
echo "=== GET http://localhost:5500/api/user?filter=gender:male&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male&sort=-createdAt"
echo ""

# 12:43:04.278 - Request #214
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName"
echo ""

# 12:43:04.305 - Request #215
echo "=== GET http://localhost:5500/api/user?filter=nonexistentfield:value ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=nonexistentfield:value"
echo ""

# 12:43:04.308 - Request #216
echo "=== GET http://localhost:5500/api/user?filter=invalidformat ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=invalidformat"
echo ""

# 12:43:04.331 - Request #217
echo "=== GET http://localhost:5500/api/user?filter= ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter="
echo ""

# 12:43:04.364 - Request #218
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male"
echo ""

# 12:43:04.367 - Request #219
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male,isAccountOwner:true"
echo ""

# 12:43:07.386 - Request #220
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&pageSize=3"
echo ""

# 12:43:07.419 - Request #221
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&page=1&pageSize=5"
echo ""

# 12:43:07.449 - Request #222
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&page=2&pageSize=3"
echo ""

# 12:43:07.475 - Request #223
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=username"
echo ""

# 12:43:07.602 - Request #224
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&sort=-createdAt"
echo ""

# 12:43:07.723 - Request #225
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=firstName,lastName"
echo ""

# 12:43:07.806 - Request #226
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true"
echo ""

# 12:43:07.910 - Request #227
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male,isAccountOwner:true"
echo ""

# 12:43:07.953 - Request #228
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=username:valid_all_user_123456"
echo ""

# 12:43:07.959 - Request #229
echo "=== GET http://localhost:5500/api/user?sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username&pageSize=3"
echo ""

# 12:43:07.969 - Request #230
echo "=== GET http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:43:07.979 - Request #231
echo "=== GET http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3"
echo ""

# 12:43:07.986 - Request #232
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3"
echo ""

# 12:43:08.007 - Request #233
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&page=1&pageSize=5"
echo ""

# 12:43:08.011 - Request #234
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3"
echo ""

# 12:43:08.018 - Request #235
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username"
echo ""

# 12:43:08.048 - Request #236
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&sort=-createdAt"
echo ""

# 12:43:08.051 - Request #237
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName"
echo ""

# 12:43:08.083 - Request #238
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=isAccountOwner:true&sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true&sort=username&pageSize=3"
echo ""

# 12:43:08.092 - Request #239
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&filter=gender:male&sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male&sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:43:08.102 - Request #240
echo "=== GET http://localhost:5500/api/user?view={"account":["id","expiredAt"]}&filter=isAccountOwner:false,gender:female&sort=firstName,lastName&page=1&pageSize=10 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22expiredAt%22%5D%7D&filter=isAccountOwner:false,gender:female&sort=firstName,lastName&page=1&pageSize=10"
echo ""

# 12:43:19.757 - Request #241
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456"
echo ""

# 12:43:19.763 - Request #242
echo "=== GET http://localhost:5500/api/user/bad_enum_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_enum_user_123456"
echo ""

# 12:43:19.765 - Request #243
echo "=== GET http://localhost:5500/api/user/bad_currency_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_currency_user_123456"
echo ""

# 12:43:19.767 - Request #244
echo "=== GET http://localhost:5500/api/user/bad_fk_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_fk_user_123456"
echo ""

# 12:43:19.770 - Request #245
echo "=== GET http://localhost:5500/api/user/multiple_errors_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/multiple_errors_user_123456"
echo ""

# 12:43:19.772 - Request #246
echo "=== GET http://localhost:5500/api/user/nonexistent_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/nonexistent_user_123456"
echo ""

# 12:43:19.777 - Request #247
echo "=== GET http://localhost:5500/api/user ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user"
echo ""

# 12:43:19.800 - Request #248
echo "=== GET http://localhost:5500/api/user?pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3"
echo ""

# 12:43:22.813 - Request #249
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:43:22.823 - Request #250
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["id","createdAt","expiredAt"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D"
echo ""

# 12:43:22.834 - Request #251
echo "=== GET http://localhost:5500/api/user/bad_fk_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/bad_fk_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:43:22.846 - Request #252
echo "=== GET http://localhost:5500/api/user/multiple_errors_user_123456?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/multiple_errors_user_123456?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:43:22.860 - Request #253
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?view={"account":["nonexistent_field"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?view=%7B%22account%22%3A%5B%22nonexistent_field%22%5D%7D"
echo ""

# 12:43:22.871 - Request #254
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:43:22.978 - Request #255
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt","expiredAt"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%2C%22expiredAt%22%5D%7D"
echo ""

# 12:43:23.109 - Request #256
echo "=== GET http://localhost:5500/api/user?pageSize=3&view={"account":["id"]} ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3&view=%7B%22account%22%3A%5B%22id%22%5D%7D"
echo ""

# 12:43:26.152 - Request #257
echo "=== GET http://localhost:5500/api/user ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user"
echo ""

# 12:43:26.272 - Request #258
echo "=== GET http://localhost:5500/api/user?pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=3"
echo ""

# 12:43:26.297 - Request #259
echo "=== GET http://localhost:5500/api/user?page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=1&pageSize=5"
echo ""

# 12:43:26.333 - Request #260
echo "=== GET http://localhost:5500/api/user?page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=2&pageSize=3"
echo ""

# 12:43:26.359 - Request #261
echo "=== GET http://localhost:5500/api/user?page=0&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=0&pageSize=5"
echo ""

# 12:43:26.391 - Request #262
echo "=== GET http://localhost:5500/api/user?pageSize=1000 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=1000"
echo ""

# 12:43:28.489 - Request #263
echo "=== GET http://localhost:5500/api/user?page=999&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?page=999&pageSize=5"
echo ""

# 12:43:28.495 - Request #264
echo "=== GET http://localhost:5500/api/user?pageSize=0 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?pageSize=0"
echo ""

# 12:43:28.572 - Request #265
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456"
echo ""

# 12:43:28.580 - Request #266
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?page=2&pageSize=10 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?page=2&pageSize=10"
echo ""

# 12:43:31.596 - Request #267
echo "=== GET http://localhost:5500/api/user?sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username"
echo ""

# 12:43:31.730 - Request #268
echo "=== GET http://localhost:5500/api/user?sort=-username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-username"
echo ""

# 12:43:31.859 - Request #269
echo "=== GET http://localhost:5500/api/user?sort=createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=createdAt"
echo ""

# 12:43:31.908 - Request #270
echo "=== GET http://localhost:5500/api/user?sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt"
echo ""

# 12:43:31.952 - Request #271
echo "=== GET http://localhost:5500/api/user?sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName,lastName"
echo ""

# 12:43:31.997 - Request #272
echo "=== GET http://localhost:5500/api/user?sort=firstName,-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName,-createdAt"
echo ""

# 12:43:32.084 - Request #273
echo "=== GET http://localhost:5500/api/user?sort=-lastName,firstName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-lastName,firstName"
echo ""

# 12:43:32.191 - Request #274
echo "=== GET http://localhost:5500/api/user?sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username&pageSize=3"
echo ""

# 12:43:32.220 - Request #275
echo "=== GET http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:43:32.248 - Request #276
echo "=== GET http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3"
echo ""

# 12:43:32.276 - Request #277
echo "=== GET http://localhost:5500/api/user?sort=nonexistentfield ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=nonexistentfield"
echo ""

# 12:43:32.287 - Request #278
echo "=== GET http://localhost:5500/api/user?sort= ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort="
echo ""

# 12:43:32.428 - Request #279
echo "=== GET http://localhost:5500/api/user?sort=- ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-"
echo ""

# 12:43:32.561 - Request #280
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?sort=username"
echo ""

# 12:43:32.571 - Request #281
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?sort=-createdAt,firstName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?sort=-createdAt,firstName"
echo ""

# 12:43:35.585 - Request #282
echo "=== GET http://localhost:5500/api/user?filter=gender:male ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male"
echo ""

# 12:43:35.650 - Request #283
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true"
echo ""

# 12:43:35.708 - Request #284
echo "=== GET http://localhost:5500/api/user?filter=username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=username:valid_all_user_123456"
echo ""

# 12:43:35.718 - Request #285
echo "=== GET http://localhost:5500/api/user?filter=username:nonexistent_user_12345 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=username:nonexistent_user_12345"
echo ""

# 12:43:35.726 - Request #286
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:true"
echo ""

# 12:43:35.783 - Request #287
echo "=== GET http://localhost:5500/api/user?filter=gender:female,isAccountOwner:false ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:female,isAccountOwner:false"
echo ""

# 12:43:35.837 - Request #288
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true,username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true,username:valid_all_user_123456"
echo ""

# 12:43:35.844 - Request #289
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3"
echo ""

# 12:43:35.854 - Request #290
echo "=== GET http://localhost:5500/api/user?filter=gender:male&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male&page=1&pageSize=5"
echo ""

# 12:43:35.871 - Request #291
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3"
echo ""

# 12:43:35.885 - Request #292
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username"
echo ""

# 12:43:35.970 - Request #293
echo "=== GET http://localhost:5500/api/user?filter=gender:male&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male&sort=-createdAt"
echo ""

# 12:43:36.079 - Request #294
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName"
echo ""

# 12:43:36.209 - Request #295
echo "=== GET http://localhost:5500/api/user?filter=nonexistentfield:value ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=nonexistentfield:value"
echo ""

# 12:43:36.218 - Request #296
echo "=== GET http://localhost:5500/api/user?filter=invalidformat ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=invalidformat"
echo ""

# 12:43:36.348 - Request #297
echo "=== GET http://localhost:5500/api/user?filter= ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter="
echo ""

# 12:43:36.474 - Request #298
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male"
echo ""

# 12:43:36.480 - Request #299
echo "=== GET http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user/valid_all_user_123456?filter=gender:male,isAccountOwner:true"
echo ""

# 12:43:39.497 - Request #300
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&pageSize=3"
echo ""

# 12:43:39.518 - Request #301
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&page=1&pageSize=5"
echo ""

# 12:43:39.552 - Request #302
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&page=2&pageSize=3"
echo ""

# 12:43:39.579 - Request #303
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=username"
echo ""

# 12:43:39.713 - Request #304
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&sort=-createdAt"
echo ""

# 12:43:39.831 - Request #305
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&sort=firstName,lastName"
echo ""

# 12:43:39.966 - Request #306
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true"
echo ""

# 12:43:40.098 - Request #307
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&filter=gender:male,isAccountOwner:true ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male,isAccountOwner:true"
echo ""

# 12:43:40.236 - Request #308
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=username:valid_all_user_123456 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=username:valid_all_user_123456"
echo ""

# 12:43:40.257 - Request #309
echo "=== GET http://localhost:5500/api/user?sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=username&pageSize=3"
echo ""

# 12:43:40.280 - Request #310
echo "=== GET http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:43:40.309 - Request #311
echo "=== GET http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?sort=firstName&page=2&pageSize=3"
echo ""

# 12:43:40.331 - Request #312
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&pageSize=3"
echo ""

# 12:43:40.356 - Request #313
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&page=1&pageSize=5"
echo ""

# 12:43:40.367 - Request #314
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&page=2&pageSize=3"
echo ""

# 12:43:40.392 - Request #315
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:true&sort=username"
echo ""

# 12:43:40.521 - Request #316
echo "=== GET http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&sort=-createdAt ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=gender:male,isAccountOwner:false&sort=-createdAt"
echo ""

# 12:43:40.532 - Request #317
echo "=== GET http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?filter=isAccountOwner:false&sort=firstName,lastName"
echo ""

# 12:43:40.685 - Request #318
echo "=== GET http://localhost:5500/api/user?view={"account":["id"]}&filter=isAccountOwner:true&sort=username&pageSize=3 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%5D%7D&filter=isAccountOwner:true&sort=username&pageSize=3"
echo ""

# 12:43:40.708 - Request #319
echo "=== GET http://localhost:5500/api/user?view={"account":["id","createdAt"]}&filter=gender:male&sort=-createdAt&page=1&pageSize=5 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22createdAt%22%5D%7D&filter=gender:male&sort=-createdAt&page=1&pageSize=5"
echo ""

# 12:43:40.734 - Request #320
echo "=== GET http://localhost:5500/api/user?view={"account":["id","expiredAt"]}&filter=isAccountOwner:false,gender:female&sort=firstName,lastName&page=1&pageSize=10 ==="
curl -w "Time: %{time_total}s\nStatus: %{http_code}\n" -X GET "http://localhost:5500/api/user?view=%7B%22account%22%3A%5B%22id%22%2C%22expiredAt%22%5D%7D&filter=isAccountOwner:false,gender:female&sort=firstName,lastName&page=1&pageSize=10"
echo ""

