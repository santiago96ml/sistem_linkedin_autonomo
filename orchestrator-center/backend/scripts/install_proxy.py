#!/usr/bin/env python3
"""
install_proxy.py — Automatiza instalación de microsocks en VPS vía SSH.

Uso:
  python install_proxy.py --host 1.2.3.4 --user root --port 1080
  python install_proxy.py --host 1.2.3.4 --user root --no-auth

Requiere: paramiko (pip install paramiko)
"""
import argparse
import os
import sys
import subprocess
import random
import string

try:
    import paramiko
except ImportError:
    print("ERROR: Necesitás paramiko. Instalá: pip install paramiko")
    sys.exit(1)


def generate_password(length=16):
    return ''.join(random.choices(string.ascii_letters + string.digits, k=length))


def run_ssh(host, port, ssh_user, ssh_key, command):
    """Ejecuta un comando vía SSH y devuelve stdout."""
    client = paramiko.SSHClient()
    client.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    connect_kwargs = {"hostname": host, "port": port, "username": ssh_user}
    if ssh_key:
        connect_kwargs["key_filename"] = os.path.expanduser(ssh_key)
    else:
        connect_kwargs["look_for_keys"] = True
        connect_kwargs["allow_agent"] = True

    client.connect(**connect_kwargs)
    stdin, stdout, stderr = client.exec_command(command, timeout=120)
    exit_code = stdout.channel.recv_exit_status()
    out = stdout.read().decode().strip()
    err = stderr.read().decode().strip()
    client.close()

    if exit_code != 0:
        print(f"  [WARN] Exit code {exit_code}: {err[:200]}")
    return out, err, exit_code


def install_proxy(host, ssh_port, ssh_user, ssh_key, proxy_port, proxy_user, proxy_pass, no_auth):
    """Instala microsocks vía SSH."""
    print(f" Conectando a {ssh_user}@{host}:{ssh_port}...")

    # Build install command
    cmd_parts = ["bash -s"]
    if no_auth:
        cmd_parts.append("--no-auth")
    else:
        cmd_parts.extend([f"--port {proxy_port}", f"--user {proxy_user}"])
        if proxy_pass:
            cmd_parts.append(f"--pass '{proxy_pass}'")

    # Read the bash script
    script_dir = os.path.dirname(os.path.abspath(__file__))
    script_path = os.path.join(script_dir, "install_proxy.sh")
    if not os.path.exists(script_path):
        print(f"ERROR: No encuentro install_proxy.sh en {script_dir}")
        sys.exit(1)

    with open(script_path) as f:
        script_content = f.read()

    # Execute via SSH
    print(" Transfiriendo script e instalando microsocks...")
    transport = paramiko.Transport((host, ssh_port))
    if ssh_key:
        key = paramiko.RSAKey.from_private_key_file(os.path.expanduser(ssh_key))
        transport.connect(username=ssh_user, pkey=key)
    else:
        transport.connect(username=ssh_user)

    session = transport.open_session()
    session.exec_command("bash -s " + " ".join(cmd_parts[2:]))
    session.send(script_content.encode())
    session.shutdown_write()

    stdout_data = session.makefile("r", -1).read()
    stderr_data = session.makefile_stderr("r", -1).read()
    exit_code = session.recv_exit_status()
    transport.close()

    print(stdout_data)
    if stderr_data:
        print(f"[STDERR] {stderr_data[:500]}")

    # Parse output for proxy URL
    for line in stdout_data.split("\n"):
        if "Proxy URL:" in line:
            url = line.split("Proxy URL:")[1].strip()
            print(f"\n Proxy URL: {url}")
            return url

    return None


def main():
    parser = argparse.ArgumentParser(description="Instalar microsocks SOCKS5 en VPS")
    parser.add_argument("--host", required=True, help="IP del VPS")
    parser.add_argument("--ssh-port", type=int, default=22, help="Puerto SSH (default: 22)")
    parser.add_argument("--ssh-user", default="root", help="Usuario SSH (default: root)")
    parser.add_argument("--ssh-key", default=None, help="Ruta a clave SSH privada")
    parser.add_argument("--port", type=int, default=1080, help="Puerto proxy (default: 1080)")
    parser.add_argument("--user", default="proxy", help="Usuario proxy (default: proxy)")
    parser.add_argument("--pass", dest="proxy_pass", default=None, help="Contraseña proxy (default: random)")
    parser.add_argument("--no-auth", action="store_true", help="Proxy sin autenticación")
    args = parser.parse_args()

    if not args.proxy_pass and not args.no_auth:
        args.proxy_pass = generate_password()

    url = install_proxy(
        host=args.host,
        ssh_port=args.ssh_port,
        ssh_user=args.ssh_user,
        ssh_key=args.ssh_key,
        proxy_port=args.port,
        proxy_user=args.user,
        proxy_pass=args.proxy_pass,
        no_auth=args.no_auth,
    )

    if url:
        print(f"\n Proxy lista! Agregala en la UI de Proxies.")
    else:
        print("\n No se pudo extraer la URL. Revisá el output arriba.")


if __name__ == "__main__":
    main()
