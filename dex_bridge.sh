#!/usr/bin/env bash

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
        echo -e "${BLUE}$(center_text "Proxy Management Tool" $term_width)${NC}"
    else
        # Simplified banner for narrow terminals
        echo -e "${CYAN}"
        echo "╔════════════════════════════════════╗"
        echo "║                                    ║"
        echo "║         DEX BRIDGE PROXY           ║"
        echo "║      Management Tool v1.0          ║"
        echo "║                                    ║"
        echo "╚════════════════════════════════════╝"
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

download_mitm_cert() {
    local dest_dir="$HOME/.mitmproxy"
    local cert_url="http://mitm.it/cert/pem"
    local dest_file="$dest_dir/mitmproxy-ca-cert.pem"
    if [ ! -d "$dest_dir" ]; then
        mkdir -p "$dest_dir"
    fi

    if [[ -s "$dest_file" ]]; then
        echo -e "${GREEN}✓ mitmproxy CA certificate already exists at $dest_file${NC}"
        return
    fi

    echo -e "${YELLOW}Downloading mitmproxy CA certificate...${NC}"

    if command -v curl >/dev/null 2>&1; then
        curl -s -o "$dest_file" "$cert_url"
    elif command -v wget >/dev/null 2>&1; then
        wget -q -O "$dest_file" "$cert_url"
    else
        echo -e "${RED}✗ Neither curl nor wget is installed. Please install one to download the certificate.${NC}"
        return 1
    fi

    if [[ ! -s "$dest_file" ]]; then
        echo -e "${RED}✗ Failed to download mitmproxy CA certificate.${NC}"
        return 2
    fi

    echo "CA certificate downloaded to $dest_file"
    echo "$dest_file"
    return 0
}

install_mitm_ca_cert() {
    echo -e "${YELLOW}Installing mitmproxy CA certificate...${NC}"
    local cert_path="$HOME/.mitmproxy/mitmproxy-ca-cert.pem"
    if [ -f "$cert_path" ]; then
        sudo security add-trusted-cert -d -r trustRoot -k /Library/Keychains/System.keychain "$cert_path"
        echo -e "${GREEN}✓ mitmproxy CA certificate installed successfully${NC}"
    else
        echo -e "${RED}✗ mitmproxy CA certificate not found at $cert_path${NC}"
    fi
    sleep 1
}

verify_mitm_cert() {
    local cert_name="mitmproxy-ca-cert.pem"
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
        cert_path=$(download_mitm_cert)
        if [ $? -eq 0 ]; then
            install_mitm_ca_cert
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