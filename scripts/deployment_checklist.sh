#!/usr/bin/env bash
# =============================================================================
# Production Deployment Checklist
# NEUM LEX COUNSEL — Pre-Launch Verification
# =============================================================================

set -e

echo "🚀 NEUM LEX COUNSEL - Production Deployment Checklist"
echo "========================================================="
echo ""

# Color codes
GREEN='\033[0;32m'
RED='\033[0;31m'
YELLOW='\033[1;33m'
NC='\033[0m'

PASSED=0
FAILED=0

# Helper functions
check_pass() {
  echo -e "${GREEN}✅ $1${NC}"
  PASSED=$((PASSED + 1))
}

check_fail() {
  echo -e "${RED}❌ $1${NC}"
  FAILED=$((FAILED + 1))
}

check_warn() {
  echo -e "${YELLOW}⚠️  $1${NC}"
}

echo "1️⃣  BACKEND CHECKS"
echo "===================="

# Check fly.toml exists
if [ -f "fly.toml" ]; then
  check_pass "fly.toml exists"
else
  check_fail "fly.toml missing"
fi

# Check Dockerfile
if [ -f "Dockerfile" ]; then
  check_pass "Dockerfile exists"
else
  check_fail "Dockerfile missing"
fi

# Check requirements.txt
if [ -f "requirements.txt" ]; then
  check_pass "requirements.txt exists"
else
  check_fail "requirements.txt missing"
fi

# Check environment variables
if grep -q "DATABASE_URL\|REDIS_URL\|JWT_SECRET" .env 2>/dev/null; then
  check_pass "Environment variables configured locally"
else
  check_warn "Review .env file for all required variables"
fi

echo ""
echo "2️⃣  GITHUB ACTIONS WORKFLOWS"
echo "=============================="

if [ -f ".github/workflows/deploy-fly.yml" ]; then
  check_pass "Backend deployment workflow exists"
else
  check_fail "Backend deployment workflow missing"
fi

if [ -f ".github/workflows/backup-health-check.yml" ]; then
  check_pass "Health check workflow exists"
else
  check_fail "Health check workflow missing"
fi

if [ -f ".github/workflows/daily-s3-backup.yml" ]; then
  check_pass "S3 backup workflow exists"
else
  check_fail "S3 backup workflow missing"
fi

echo ""
echo "3️⃣  DOCUMENTATION"
echo "=================="

if [ -f "FLY_DEPLOYMENT_GUIDE.md" ]; then
  check_pass "Deployment guide exists"
else
  check_fail "Deployment guide missing"
fi

if [ -f "FLY_MONITORING_SETUP.md" ]; then
  check_pass "Monitoring documentation exists"
else
  check_fail "Monitoring documentation missing"
fi

if [ -f "BACKUP_DISASTER_RECOVERY.md" ]; then
  check_pass "Disaster recovery plan exists"
else
  check_fail "Disaster recovery plan missing"
fi

echo ""
echo "4️⃣  SECURITY CHECKS"
echo "===================="

# Check if secrets are in git (should not be)
if grep -r "\.env$" .gitignore > /dev/null 2>&1; then
  check_pass ".env file is gitignored"
else
  check_fail ".env file should be gitignored"
fi

# Check docker ignore
if [ -f ".dockerignore" ]; then
  check_pass ".dockerignore exists"
else
  check_warn ".dockerignore not found (should exclude .git, __pycache__, etc.)"
fi

echo ""
echo "5️⃣  DEPLOYMENT READINESS"
echo "========================="

echo ""
echo "Before pushing to production, complete:"
echo ""
echo "Backend Setup:"
echo "  [ ] Install flyctl: curl -L https://fly.io/install.sh | sh"
echo "  [ ] Authenticate: flyctl auth login"
echo "  [ ] Apply fly.toml: flyctl launch"
echo "  [ ] Create PostgreSQL: flyctl postgres create"
echo "  [ ] Create Redis: flyctl redis create"
echo "  [ ] Set secrets: flyctl secrets set ..."
echo "  [ ] Deploy: flyctl deploy"
echo "  [ ] Run migrations: flyctl ssh console → alembic upgrade head"
echo ""
echo "Frontend Setup:"
echo "  [ ] Create Vercel account"
echo "  [ ] Import nlc_frontend repository"
echo "  [ ] Set NEXT_PUBLIC_API_URL environment variable"
echo "  [ ] Deploy to Vercel"
echo ""
echo "Integration:"
echo "  [ ] Update ALLOWED_ORIGINS in backend"
echo "  [ ] Test CORS (frontend → backend API call)"
echo "  [ ] Configure Slack webhook (optional)"
echo "  [ ] Configure AWS S3 (optional)"
echo ""

echo ""
echo "==========================================================="
echo "✅ SUMMARY"
echo "==========================================================="
echo -e "${GREEN}Passed:${NC} $PASSED"
echo -e "${RED}Failed:${NC} $FAILED"
echo ""

if [ $FAILED -eq 0 ]; then
  echo "🎉 All checks passed! Ready for deployment."
  exit 0
else
  echo "⚠️  Please fix failed checks before deployment."
  exit 1
fi
