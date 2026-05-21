#!/bin/bash
# ==============================================================================
# Odoo ERP Security Hardening Auditor
# Usage: chmod +x audit_security.sh && ./audit_security.sh
# ==============================================================================

# Text Formatting Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
BOLD='\033[1m'
NC='\033[0;0m' # No Color

echo -e "${BLUE}${BOLD}====================================================================${NC}"
echo -e "${BLUE}${BOLD}        Executing Odoo Security Hardening Audit Scanner             ${NC}"
echo -e "${BLUE}${BOLD}====================================================================${NC}"

VULNS_FOUND=0

# ------------------------------------------------------------------------------
# TEST 1: Check for Manifest Security Coverage
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[Test 1/5] Checking Access Control Definitions...${NC}"
if [ ! -f "security/ir.model.access.csv" ]; then
    echo -e "  ${RED}✗ CRITICAL: security/ir.model.access.csv file is completely missing!${NC}"
    ((VULNS_FOUND++))
else
    echo -e "  ${GREEN}✓ Found access control file: security/ir.model.access.csv${NC}"
fi

# ------------------------------------------------------------------------------
# TEST 2: Scan for Uncontrolled .sudo() Usage
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[Test 2/5] Scanning for bypassing access controls (.sudo())...${NC}"
SUDO_COUNT=$(grep -rn "\.sudo()" . --include="*.py" | wc -l)

if [ "$SUDO_COUNT" -gt 0 ]; then
    echo -e "  ${YELLOW}⚠ WARNING: Found $SUDO_COUNT instances of .sudo() execution.${NC}"
    echo -e "  Review the lines below to ensure regular users can't exploit them:"
    grep -rn "\.sudo()" . --include="*.py" | sed 's/^/    /'
    ((VULNS_FOUND++))
else
    echo -e "  ${GREEN}✓ Clean! No bare .sudo() calls found in Python source code.${NC}"
fi

# ------------------------------------------------------------------------------
# TEST 3: Scan for Potential SQL Injection Vectors
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[Test 3/5] Scanning for unsafe Raw SQL execution (SQL Injection)...${NC}"
# Checks for cr.execute containing Python string interpolation (%, format, f-strings)
SQL_INJ=$(grep -rnE "cr\.execute\s*\(.*(%|\.format|f[\"']).*\)" . --include="*.py")

if [ -n "$SQL_INJ" ]; then
    echo -e "  ${RED}✗ CRITICAL: Detected potential SQL injection vulnerabilities!${NC}"
    echo -e "  Raw SQL queries must use parameterized arguments, never direct string formatting:"
    echo "$SQL_INJ" | sed 's/^/    /'
    ((VULNS_FOUND++))
else
    echo -e "  ${GREEN}✓ Clean! No dynamic string formats found inside cr.execute().${NC}"
fi

# ------------------------------------------------------------------------------
# TEST 4: Scan for Unsecured HTTP Routing / CSRF Disables
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[Test 4/5] Auditing Controller Web Routes...${NC}"
WEAK_AUTH=$(grep -rnE "auth=['\"]none['\"]" . --include="*.py")
DISABLED_CSRF=$(grep -rn "csrf=False" . --include="*.py")

if [ -n "$WEAK_AUTH" ] || [ -n "$DISABLED_CSRF" ]; then
    echo -e "  ${YELLOW}⚠ WARNING: Web controller vulnerabilities detected.${NC}"
    if [ -n "$WEAK_AUTH" ]; then
        echo -e "    ${RED}• Public routes discovered (auth='none'):${NC}"
        echo "$WEAK_AUTH" | sed 's/^/      /'
    fi
    if [ -n "$DISABLED_CSRF" ]; then
        echo -e "    ${RED}• CSRF Protection turned off (csrf=False):${NC}"
        echo "$DISABLED_CSRF" | sed 's/^/      /'
    fi
    ((VULNS_FOUND++))
else
    echo -e "  ${GREEN}✓ Clean! Web routes are enforcing standard authentication and anti-CSRF tokens.${NC}"
fi

# ------------------------------------------------------------------------------
# TEST 5: Verify Model vs CSV Registration Alignment
# ------------------------------------------------------------------------------
echo -e "\n${BOLD}[Test 5/5] Auditing Custom Model System Registration...${NC}"
if [ -f "security/ir.model.access.csv" ]; then
    MISSING_MODS=0
    # Find all declared models _name = 'xyz'
    grep -rn "_name\s*=\s*['\"][a-zA-Z0-9._]*['\"]" . --include="*.py" | while read -r line; do
        # Extract the model name string
        MODEL_NAME=$(echo "$line" | grep -oE "['\"][a-zA-Z0-9._]*['\"]" | sed "s/['\"]//g")
        # Format to CSV model convention (replace periods with underscores)
        CSV_MODEL_ID="model_$(echo "$MODEL_NAME" | tr '.' '_')"
        
        # Look for this formatted model ID inside the security file
        if ! grep -q "$CSV_MODEL_ID" "security/ir.model.access.csv"; then
            FILE_INFO=$(echo "$line" | cut -d: -f1,2)
            echo -e "  ${RED}✗ MISMATCH:${NC} Model '${MODEL_NAME}' ($FILE_INFO) is missing an entry in ir.model.access.csv!"
            ((MISSING_MODS++))
        fi
    done
    if [ "$MISSING_MODS" -eq 0 ]; then
        echo -e "  ${GREEN}✓ Clean! All custom objects found match up with access rules.${NC}"
    else
        ((VULNS_FOUND++))
    fi
fi

# ------------------------------------------------------------------------------
# Summary Evaluation
# ------------------------------------------------------------------------------
echo -e "\n${BLUE}${BOLD}====================================================================${NC}"
if [ "$VULNS_FOUND" -eq 0 ]; then
    echo -e "${GREEN}${BOLD} ★ QUEST SUCCESSFUL: NO VULNERABILITIES DETECTED! ${NC}"
    echo -e "${YELLOW}${BOLD} 🏆 ACHIEVEMENT UNLOCKED: \"Fort Knox ERP Architect\" 🏆${NC}"
    echo -e " Code status: Certified Secure."
else
    echo -e "${RED}${BOLD} ✗ QUEST INCOMPLETE: $VULNS_FOUND Security gaps need attention before check-in.${NC}"
fi
echo -e "${BLUE}${BOLD}====================================================================${NC}"
