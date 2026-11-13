"""Mede a internet com o Speedtest CLI da Ookla e grava uma linha em medicoes.csv,
na pasta escolhida no painel (config.json).

E o script que o Agendador de Tarefas do Windows executa. So usa a biblioteca padrao.
"""
import csv
import json
import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path

CONFIG = Path(__file__).with_name("config.json")
CAMPOS = ["data_hora", "download_mbps", "upload_mbps", "ping_ms", "jitter_ms",
          "perda_pct", "isp", "servidor", "url", "erro"]


def config() -> dict:
    """Configuracao salva pelo painel; sem arquivo, grava ao lado do script."""
    padrao = {"pasta": str(CONFIG.parent), "contratado": 600}
    try:
        return padrao | json.loads(CONFIG.read_text("utf-8"))
    except (OSError, ValueError):
        return padrao


def caminho_csv() -> Path:
    """Lido a cada medicao: trocar a pasta no painel nao exige reagendar."""
    return Path(config()["pasta"]) / "medicoes.csv"


def achar_speedtest() -> str | None:
    """PATH primeiro; depois a pasta do winget (o PATH so atualiza em terminal novo)."""
    winget = Path(os.environ.get("LOCALAPPDATA", ""), "Microsoft", "WinGet")
    return shutil.which("speedtest") or next(map(str, winget.rglob("speedtest.exe")), None)


def interpretar(r: dict) -> dict:
    """Converte o JSON do Speedtest CLI nas colunas do CSV."""
    def mbps(bytes_por_s):  # o CLI informa a banda em bytes/s
        return round(bytes_por_s * 8 / 1e6, 2)

    return {
        "download_mbps": mbps(r["download"]["bandwidth"]),
        "upload_mbps": mbps(r["upload"]["bandwidth"]),
        "ping_ms": round(r["ping"]["latency"], 1),
        "jitter_ms": round(r["ping"]["jitter"], 1),
        "perda_pct": round(r.get("packetLoss", 0), 2),
        "isp": r.get("isp", ""),
        "servidor": f'{r["server"]["name"]} ({r["server"]["location"]})',
        "url": r.get("result", {}).get("url", ""),
    }


def medir() -> dict:
    exe = achar_speedtest()
    if not exe:  # nao e queda de internet: nao grava no CSV
        raise SystemExit("Speedtest CLI nao encontrado. Instale com: "
                         "winget install -e --id Ookla.Speedtest.CLI")

    linha = {"data_hora": datetime.now().isoformat(timespec="seconds")}
    try:
        p = subprocess.run(
            [exe, "--format=json", "--accept-license", "--accept-gdpr"],
            capture_output=True, encoding="utf-8", errors="replace", timeout=180,
            creationflags=subprocess.CREATE_NO_WINDOW,  # sem janela preta piscando
        )
        if p.returncode != 0:
            raise RuntimeError((p.stderr or p.stdout).strip().splitlines()[-1])
        linha |= interpretar(json.loads(p.stdout))
    except Exception as e:  # falhou = internet fora; isso tambem e dado, entao grava
        linha["erro"] = str(e)[:200]

    destino = caminho_csv()
    destino.parent.mkdir(parents=True, exist_ok=True)
    novo = not destino.exists()
    with destino.open("a", newline="", encoding="utf-8") as f:
        w = csv.DictWriter(f, CAMPOS)
        if novo:
            w.writeheader()
        w.writerow(linha)
    return linha


if __name__ == "__main__":
    print(medir())
