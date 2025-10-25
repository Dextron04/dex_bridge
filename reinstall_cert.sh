#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

CERT_PATH="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"

echo -e "${YELLOW}=== mitmproxy Certificate Reinstallation ===${NC}\n"

# Check if certificate exists
if [ ! -f "$CERT_PATH" ]; then
    echo -e "${RED}✗ Certificate not found at $CERT_PATH${NC}"
    echo -e "${YELLOW}Please run the main script first to generate the certificate.${NC}"
    exit 1
fi

echo -e "${YELLOW}Certificate found at: $CERT_PATH${NC}\n"

# Remove old certificates from system keychain
echo -e "${YELLOW}Removing old mitmproxy certificates (if any)...${NC}"
sudo security delete-certificate -c "mitmproxy" /Library/Keychains/System.keychain 2>/dev/null && \
    echo -e "${GREEN}✓ Removed from System keychain${NC}" || \
    echo -e "${YELLOW}No existing certificate in System keychain${NC}"

security delete-certificate -c "mitmproxy" ~/Library/Keychains/login.keychain-db 2>/dev/null && \
    echo -e "${GREEN}✓ Removed from login keychain${NC}" || \
    echo -e "${YELLOW}No existing certificate in login keychain${NC}"

echo ""

# Install to System keychain (without setting trust - we'll do it manually)
echo -e "${YELLOW}Installing certificate to System keychain...${NC}"
sudo security add-certificates -k /Library/Keychains/System.keychain "$CERT_PATH"

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Certificate added to System keychain${NC}"
    
    # Set trust settings for SSL only
    echo -e "${YELLOW}Setting trust for SSL/TLS only...${NC}"
    sudo security add-trusted-cert -d -p ssl -r trustRoot -k /Library/Keychains/System.keychain "$CERT_PATH" 2>/dev/null
    echo -e "${GREEN}✓ Trust configured for SSL/TLS only${NC}"
else
    echo -e "${RED}✗ Failed to install to System keychain${NC}"
    exit 1
fi

# Install to user's login keychain with SSL-only trust
echo -e "${YELLOW}Installing certificate to login keychain...${NC}"
security add-certificates -k ~/Library/Keychains/login.keychain-db "$CERT_PATH" 2>/dev/null

if [ $? -eq 0 ]; then
    echo -e "${GREEN}✓ Certificate added to login keychain${NC}"
    
    # Set trust settings for SSL only in login keychain
    security add-trusted-cert -d -p ssl -r trustRoot -k ~/Library/Keychains/login.keychain-db "$CERT_PATH" 2>/dev/null
    echo -e "${GREEN}✓ Trust configured for SSL/TLS only in login keychain${NC}"
else
    echo -e "${YELLOW}⚠ Could not install to login keychain (may not be critical)${NC}"
fi

echo ""
echo -e "${GREEN}=== Certificate Installation Complete ===${NC}"
echo ""
echo -e "${YELLOW}Important: Please restart your browser for the changes to take effect!${NC}"
echo ""
echo -e "If you still see certificate warnings, you may need to:"
echo -e "  1. Completely quit and restart your browser (not just close the window)"
echo -e "  2. Clear your browser's SSL state/cached certificates"
echo -e "  3. In Chrome/Edge: Go to chrome://restart"
echo -e "  4. In Safari: Quit Safari completely and restart"
echo ""
