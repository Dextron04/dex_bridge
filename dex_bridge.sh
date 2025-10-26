#!/usr/bin/env bash

# ============================================================================
# Dex Bridge - Proxy Management Tool
# ============================================================================
# 
# Copyright (c) 2025 Dextron04
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in
# all copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN
# THE SOFTWARE.
# ============================================================================

SERVICE="Wi-Fi"
PROXY_IP="127.0.0.1"
PROXY_PORT=8080

# Colors for better UI
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
CYAN='\033[0;36m'
NC='\033[0m' # No Color

# Function to display ASCII art
show_banner() {
    clear
    
    # Get terminal width
    local term_width=$(tput cols 2>/dev/null || echo 80)
    local art_width=90  # Width of the ASCII art
    
    # Only show full ASCII art if terminal is wide enough
    if [ "$term_width" -ge "$art_width" ]; then
        echo -e "${CYAN}"
        cat << "EOF"
                                                                                     
________                            ________                    ___                  
`MMMMMMMb.                          `MMMMMMMb.         68b      `MM                  
 MM    `Mb                           MM    `Mb         Y89       MM                  
 MM     MM   ____  ____   ___        MM     MM ___  __ ___   ____MM   __      ____   
 MM     MM  6MMMMb `MM(   )P'        MM    .M9 `MM 6MM `MM  6MMMMMM  6MMbMMM 6MMMMb  
 MM     MM 6M'  `Mb `MM` ,P          MMMMMMM(   MM69 "  MM 6M'  `MM 6M'`Mb  6M'  `Mb 
 MM     MM MM    MM  `MM,P           MM    `Mb  MM'     MM MM    MM MM  MM  MM    MM 
 MM     MM MMMMMMMM   `MM.           MM     MM  MM      MM MM    MM YM.,M9  MMMMMMMM 
 MM     MM MM         d`MM.          MM     MM  MM      MM MM    MM  YMM9   MM       
 MM    .M9 YM    d9  d' `MM.         MM    .M9  MM      MM YM.  ,MM (M      YM    d9 
_MMMMMMM9'  YMMMM9 _d_  _)MM_       _MMMMMMM9' _MM_    _MM_ YMMMMMM_ YMMMMb. YMMMM9  
                                                                    6M    Yb         
                                                                    YM.   d9         
                                                                     YMMMM9          
EOF
        echo -e "${NC}"
        echo -e "${BLUE}$(center_text "Long term shared context between LLMs" $term_width)${NC}"
        echo -e "${BLUE}$(center_text "Copyright © 2025 Tushin Kulshreshtha" $term_width)${NC}"
    else
        # Simplified banner for narrow terminals
        echo -e "${CYAN}"
        echo "╔═══════════════════════════════════════════════╗"
        echo "║                                               ║"
        echo "║                  DEX BRIDGE                   ║"
        echo "║                                               ║"
        echo "║           []                     []           ║"
        echo "║         .:[]:                  .:[]:          ║"
        echo "║       .: :[]: :.             .: :[]: :.       ║"
        echo "║     .: : :[]: : :.         .: : :[]: : :.     ║"
        echo "║   .: : : :[]: : : :-.___.-: : : :[]: : : :.   ║"
        echo "║ _:_:_:_:_:[]:_:_:_:_:_::_:_:_:_ :[]:_:_:_:_:_ ║"
        echo "║ ^^^^^^^^^^[]^^^^^^^^^^^^^^^^^^^^^[]^^^^^^^^^^ ║"
        echo "║           []                     []           ║"
        echo "║                                               ║"
        echo "║      Long term shared context between LLMs    ║"
        echo "║                                               ║"
        echo "║        Copyright © 2025 Tushin Kulshreshtha   ║"
        echo "║                                               ║"
        echo "╚═══════════════════════════════════════════════╝"
        echo -e "${NC}"
    fi
    echo ""
    sleep 0.5
}

# Function to center text
center_text() {
    local text="$1"
    local width="$2"
    local text_length=${#text}
    local padding=$(( (width - text_length) / 2 ))
    printf "%*s%s%*s\n" $padding "" "$text" $padding ""
}

# Function to get current proxy status
get_proxy_status() {
    local http_enabled=$(networksetup -getwebproxy "$SERVICE" | grep "Enabled: Yes" | wc -l)
    local https_enabled=$(networksetup -getsecurewebproxy "$SERVICE" | grep "Enabled: Yes" | wc -l)
    
    if [ "$http_enabled" -gt 0 ] && [ "$https_enabled" -gt 0 ]; then
        echo "ON"
    else
        echo "OFF"
    fi
}

# Function to display current status
show_status() {
    if [ "${SHOW_BANNER:-true}" == "true" ]; then
        show_banner
        SHOW_BANNER=false
    else
        clear
    fi
    
    local term_width=$(tput cols 2>/dev/null || echo 80)
    local separator=$(printf '═%.0s' $(seq 1 $((term_width > 50 ? 50 : term_width))))
    
    echo -e "${BLUE}${separator}${NC}"
    echo -e "${BLUE}$(center_text "Proxy Manager - Current Status" $((term_width > 50 ? 50 : term_width)))${NC}"
    echo -e "${BLUE}${separator}${NC}"
    echo ""
    
    local status=$(get_proxy_status)
    
    echo -e "Network Service: ${YELLOW}$SERVICE${NC}"
    echo -e "Proxy Address:   ${YELLOW}$PROXY_IP:$PROXY_PORT${NC}"
    echo ""
    
    if [ "$status" == "ON" ]; then
        echo -e "Proxy Status:    ${GREEN}● ENABLED${NC}"
    else
        echo -e "Proxy Status:    ${RED}○ DISABLED${NC}"
    fi
    
    echo ""
    echo "HTTP Proxy Details:"
    networksetup -getwebproxy "$SERVICE" | grep -E "Enabled|Server|Port" | sed 's/^/  /'
    
    echo ""
    echo "HTTPS Proxy Details:"
    networksetup -getsecurewebproxy "$SERVICE" | grep -E "Enabled|Server|Port" | sed 's/^/  /'
    
    echo ""
    local term_width=$(tput cols 2>/dev/null || echo 80)
    local separator=$(printf '═%.0s' $(seq 1 $((term_width > 50 ? 50 : term_width))))
    echo -e "${BLUE}${separator}${NC}"
}

# Function to enable proxy
enable_proxy() {
    echo -e "${YELLOW}Enabling proxy...${NC}"
    networksetup -setwebproxy "$SERVICE" "$PROXY_IP" "$PROXY_PORT"
    networksetup -setwebproxystate "$SERVICE" on
    networksetup -setsecurewebproxy "$SERVICE" "$PROXY_IP" "$PROXY_PORT"
    networksetup -setsecurewebproxystate "$SERVICE" on
    echo -e "${GREEN}✓ Proxy enabled successfully${NC}"
    sleep 1
}

# Function to disable proxy
disable_proxy() {
    echo -e "${YELLOW}Disabling proxy...${NC}"
    networksetup -setwebproxystate "$SERVICE" off
    networksetup -setsecurewebproxystate "$SERVICE" off
    echo -e "${GREEN}✓ Proxy disabled successfully${NC}"
    sleep 1
}

# Function to toggle proxy
toggle_proxy() {
    local status=$(get_proxy_status)
    if [ "$status" == "ON" ]; then
        disable_proxy
    else
        enable_proxy
    fi
}

start_mitm_capture() {
    echo -e "${YELLOW}Starting mitmproxy to capture data...${NC}"
    mitmdump -s mitm/scripts/capture_req.py -s mitm/scripts/capture_claude.py -w chatgpt_posts.mitm
}

# Function to display menu
show_menu() {
    show_status
    echo ""
    echo "Options:"
    echo "  [1] Toggle Proxy (ON/OFF)"
    echo "  [2] Start capturing data"
    echo "  [3] Refresh Status"
    echo "  [q] Quit"
    echo ""
    echo -ne "${BLUE}Select option: ${NC}"
}

# --- Certificate Management Functions -- #

generate_mitm_cert() {
    # Get the actual user when running with sudo
    local actual_user="${SUDO_USER:-$USER}"
    local user_home=$(eval echo ~$actual_user)
    local dest_dir="$user_home/.mitmproxy"
    local dest_file="$dest_dir/mitmproxy-ca-cert.pem"
    
    if [ ! -d "$dest_dir" ]; then
        mkdir -p "$dest_dir"
        chown "$actual_user" "$dest_dir" 2>/dev/null || true
    fi

    if [[ -s "$dest_file" ]]; then
        echo -e "${GREEN}✓ mitmproxy CA certificate already exists at $dest_file${NC}"
        return 0
    fi

    echo -e "${YELLOW}Generating mitmproxy CA certificate...${NC}"
    
    # Run mitmdump briefly to generate the certificate as the actual user
    if command -v mitmdump >/dev/null 2>&1; then
        # Start mitmdump in background and kill it after 2 seconds
        if [ "$actual_user" != "root" ] && [ -n "$SUDO_USER" ]; then
            # Run as the actual user if we're running with sudo
            sudo -u "$actual_user" mitmdump >/dev/null 2>&1 &
        else
            mitmdump >/dev/null 2>&1 &
        fi
        local mitm_pid=$!
        sleep 2
        kill $mitm_pid 2>/dev/null || true
        wait $mitm_pid 2>/dev/null || true
    else
        echo -e "${RED}✗ mitmdump is not installed. Cannot generate certificate.${NC}"
        return 1
    fi

    # Give it a moment to finish writing
    sleep 1

    # Check if certificate was generated
    if [[ -s "$dest_file" ]]; then
        echo -e "${GREEN}✓ mitmproxy CA certificate generated at $dest_file${NC}"
        # Ensure proper ownership
        chown "$actual_user" "$dest_file" 2>/dev/null || true
        return 0
    else
        echo -e "${RED}✗ Failed to generate mitmproxy CA certificate.${NC}"
        return 1
    fi
}

install_mitm_ca_cert() {
    echo -e "${YELLOW}Installing mitmproxy CA certificate...${NC}"
    local actual_user="${SUDO_USER:-$USER}"
    local user_home=$(eval echo ~$actual_user)
    local cert_path="$user_home/.mitmproxy/mitmproxy-ca-cert.pem"
    
    if [ ! -f "$cert_path" ]; then
        echo -e "${RED}✗ mitmproxy CA certificate not found at $cert_path${NC}"
        return 1
    fi
    
    # Remove old certificate if it exists (to avoid duplicates)
    security delete-certificate -c "mitmproxy" /Library/Keychains/System.keychain 2>/dev/null || true
    
    # Install certificate to system keychain with SSL-only trust
    sudo security add-certificates -k /Library/Keychains/System.keychain "$cert_path"
    
    if [ $? -eq 0 ]; then
        # Set trust settings for SSL only
        sudo security add-trusted-cert -d -p ssl -r trustRoot -k /Library/Keychains/System.keychain "$cert_path" 2>/dev/null
        echo -e "${GREEN}✓ mitmproxy CA certificate installed to system keychain (SSL/TLS trust only)${NC}"
        
        # Also add to user's login keychain for browser compatibility
        security add-certificates -k ~/Library/Keychains/login.keychain-db "$cert_path" 2>/dev/null && \
        security add-trusted-cert -d -p ssl -r trustRoot -k ~/Library/Keychains/login.keychain-db "$cert_path" 2>/dev/null || true
        
        echo -e "${GREEN}✓ mitmproxy CA certificate installed successfully${NC}"
        echo -e "${YELLOW}Note: Certificate is trusted for SSL/TLS only. Restart browser for changes to take effect${NC}"
    else
        echo -e "${RED}✗ Failed to install mitmproxy CA certificate${NC}"
        return 1
    fi
    
    sleep 1
    return 0
}

verify_mitm_cert() {
    local actual_user="${SUDO_USER:-$USER}"
    local user_home=$(eval echo ~$actual_user)
    local cert_path="$user_home/.mitmproxy/mitmproxy-ca-cert.pem"
    local cert_name="mitmproxy"
    
    # Check if certificate file exists on disk
    if [ ! -f "$cert_path" ]; then
        echo -e "${YELLOW}Certificate file not found at $cert_path${NC}"
        return 1
    fi
    
    # Check if certificate is installed in system keychain
    if security find-certificate -a -c "$cert_name" /Library/Keychains/System.keychain >/dev/null 2>&1; then
        return 0
    else
        return 1
    fi
}

# Main interactive loop
main() {
    # Initialize banner flag
    SHOW_BANNER=true

    echo -e "${YELLOW}Checking mitmproxy CA certificate...${NC}"
    if verify_mitm_cert; then
        echo -e "${GREEN}Certificate verification passed.${NC}"
    else
        echo -e "${YELLOW}Certificate not found or not trusted. Installing...${NC}"
        if generate_mitm_cert; then
            install_mitm_ca_cert
        else
            echo -e "${RED}✗ Failed to generate certificate. Please check your mitmproxy installation.${NC}"
        fi
    fi
    sleep 1

    if mitmdump --version >/dev/null 2>&1; then
        echo -e "${GREEN}✓ mitmdump is installed.${NC}"
    else
        echo -e "${RED}✗ mitmdump is not installed. Please install mitmproxy to proceed.${NC}"
        exit 1
    fi
    
    # Check if running in non-interactive mode (with argument)
    if [ $# -gt 0 ]; then
        case "$1" in
            on|enable)
                enable_proxy
                ;;
            off|disable)
                disable_proxy
                ;;
            toggle)
                toggle_proxy
                ;;
            status)
                show_status
                ;;
            *)
                echo "Usage: $0 [on|off|toggle|status]"
                exit 1
                ;;
        esac
        exit 0
    fi
    
    # Interactive mode
    while true; do
        show_menu
        read -r choice
        
        case "$choice" in
            1)
                toggle_proxy
                ;;
            2)
                if get_proxy_status | grep -q "ON"; then
                    start_mitm_capture
                else
                    echo -e "${RED}Proxy is disabled. Please enable the proxy before capturing data.${NC}"
                    sleep 2
                    continue
                fi
                ;;
            
            3)
                # Just refresh (menu will redisplay)
                ;;
            q|Q)
                if get_proxy_status | grep -q "ON"; then
                    disable_proxy
                fi
                echo -e "${GREEN}Goodbye!${NC}"
                exit 0
                ;;
            *)
                echo -e "${RED}Invalid option. Press Enter to continue...${NC}"
                read
                ;;
        esac
    done
}

# Run main function
main "$@"