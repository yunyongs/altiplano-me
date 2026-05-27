"""
Power BI Refresh Pipeline / Pipeline de Actualización de Power BI
Launches PBI Desktop, connects via MCP, and provides refresh orchestration.
Abre PBI Desktop, conecta vía MCP y orquesta la actualización de datos.
"""
import subprocess
import time
import os
import sys
import json
import socket

# --- Configuration / Configuración ---
PBIP_PATH = os.path.join(
    os.path.dirname(__file__),
    "03_PowerBI_Dashboard", "AR_Dashboard.pbip"
)
TMDL_FOLDER = os.path.join(
    os.path.dirname(__file__),
    "03_PowerBI_Dashboard", "AR_Dashboard.SemanticModel", "definition"
)
PBI_DESKTOP_EXE = r"C:\Program Files\Microsoft Power BI Desktop\bin\PBIDesktop.exe"
PBI_DESKTOP_STORE = os.path.join(
    os.environ.get("LOCALAPPDATA", ""),
    "Microsoft", "WindowsApps", "PBIDesktopStore.exe"
)


def find_pbi_executable():
    """Find Power BI Desktop executable / Buscar ejecutable de PBI Desktop."""
    for path in [PBI_DESKTOP_EXE, PBI_DESKTOP_STORE]:
        if os.path.exists(path):
            return path
    # Try via PATH
    for cmd in ["PBIDesktop.exe", "PBIDesktopStore.exe"]:
        result = subprocess.run(
            ["where", cmd], capture_output=True, text=True, shell=True
        )
        if result.returncode == 0:
            return result.stdout.strip().split("\n")[0]
    return None


def find_pbi_port(pbip_path=None):
    """Scan for PBI Desktop Analysis Services port / Buscar puerto AS de PBI Desktop.
    PBI Desktop runs a local SSAS instance on a dynamic port (usually 49xxx-65xxx).
    The port is stored in a .port.txt file in LOCALAPPDATA.
    If pbip_path is given, try to match the workspace to that project.
    """
    local_app = os.environ.get("LOCALAPPDATA", "")
    port_dir = os.path.join(
        local_app, "Microsoft", "Power BI Desktop", "AnalysisServicesWorkspaces"
    )
    if not os.path.exists(port_dir):
        return None

    found_ports = []
    for workspace in os.listdir(port_dir):
        port_file = os.path.join(port_dir, workspace, "Data", "msmdsrv.port.txt")
        if os.path.exists(port_file):
            with open(port_file, "r") as f:
                port = f.read().strip()
            if port.isdigit():
                found_ports.append({"workspace": workspace, "port": int(port)})

    if not found_ports:
        return None

    # If only one workspace, return it directly
    if len(found_ports) == 1:
        return found_ports[0]["port"]

    # If pbip_path provided, try to correlate
    if pbip_path:
        pbip_name = os.path.splitext(os.path.basename(pbip_path))[0].lower()
        for entry in found_ports:
            if pbip_name in entry["workspace"].lower():
                return entry["port"]

    # Fallback: return first (with logged warning)
    return found_ports[0]["port"]


def is_port_open(port, host="localhost", timeout=2):
    """Check if a port is open / Verificar si el puerto está abierto."""
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except (OSError, ConnectionRefusedError):
        return False


def launch_pbi_desktop(pbip_path=None):
    """Launch Power BI Desktop / Abrir Power BI Desktop.
    Returns True if launched, False if not found.
    """
    exe = find_pbi_executable()
    if not exe:
        print("ERROR: Power BI Desktop not found / No se encontró PBI Desktop")
        print("  Install from: https://powerbi.microsoft.com/desktop/")
        return False

    target = pbip_path or PBIP_PATH
    if not os.path.exists(target):
        print(f"ERROR: File not found / Archivo no encontrado: {target}")
        return False

    print(f"Launching PBI Desktop / Abriendo PBI Desktop...")
    print(f"  Executable: {exe}")
    print(f"  File: {target}")
    subprocess.Popen([exe, target])
    return True


def wait_for_pbi(max_wait=120, poll_interval=5):
    """Wait for PBI Desktop to start its AS engine / Esperar que PBI Desktop inicie AS.
    Returns the port number or None.
    """
    print(f"Waiting for PBI Desktop AS engine (max {max_wait}s)...")
    print("  Esperando que el motor AS de PBI Desktop inicie...")
    elapsed = 0
    while elapsed < max_wait:
        port = find_pbi_port()
        if port and is_port_open(port):
            print(f"  PBI Desktop AS engine ready on port {port}")
            return port
        time.sleep(poll_interval)
        elapsed += poll_interval
        print(f"  ...waiting ({elapsed}s)")
    print("  TIMEOUT: PBI Desktop AS engine not detected")
    return None


def get_connection_string(port):
    """Build MSOLAP connection string / Construir cadena de conexión MSOLAP."""
    return f"Provider=MSOLAP;Data Source=localhost:{port}"


def print_mcp_instructions(port):
    """Print MCP connection and refresh instructions for VS Code Copilot."""
    conn_str = get_connection_string(port)
    print("\n" + "=" * 70)
    print("PBI Desktop is ready! Use these MCP commands in VS Code Copilot:")
    print("PBI Desktop está listo! Use estos comandos MCP en VS Code Copilot:")
    print("=" * 70)
    print(f"""
1. CONNECT / CONECTAR:
   connection_operations -> Connect
   ConnectionString: "{conn_str}"

2. REFRESH ALL / ACTUALIZAR TODO:
   database_operations -> List  (to see the database name)
   Then use partition_operations -> Refresh for each table

3. VERIFY / VERIFICAR:
   dax_query_operations -> Execute
   Query: "EVALUATE ROW(\\"RowCount\\", COUNTROWS('Tbl_Actvdd_m_e_data'))"
""")


def print_status():
    """Print current status / Imprimir estado actual."""
    print("\n--- Power BI Refresh Pipeline Status ---")
    print("--- Estado del Pipeline de Actualización ---\n")

    # Check PBI Desktop
    port = find_pbi_port()
    if port and is_port_open(port):
        print(f"  PBI Desktop: RUNNING on port {port}")
        print_mcp_instructions(port)
    else:
        print("  PBI Desktop: NOT RUNNING / NO ESTÁ CORRIENDO")

    # Check PBIP file
    if os.path.exists(PBIP_PATH):
        print(f"  PBIP file: OK ({PBIP_PATH})")
    else:
        print(f"  PBIP file: NOT FOUND / NO ENCONTRADO")

    # Check TMDL folder
    if os.path.exists(os.path.join(TMDL_FOLDER, "database.tmdl")):
        print(f"  TMDL folder: OK")
    else:
        print(f"  TMDL folder: NOT FOUND / NO ENCONTRADO")

    # Check BasePath
    expr_file = os.path.join(TMDL_FOLDER, "expressions.tmdl")
    if os.path.exists(expr_file):
        with open(expr_file, "r", encoding="utf-8") as f:
            content = f.read()
        if "BasePath" in content:
            # Extract BasePath value
            for line in content.split("\n"):
                if line.startswith("expression BasePath"):
                    # Extract the quoted string
                    start = line.find('"')
                    end = line.find('"', start + 1)
                    if start > 0 and end > start:
                        bp = line[start + 1:end]
                        exists = os.path.exists(bp)
                        print(f"  BasePath: {bp}")
                        print(f"  BasePath exists: {'YES' if exists else 'NO / Path not found'}")
                    break
        else:
            print("  BasePath: NOT CONFIGURED / NO CONFIGURADO")


def main():
    if len(sys.argv) < 2:
        print("Usage / Uso: python pbi_refresh.py <command>")
        print("Commands / Comandos:")
        print("  status    - Show pipeline status / Mostrar estado")
        print("  launch    - Open PBI Desktop with .pbip / Abrir PBI Desktop")
        print("  wait      - Wait for PBI Desktop AS engine / Esperar motor AS")
        print("  full      - Launch + wait + show instructions / Lanzar + esperar")
        return

    cmd = sys.argv[1].lower()

    if cmd == "status":
        print_status()
    elif cmd == "launch":
        launch_pbi_desktop()
    elif cmd == "wait":
        port = wait_for_pbi()
        if port:
            print_mcp_instructions(port)
    elif cmd == "full":
        if launch_pbi_desktop():
            port = wait_for_pbi()
            if port:
                print_mcp_instructions(port)
    else:
        print(f"Unknown command / Comando desconocido: {cmd}")


if __name__ == "__main__":
    main()
