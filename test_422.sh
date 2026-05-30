#!/bin/bash
API="https://nlc-platform.onrender.com/api/v1"

echo "=== 1. Schema check (local) ==="
grep -A 25 "class CompanyCreateRequest" app/schemas/*.py 2>/dev/null || echo "Schema not found in expected location"

echo ""
echo "=== 2. Test empty body (should 422) ==="
curl -s -X POST "$API/companies" \
  -H "Content-Type: application/json" \
  -d '{}' | python -m json.tool

echo ""
echo "=== 3. Test with only name (should 422, shows missing fields) ==="
curl -s -X POST "$API/companies" \
  -H "Content-Type: application/json" \
  -d '{"company_name":"X"}' | python -m json.tool

echo ""
echo "=== 4. Test with all fields but bad date ==="
curl -s -X POST "$API/companies" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Co",
    "registration_number": "C-12345",
    "incorporation_date": "15-01-2020",
    "registered_address": "Dhaka",
    "company_type": "PRIVATE_LIMITED",
    "financial_year_end": "2025-06-30"
  }' | python -m json.tool

echo ""
echo "=== 5. Test with all fields but wrong company_type casing ==="
curl -s -X POST "$API/companies" \
  -H "Content-Type: application/json" \
  -d '{
    "company_name": "Test Co",
    "registration_number": "C-12345",
    "incorporation_date": "2020-01-15",
    "registered_address": "Dhaka",
    "company_type": "private_limited",
    "financial_year_end": "2025-06-30"
  }' | python -m json.tool
