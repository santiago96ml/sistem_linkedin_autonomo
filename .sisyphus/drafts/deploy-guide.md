# Guía de Despliegue — Preuenba en Servidor Remoto

> Servidor destino: `109.176.199.140`
> Puertos: Backend `:8000`, Frontend `:3000`

---

## Opción 1 — Deploy Automático (script todo-en-uno)

### Requisitos previos en tu servidor
```bash
# Verificar que tenés lo necesario
python3 --version    # 3.9+
node --version       # 18+
git --version
curl --version
```

### 1. Conectate por SSH a tu servidor

```bash
ssh usuario@109.176.199.140
# Si usás contraseña: ssh usuario@109.176.199.140
# Te va a pedir la contraseña
```

### 2. Descargar y ejecutar script de deploy

```bash
# Pararte en donde quieras instalar
cd /opt  # o ~/apps, o donde prefieras

# Descargar script
curl -O https://raw.githubusercontent.com/santiago96ml/sistem_linkedin_autonomo/main/scripts/deploy.sh
# O crealo manualmente (copiando el contenido de abajo)

# Dar permisos y ejecutar
chmod +x deploy.sh
./deploy.sh
```

### 3. Script de Deploy (`deploy.sh`)

Creá este archivo en tu servidor:

```bash
#!/bin/bash
set -e

echo "=== Instalando Preuenba LinkedIn Intelligence Hub ==="

# 1. Dependencias del sistema
echo "[1/6] Instalando dependencias del sistema..."
apt-get update -qq
apt-get install -y -qq python3 python3-pip python3-venv nodejs npm git curl nginx 2>&1 | tail -3

# 2. Clonar repositorio
echo "[2/6] Clonando repositorio..."
if [ -d "preuenba" ]; then
  cd preuenba && git pull
else
  git clone https://github.com/santiago96ml/sistem_linkedin_autonomo.git preuenba
  cd preuenba
fi

# 3. Backend
echo "[3/6] Configurando backend..."
cd orchestrator-center/backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
playwright install chromium 2>&1 | tail -3
deactivate

# 4. Frontend
echo "[4/6] Configurando frontend..."
cd ../frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://109.176.199.140:8000" > .env.local
npm run build

# 5. Crear servicios systemd
echo "[5/6] Creando servicios systemd..."

# Backend service
cat > /etc/systemd/system/preuenba-backend.service << 'SERVICE'
[Unit]
Description=Preuenba Backend API
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/preuenba/orchestrator-center/backend
ExecStart=/opt/preuenba/orchestrator-center/backend/venv/bin/uvicorn main:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
SERVICE

# Frontend service
cat > /etc/systemd/system/preuenba-frontend.service << 'SERVICE'
[Unit]
Description=Preuenba Frontend
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/preuenba/orchestrator-center/frontend
ExecStart=/usr/bin/npx next start -p 3000
Restart=always
RestartSec=5
Environment=NEXT_PUBLIC_API_URL=http://109.176.199.140:8000

[Install]
WantedBy=multi-user.target
SERVICE

systemctl daemon-reload
systemctl enable preuenba-backend preuenba-frontend
systemctl start preuenba-backend preuenba-frontend

# 6. Configurar firewall
echo "[6/6] Configurando firewall..."
ufw allow 22/tcp    # SSH
ufw allow 8000/tcp  # Backend API
ufw allow 3000/tcp  # Frontend
ufw --force enable

echo ""
echo "============================================"
echo "  DEPLOY COMPLETADO!"
echo "============================================"
echo ""
echo "  Frontend: http://109.176.199.140:3000"
echo "  Backend:  http://109.176.199.140:8000"
echo "  API Docs: http://109.176.199.140:8000/docs"
echo ""
echo "  Para ver logs:"
echo "    journalctl -u preuenba-backend -f"
echo "    journalctl -u preuenba-frontend -f"
echo ""
echo "  Para reiniciar:"
echo "    systemctl restart preuenba-backend"
echo "    systemctl restart preuenba-frontend"
echo ""
echo "============================================"
```

---

## Opción 2 — Deploy Manual (paso a paso)

Si preferís hacerlo manual para tener control total:

### 1. Conectate al servidor

```bash
ssh usuario@109.176.199.140
```

### 2. Instalar dependencias

```bash
# Python 3 y pip
apt-get update
apt-get install -y python3 python3-pip python3-venv

# Node.js 18+
curl -fsSL https://deb.nodesource.com/setup_18.x | bash -
apt-get install -y nodejs

# Git
apt-get install -y git

# Nginx (opcional, para producción)
apt-get install -y nginx
```

### 3. Clonar y configurar backend

```bash
git clone https://github.com/santiago96ml/sistem_linkedin_autonomo.git preuenba
cd preuenba/orchestrator-center/backend

python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Instalar Playwright browsers
playwright install chromium

# Probar que funciona
uvicorn main:app --host 0.0.0.0 --port 8000
# Ctrl+C para detener
```

### 4. Configurar frontend

```bash
cd preuenba/orchestrator-center/frontend
npm install
echo "NEXT_PUBLIC_API_URL=http://109.176.199.140:8000" > .env.local
npm run build

# Probar
npx next start -p 3000
```

### 5. Configurar como servicios (systemd)

```bash
# Backend
nano /etc/systemd/system/preuenba-backend.service
# Pegar el contenido de arriba (la sección backend service)

# Frontend
nano /etc/systemd/system/preuenba-frontend.service
# Pegar el contenido de arriba (la sección frontend service)

# Habilitar e iniciar
systemctl daemon-reload
systemctl enable preuenba-backend preuenba-frontend
systemctl start preuenba-backend preuenba-frontend
systemctl status preuenba-backend
systemctl status preuenba-frontend
```

### 6. Abrir puertos en firewall

```bash
ufw allow 22/tcp
ufw allow 8000/tcp
ufw allow 3000/tcp
ufw --force enable
```

---

## Opción 3 — Usando Docker Compose (si tu servidor tiene Docker)

```bash
# Instalar Docker
curl -fsSL https://get.docker.com | bash

# Clonar y ejecutar
git clone https://github.com/santiago96ml/sistem_linkedin_autonomo.git
cd preuenba
docker compose up --build -d

# Verificar
docker compose ps
docker compose logs -f
```

---

## Post-Deploy: Verificar que funciona

### Backend
```bash
curl http://localhost:8000/
# → {"status":"LinkedIn Orchestrator Online"}

curl http://localhost:8000/proxies/
# → [] (vacío, hay que agregar proxies)

curl http://localhost:8000/stats
# → métricas iniciales
```

### Frontend
```bash
curl http://localhost:3000/
# → Debe responder HTML (puede tardar en primera carga)
```

### Playwright (crítico)
```bash
cd /opt/preuenba/orchestrator-center/backend
source venv/bin/activate

# Verificar que Playwright puede lanzar Chromium
python -c "
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    b = p.chromium.launch(headless=True)
    print('Playwright OK, version:', b.version)
    b.close()
"
```

---

## Después del Deploy: Siguientes Pasos

### 1. Agregar proxies

Seguir la guía en la sección 6.2 de la documentación principal:
- Crear VPS en Oracle Cloud Free Tier
- Instalar microsocks con `scripts/install_proxy.sh`
- Agregar en UI → Proxies → Añadir Proxy

### 2. Vincular cuentas

- Ir a http://109.176.199.140:3000
- Account Registry → Vincular Nueva
- Elegir método: credenciales o cookies

### 3. Configurar AutoPilot (opcional)

- Ir a Piloto Automático
- Agregar perfiles objetivo
- Configurar horarios y keywords

---

## Troubleshooting de Deploy

### Error: `playwright install chromium` falla
```bash
# Instalar dependencias de sistema para Chromium
apt-get install -y ca-certificates fonts-liberation libappindicator3-1 libasound2 \
  libatk-bridge2.0-0 libatk1.0-0 libcups2 libdbus-1-3 libgdk-pixbuf2.0-0 \
  libnspr4 libnss3 libx11-xcb1 libxcomposite1 libxdamager1 libxrandr2 \
  xdg-utils libgbm1
```

### Error: `uvicorn` no encontrado
```bash
# Asegurarse de activar el venv
cd /opt/preuenba/orchestrator-center/backend
source venv/bin/activate
which uvicorn  # Debe mostrar el path dentro de venv
```

### Error: EADDRINUSE (puerto ocupado)
```bash
# Ver qué está usando el puerto
lsof -i :8000
lsof -i :3000
# Matar proceso
kill -9 PID
```

### Error: Frontend no conecta con backend
```bash
# Verificar que el archivo .env.local tenga la IP correcta
cat /opt/preuenba/orchestrator-center/frontend/.env.local
# Debe decir: NEXT_PUBLIC_API_URL=http://109.176.199.140:8000
# Luego rebuild: cd /opt/preuenba/orchestrator-center/frontend && npm run build
```

---

*Documentación de deploy generada el 15 de mayo de 2026*
