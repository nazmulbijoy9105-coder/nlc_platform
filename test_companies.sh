#!/bin/bash
API="https://nlc-platform.onrender.com/api/v1"

TOKEN=$(curl -s -X POST "$API/auth/login" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "username=admin@neumlexcounsel.com&password=NLC@Admin2026!" | python -c "import sys,json; d=json.load(sys.stdin); print(d.get('access_token',''))")

echo "TOKEN: $TOKEN"
echo ""

echo "=== 1. Empty body → should 422 ==="
curl -s -X POST "$API/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{}' | python -m json.tool

echo ""
echo "=== 2. Partial body → shows missing fields ==="
curl -s -X POST "$API/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"company_name":"X"}' | python -m json.tool

echo ""
echo "=== 3. Valid body ==="
curl -s -X POST "$API/companies" \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $TOKEN" \
  -d '{
    "company_name": "Test Company Ltd",
    "registration_number": "C-12345",
    "incorporation_date": "2020-01-15",
    "registered_address": "123 Motijheel, Dhaka 1000",
    "company_type": "PRIVATE_LIMITED"
  }' | python -m json.tool
