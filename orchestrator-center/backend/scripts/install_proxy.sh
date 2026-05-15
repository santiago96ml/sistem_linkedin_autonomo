#!/bin/bash
# =============================================================================
# install_proxy.sh — Instala microsocks SOCKS5 proxy en VPS Linux
#
# Uso:
#   ssh user@vps-ip 'bash -s' < install_proxy.sh [--port 1080] [--user proxy] [--pass secreto]
#
# Sin autenticación (solo por IP):
#   ssh user@vps-ip 'bash -s' < install_proxy.sh --no-auth
#
# Flags:
#   --port PORT     Puerto del proxy (default: 1080)
#   --user USER     Usuario para auth (default: proxy)
#   --pass PASS     Contraseña para auth (default: random 16 chars)
#   --no-auth       Proxy sin autenticación (solo firewall por IP)
# =============================================================================
set -e

# --- Parse args ---
PORT=1080
PROXY_USER="proxy"
PROXY_PASS=""
NO_AUTH=false

while [[ $# -gt 0 ]]; do
  case $1 in
    --port) PORT="$2"; shift 2 ;;
    --user) PROXY_USER="$2"; shift 2 ;;
    --pass) PROXY_PASS="$2"; shift 2 ;;
    --no-auth) NO_AUTH=true; shift ;;
    *) echo "Unknown: $1"; exit 1 ;;
  esac
done

if [ "$NO_AUTH" = false ] && [ -z "$PROXY_PASS" ]; then
  PROXY_PASS=$(tr -dc 'a-zA-Z0-9' < /dev/urandom | head -c 16)
fi

echo "=== Instalando microsocks SOCKS5 proxy ==="
echo " Puerto: $PORT"
echo " Auth:   $([ "$NO_AUTH" = true ] && echo 'NO (solo firewall)' || echo "YES user=$PROXY_USER")"
echo ""

# --- 1. Dependencias ---
echo "[1/5] Instalando dependencias..."
apt-get update -qq
apt-get install -y -qq build-essential git ufw curl 2>&1 | tail -1

# --- 2. Compilar microsocks ---
echo "[2/5] Compilando microsocks..."
cd /tmp
rm -rf microsocks
git clone https://github.com/rofl0r/microsocks.git 2>&1 | tail -1
cd microsocks
make 2>&1 | tail -1
cp microsocks /usr/local/bin/
chmod +x /usr/local/bin/microsocks
echo "  microsocks instalado en /usr/local/bin/microsocks"

# --- 3. Sistema de autenticación ---
echo "[3/5] Configurando autenticación..."
if [ "$NO_AUTH" = true ]; then
  # Sin auth - ejecutamos microsocks directamente
  CMD="/usr/local/bin/microsocks -i 0.0.0.0 -p $PORT"
else
  # Con auth - compilamos el plugin de auth
  cd /tmp/microsocks
  cat > /tmp/microsocks/auth.c << 'AUTH_EOF'
// microsocks auth plugin — valida usuario:contraseña
#include <string.h>
#include <stdio.h>
#include <stdlib.h>

#define MAX_USERS 20
static char *users[MAX_USERS];
static char *passwords[MAX_USERS];
static int user_count = 0;

// Esta función es llamada por microsocks para validar credenciales
// Retorna 0 si válido, -1 si inválido
int validate_user(const char *user, const char *pass) {
    for (int i = 0; i < user_count; i++) {
        if (strcmp(user, users[i]) == 0 && strcmp(pass, passwords[i]) == 0) {
            return 0;
        }
    }
    return -1;
}

// Inicializar desde archivo /etc/microsocks_passwd
__attribute__((constructor))
void init_users() {
    FILE *f = fopen("/etc/microsocks_passwd", "r");
    if (!f) return;
    char line[256];
    while (fgets(line, sizeof(line), f) && user_count < MAX_USERS) {
        char *sep = strchr(line, ':');
        if (!sep) continue;
        *sep = '\0';
        users[user_count] = strdup(line);
        passwords[user_count] = strdup(sep + 1);
        // Strip newline from password
        size_t len = strlen(passwords[user_count]);
        if (len > 0 && passwords[user_count][len-1] == '\n')
            passwords[user_count][len-1] = '\0';
        user_count++;
    }
    fclose(f);
}
AUTH_EOF

  # Compilamos con auth support
  cd /tmp/microsocks
  gcc -o microsocks-auth microsocks.c auth.c -lpthread 2>&1 | tail -3
  cp microsocks-auth /usr/local/bin/microsocks

  # Escribir credenciales
  echo "$PROXY_USER:$PROXY_PASS" > /etc/microsocks_passwd
  chmod 600 /etc/microsocks_passwd

  CMD="/usr/local/bin/microsocks -i 0.0.0.0 -p $PORT -A /etc/microsocks_passwd"
fi

# --- 4. Systemd service ---
echo "[4/5] Creando servicio systemd..."
cat > /etc/systemd/system/microsocks.service << SERVICE
[Unit]
Description=microsocks SOCKS5 Proxy
After=network.target

[Service]
Type=simple
ExecStart=$CMD
Restart=always
RestartSec=5
LimitNOFILE=65536

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable microsocks
systemctl restart microsocks
echo "  Servicio microsocks iniciado"

# --- 5. Firewall ---
echo "[5/5] Configurando firewall..."
ufw allow "$PORT/tcp" 2>&1 | tail -1
echo ""

# --- Resumen ---
IP=$(curl -s ifconfig.me 2>/dev/null || hostname -I | awk '{print $1}')
echo ""
echo "============================================"
echo "  PROXY SOCKS5 INSTALADO!"
echo "============================================"
echo ""
echo "  Proxy URL: socks5://$([ "$NO_AUTH" = true ] && echo "" || echo "$PROXY_USER:$PROXY_PASS@")$IP:$PORT"
echo ""
if [ "$NO_AUTH" = false ]; then
  echo "  Usuario:   $PROXY_USER"
  echo "  Password:  $PROXY_PASS"
fi
echo "  Puerto:    $PORT"
echo "  Status:    $(systemctl is-active microsocks)"
echo ""
echo "  Para probar:"
echo "    curl --socks5 $([ "$NO_AUTH" = true ] && echo "" || echo "$PROXY_USER:$PROXY_PASS@")$IP:$PORT ifconfig.me"
echo ""
echo "============================================"
