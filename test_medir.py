"""Checagem minima: rode `python test_medir.py`."""
from medir import interpretar

amostra = {
    "ping": {"jitter": 1.234, "latency": 8.76},
    "download": {"bandwidth": 10_000_000},  # bytes/s -> 80 Mbps
    "upload": {"bandwidth": 37_500_000},    # bytes/s -> 300 Mbps
    "packetLoss": 0,
    "isp": "Operadora",
    "server": {"name": "Servidor", "location": "São Paulo"},
    "result": {"url": "https://www.speedtest.net/result/c/abc"},
}
r = interpretar(amostra)
assert r["download_mbps"] == 80.0, r
assert r["upload_mbps"] == 300.0, r
assert (r["ping_ms"], r["jitter_ms"]) == (8.8, 1.2), r
assert r["servidor"] == "Servidor (São Paulo)", r
assert interpretar({**amostra, "packetLoss": 1.5})["perda_pct"] == 1.5
del amostra["packetLoss"], amostra["result"]  # campos opcionais ausentes
assert interpretar(amostra)["url"] == ""

# Intervalo do agendamento (precisa do nicegui: rode com .venv\Scripts\python)
from app import minutos_iso

assert minutos_iso("PT30M") == 30 and minutos_iso("PT1H") == 60 and minutos_iso("PT1H30M") == 90
assert minutos_iso("P1D") is None and minutos_iso("PT") is None
print("ok")
