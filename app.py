"""Painel do Internet Check. Rode com: python app.py (ou de dois cliques no iniciar.bat)."""
import csv
import json
import re
import shutil
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from statistics import mean

from nicegui import run, ui

import medir

TAREFA = "InternetCheck"
INTERVALOS = {5: "5 minutos", 10: "10 minutos", 15: "15 minutos", 30: "30 minutos",
              60: "1 hora", 120: "2 horas", 360: "6 horas", 720: "12 horas"}
PERIODOS = {"Hoje": 0, "7 dias": 7, "30 dias": 30, "Tudo": None}
NUMERICOS = ["download_mbps", "upload_mbps", "ping_ms", "jitter_ms", "perda_pct"]
SEM_JANELA = subprocess.CREATE_NO_WINDOW
SELETOR = ("import tkinter as tk, tkinter.filedialog as fd; r = tk.Tk(); r.withdraw(); "
           "r.attributes('-topmost', True); print(fd.askdirectory(title='Onde salvar as medições?'))")

# Paleta: series em ordem fixa, cores de status reservadas para status.
# As cores da pagina ficam no CSS (variaveis); aqui ficam as que o ECharts precisa receber prontas.
MUDO = "#898781"
BOM, ALERTA, CRITICO = "#0ca30c", "#fab219", "#d03b3b"
TEMAS = {
    True: dict(PAGINA="#0d0d0d", SUPERFICIE="#1a1a19", TINTA="#f0efec", TINTA2="#c3c2b7", GRADE="#2c2c2a",
               LINHA_EIXO="#383835", FUNDO_DICA="#232322", AZUL="#3987e5", LARANJA="#d95926", VERDE="#199e70"),
    False: dict(PAGINA="#f4f4f1", SUPERFICIE="#ffffff", TINTA="#0b0b0b", TINTA2="#52514e", GRADE="#e1e0d9",
                LINHA_EIXO="#c3c2b7", FUNDO_DICA="#ffffff", AZUL="#2a78d6", LARANJA="#eb6834", VERDE="#1baf7a"),
}


def aplicar_tema(escuro: bool) -> None:
    # ponytail: paleta global do processo (app local, um usuario). Se virar multiusuario, passar por cliente.
    g = globals()
    g.update(TEMAS[escuro])
    g["EIXO"] = {"axisLine": {"lineStyle": {"color": LINHA_EIXO}}, "axisTick": {"show": False},
                 "axisLabel": {"color": MUDO}, "splitLine": {"lineStyle": {"color": GRADE}}}
    g["EIXO_TEMPO"] = EIXO | {"type": "time", "splitLine": {"show": False}, "splitNumber": 5,
                              "axisLabel": {"color": MUDO, "formatter": "{dd}/{MM} {HH}h", "hideOverlap": True}}
    g["DICA"] = {"trigger": "axis", "backgroundColor": FUNDO_DICA, "borderColor": GRADE,
                 "textStyle": {"color": TINTA, "fontSize": 13}, "axisPointer": {"lineStyle": {"color": MUDO}}}


aplicar_tema(True)

FAVICON = ('<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24"><rect width="24" height="24" rx="6" fill="#3987e5"/>'
           '<g fill="#fff"><rect x="5" y="13" width="3.4" height="6" rx="1"/><rect x="10.3" y="9" width="3.4" height="10" rx="1"/>'
           '<rect x="15.6" y="5" width="3.4" height="14" rx="1"/></g></svg>')

# Sol que vira lua: a sombra desliza sobre o nucleo e os raios se recolhem (CSS em .tema-botao)
ICONE_TEMA = """<svg viewBox="0 0 24 24" width="20" height="20" aria-hidden="true" focusable="false">
  <mask id="lua"><rect width="24" height="24" fill="#fff"/><circle class="sombra" cx="17.5" cy="6.5" r="6.5" fill="#000"/></mask>
  <circle class="nucleo" cx="12" cy="12" r="8" fill="currentColor" mask="url(#lua)"/>
  <g class="raios" stroke="currentColor" stroke-width="1.6" stroke-linecap="round">
    <path d="M12 1.8v2.4M12 19.8v2.4M1.8 12h2.4M19.8 12h2.4M4.8 4.8l1.7 1.7M17.5 17.5l1.7 1.7M4.8 19.2l1.7-1.7M17.5 6.5l1.7-1.7"/>
  </g>
</svg>"""

CSS = """
/* Troca de tema: o tema novo e revelado por um circulo que cresce a partir do botao (animado no JS) */
::view-transition { pointer-events: none; }
html[data-theming]::view-transition-old(root), html[data-theming]::view-transition-new(root) { animation: none; mix-blend-mode: normal; }
html[data-theming] body, html[data-theming] .cartao { transition: none !important; animation: none !important; }

/* Scroll: a barra nativa e substituida por um trilho fino (montado no JS), como no luis-dev-portfolio */
* { scrollbar-width: thin; scrollbar-color: var(--borda-forte) transparent; }  /* barras internas (tabela, gaveta) */
html { scrollbar-width: none; }
html::-webkit-scrollbar { display: none; }
.trilho { position: fixed; top: 72px; right: 6px; bottom: 12px; z-index: 2100; width: 2px; border-radius: 2px;
          background: var(--borda-forte); pointer-events: none; opacity: .55; transition: opacity .4s ease; }
.trilho[data-active] { opacity: 1; }
.trilho[data-hidden] { opacity: 0; }
.trilho span { position: absolute; inset: 0 0 auto; height: var(--thumb-size, 36px); border-radius: 2px; background: var(--azul);
               transform: translate3d(0, var(--thumb-y, 0), 0); transition: height .25s ease; }

.tema-botao { display: inline-grid; place-items: center; width: 38px; height: 38px; border: 0; border-radius: 999px; cursor: pointer;
              background: transparent; color: var(--tinta); transition: background-color .2s ease; }
.tema-botao:hover { background: var(--borda); }
.tema-botao svg { overflow: visible; transition: transform .3s cubic-bezier(.2,.8,.2,1); }
.tema-botao:active svg { transform: scale(.88) rotate(-12deg); }
.tema-botao .nucleo, .tema-botao .sombra, .tema-botao .raios { transform-box: fill-box; transform-origin: center;
                                                               transition: transform 640ms cubic-bezier(.2,.8,.2,1); }
.tema-botao .nucleo { transform: scale(.56); }                 /* escuro: mostra o sol */
.tema-botao .sombra { transform: translate(9px, -9px); }
body.body--light .tema-botao .nucleo { transform: scale(.9); } /* claro: mostra a lua */
body.body--light .tema-botao .sombra { transform: none; }
body.body--light .tema-botao .raios { transform: rotate(-90deg) scale(0); }

body { --pagina: #0d0d0d; --superficie: #1a1a19; --lateral: #131312; --cabecalho: rgba(13,13,13,.72);
       --tinta: #f0efec; --tinta2: #c3c2b7; --mudo: #898781; --azul: #3987e5;
       --borda: rgba(255,255,255,.08); --borda-forte: rgba(255,255,255,.18); --sombra: 0 10px 30px rgba(0,0,0,.35); }
body.body--light { --pagina: #f4f4f1; --superficie: #ffffff; --lateral: #fbfbf9; --cabecalho: rgba(244,244,241,.78);
       --tinta: #0b0b0b; --tinta2: #52514e; --mudo: #73716b; --azul: #2a78d6;
       --borda: rgba(11,11,11,.10); --borda-forte: rgba(11,11,11,.22); --sombra: 0 10px 30px rgba(11,11,11,.10); }
body, body.body--light, body.body--dark { background: var(--pagina); color: var(--tinta); transition: background .3s ease, color .3s ease; font-family: "Segoe UI Variable Text", "Segoe UI", system-ui, sans-serif; }
.q-header.cabecalho { color: var(--tinta); background: var(--cabecalho); backdrop-filter: blur(14px); border-bottom: 1px solid var(--borda);
                      padding: 10px 24px; gap: 12px; }
.logo { width: 34px; height: 34px; border-radius: 10px; display: grid; place-items: center; font-size: 20px;
        background: linear-gradient(135deg, var(--azul), #1c5cab); color: #fff; }
.titulo { font-size: 17px; font-weight: 600; letter-spacing: -.01em; }
.q-drawer { background: var(--lateral) !important; border-right: 1px solid var(--borda); }
.lateral { padding: 20px 18px; gap: 10px; }
.secao { display: flex; align-items: center; gap: 8px; margin-top: 14px; font-size: 11px; font-weight: 600;
         letter-spacing: .08em; text-transform: uppercase; color: var(--mudo); }
.secao .q-icon { font-size: 16px; }
.caminho { font: 12px/1.5 "Cascadia Code", Consolas, monospace; color: var(--tinta2); word-break: break-all;
           background: var(--superficie); border: 1px solid var(--borda); border-radius: 10px; padding: 10px 12px; width: 100%; }
.nota { font-size: 12px; line-height: 1.5; color: var(--mudo); }

.conteudo { padding: 24px; gap: 16px; max-width: 1500px; margin: 0 auto; width: 100%; overflow-x: clip; }
.painel { display: flex; flex-direction: column; gap: 16px; width: 100%; }
.painel.vai-dir { animation: entra-dir .45s cubic-bezier(.2,.8,.2,1); }
.painel.vai-esq { animation: entra-esq .45s cubic-bezier(.2,.8,.2,1); }
.painel.vai-dir .cartao, .painel.vai-esq .cartao, .painel.sem-entrada .cartao { animation: none; }
@keyframes entra-dir { from { opacity: 0; transform: translateX(56px); } }
@keyframes entra-esq { from { opacity: 0; transform: translateX(-56px); } }

.periodo { background: var(--superficie); border: 1px solid var(--borda); border-radius: 999px; padding: 4px; }
.periodo .q-tab { min-height: 34px; padding: 0 18px; border-radius: 999px; color: var(--mudo); transition: color .25s ease; }
.periodo .q-tab--active { color: #fff; }
.periodo .q-tab__content { position: relative; z-index: 1; }
.periodo .q-tab__label { font-size: 13px; font-weight: 600; }
.periodo .q-tab__indicator { height: 100%; border-radius: 999px; }
.cartao { background: var(--superficie); border: 1px solid var(--borda); border-radius: 16px; padding: 18px 20px;
          animation: subir .55s cubic-bezier(.2,.8,.2,1) backwards; animation-delay: calc(var(--i, 0) * 55ms);
          transition: transform .2s ease, border-color .2s ease, box-shadow .2s ease; }
.cartao:hover { transform: translateY(-2px); border-color: var(--borda-forte); box-shadow: var(--sombra); }
@keyframes subir { from { opacity: 0; transform: translateY(14px); } }

.grade-topo { display: grid; grid-template-columns: minmax(280px, 1.15fr) repeat(3, 1fr); gap: 16px; width: 100%; }
.destaque { grid-row: span 2; display: flex; flex-direction: column; align-items: center;
            background: radial-gradient(120% 90% at 50% 0%, rgba(57,135,229,.14), transparent 60%), var(--superficie); }
.grade-dupla { display: grid; grid-template-columns: 1fr 1fr; gap: 16px; width: 100%; }
@media (max-width: 1100px) { .grade-topo { grid-template-columns: repeat(2, 1fr); } .destaque { grid-column: span 2; }
                             .grade-dupla { grid-template-columns: 1fr; } }

.kpi-icone { width: 38px; height: 38px; border-radius: 11px; display: grid; place-items: center; font-size: 20px; margin-bottom: 14px; }
.kpi-rotulo { font-size: 13px; color: var(--tinta2); }
.kpi-valor { font-size: 34px; font-weight: 600; letter-spacing: -.02em; line-height: 1.15; }
.kpi-unidade { font-size: 14px; color: var(--mudo); }
.cartao-titulo { display: flex; align-items: center; gap: 8px; font-size: 15px; font-weight: 600; margin-bottom: 4px; }
.cartao-titulo .q-icon { font-size: 19px; color: var(--mudo); }
.veredito { display: flex; align-items: center; gap: 6px; font-size: 14px; font-weight: 600; }
.sub { font-size: 12.5px; color: var(--mudo); text-align: center; margin-top: 6px; }

.selo { display: flex; align-items: center; gap: 8px; font-size: 13px; color: var(--tinta2); padding: 6px 12px;
        border: 1px solid var(--borda); border-radius: 999px; }
.ponto { width: 8px; height: 8px; border-radius: 50%; background: var(--mudo); }
.ponto.ativo { background: #0ca30c; animation: pulso 1.8s ease-out infinite; }
@keyframes pulso { from { box-shadow: 0 0 0 0 rgba(12,163,12,.65); } to { box-shadow: 0 0 0 9px rgba(12,163,12,0); } }

.q-table__card { background: transparent !important; box-shadow: none !important; color: var(--tinta); }
.q-table th { color: var(--mudo); font-weight: 600; }
.q-table td, .q-table th { border-color: var(--borda) !important; font-variant-numeric: tabular-nums; }
.q-table tbody tr { transition: background .15s ease; }
.link-prova { color: var(--azul); text-decoration: none; display: inline-flex; align-items: center; gap: 4px; }
.link-prova:hover { text-decoration: underline; }
.vazio { align-items: center; text-align: center; padding: 70px 20px; gap: 12px; }
.vazio .q-icon { font-size: 56px; color: var(--azul); animation: flutuar 3s ease-in-out infinite; }
@keyframes flutuar { 50% { transform: translateY(-8px); } }

@media (prefers-reduced-motion: reduce) { *, *::before, *::after { animation: none !important; transition: none !important; } }
"""

# Faz os numeros dos KPIs contarem de 0 ate o valor sempre que um cartao novo entra na tela
JS = """
// Troca de tema com onda circular (View Transition), portada do luis-dev-portfolio.
// O servidor redesenha os graficos, entao a transicao espera o aviso dele (__temaPronto) antes de revelar.
let trocandoTema = false;
function trocarTema() {
  if (trocandoTema) return;
  const escuro = !document.body.classList.contains('body--dark');
  const aplicar = () => new Promise(ok => { window.__temaPronto = ok; emitEvent('tema', {escuro}); setTimeout(ok, 1500); })
    .then(() => new Promise(ok => setTimeout(ok, 80)));  // folga para o Vue aplicar a classe e o canvas pintar
  if (!document.startViewTransition || matchMedia('(prefers-reduced-motion: reduce)').matches) { aplicar(); return; }
  const r = document.querySelector('.tema-botao').getBoundingClientRect();
  const x = r.left + r.width / 2, y = r.top + r.height / 2;
  const raio = Math.hypot(Math.max(x, innerWidth - x), Math.max(y, innerHeight - y));
  const raiz = document.documentElement;
  trocandoTema = true;
  raiz.dataset.theming = '';
  const transicao = document.startViewTransition(aplicar);
  transicao.ready.then(() => {
    raiz.animate({clipPath: [`circle(0px at ${x}px ${y}px)`, `circle(${raio}px at ${x}px ${y}px)`]},
      {duration: 1000, easing: 'cubic-bezier(0.65, 0, 0.25, 1)', pseudoElement: '::view-transition-new(root)', fill: 'both'});
    raiz.animate({filter: ['brightness(1)', 'brightness(0.72)']},
      {duration: 1000, easing: 'ease-in', pseudoElement: '::view-transition-old(root)', fill: 'both'});
  }).catch(() => {});
  transicao.finished.finally(() => { delete raiz.dataset.theming; trocandoTema = false; });
}

// Trilho de scroll: o marcador mostra onde voce esta na pagina e acende enquanto rola.
// So decorativo: a rolagem em si (roda, toque, teclado) continua nativa.
document.addEventListener('DOMContentLoaded', () => {
  const trilho = document.createElement('div');
  trilho.className = 'trilho';
  trilho.setAttribute('aria-hidden', 'true');
  trilho.appendChild(document.createElement('span'));
  document.body.appendChild(trilho);
  let quadro = 0, parado = 0;
  const atualizar = () => {
    quadro = 0;
    const doc = document.documentElement, max = doc.scrollHeight - innerHeight;
    if (max <= 4) { trilho.dataset.hidden = ''; return; }
    delete trilho.dataset.hidden;
    const pista = trilho.clientHeight, tamanho = Math.max(36, innerHeight / doc.scrollHeight * pista);
    trilho.style.setProperty('--thumb-size', tamanho.toFixed(1) + 'px');
    trilho.style.setProperty('--thumb-y', (scrollY / max * (pista - tamanho)).toFixed(1) + 'px');
  };
  const aoRolar = () => {
    if (!quadro) quadro = requestAnimationFrame(atualizar);
    trilho.dataset.active = '';
    clearTimeout(parado);
    parado = setTimeout(() => delete trilho.dataset.active, 900);
  };
  atualizar();
  new ResizeObserver(aoRolar).observe(document.body);
  addEventListener('scroll', aoRolar, {passive: true});
});

function contar(el) {
  if (matchMedia('(prefers-reduced-motion: reduce)').matches || 'theming' in document.documentElement.dataset) return;
  const fim = el.textContent, alvo = +el.dataset.alvo, t0 = performance.now();
  const passo = t => {
    const p = Math.min((t - t0) / 900, 1);
    el.textContent = p < 1 ? Math.round(alvo * (1 - Math.pow(1 - p, 3))).toLocaleString('pt-BR') : fim;
    if (p < 1) requestAnimationFrame(passo);
  };
  requestAnimationFrame(passo);
}
document.addEventListener('DOMContentLoaded', () => new MutationObserver(ms => ms.forEach(m => m.addedNodes.forEach(n =>
  n.querySelectorAll && n.querySelectorAll('[data-alvo]').forEach(contar)))).observe(document.body, {childList: true, subtree: true}));
"""


# ---------- Agendador de Tarefas do Windows ----------

def schtasks(*args: str) -> subprocess.CompletedProcess:
    return subprocess.run(["schtasks", *args], capture_output=True, encoding="oem",
                          errors="replace", creationflags=SEM_JANELA)


def agendar(minutos: int) -> subprocess.CompletedProcess:
    # pythonw.exe = Python sem console, a medicao roda invisivel em segundo plano
    pythonw = Path(sys.executable).with_name("pythonw.exe")
    r = schtasks("/Create", "/F", "/TN", TAREFA, "/SC", "MINUTE", "/MO", str(minutos),
                 "/TR", f'"{pythonw}" "{Path(medir.__file__).resolve()}"')
    if r.returncode == 0:
        # O padrao do Windows e NAO rodar na bateria; em notebook isso deixaria buracos nos dados
        subprocess.run(
            ["powershell", "-NoProfile", "-Command",
             f"Set-ScheduledTask -TaskName {TAREFA} -Settings "
             "(New-ScheduledTaskSettingsSet -AllowStartIfOnBatteries -DontStopIfGoingOnBatteries)"],
            capture_output=True, creationflags=SEM_JANELA)
    return r


def minutos_iso(duracao: str) -> int | None:
    """'PT30M' -> 30, 'PT1H30M' -> 90 (formato em que o Windows guarda o intervalo)."""
    m = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?", duracao)
    return int(m[1] or 0) * 60 + int(m[2] or 0) if m and (m[1] or m[2]) else None


def intervalo_agendado() -> int | None:
    """Minutos entre medicoes, lidos da propria tarefa; None se nao houver agendamento."""
    r = schtasks("/Query", "/TN", TAREFA, "/XML")
    achou = re.search(r"<Interval>(.+?)</Interval>", r.stdout or "")
    return minutos_iso(achou[1]) if r.returncode == 0 and achou else None


# ---------- Dados ----------

def carregar() -> list[dict]:
    arquivo = medir.caminho_csv()
    if not arquivo.exists():
        return []
    linhas = []
    with arquivo.open(encoding="utf-8", newline="") as f:
        for linha in csv.DictReader(f):
            try:
                linha["data_hora"] = datetime.fromisoformat(linha["data_hora"])
                for c in NUMERICOS:
                    linha[c] = float(linha[c]) if linha[c] else None
            except (ValueError, TypeError, KeyError):
                continue  # linha cortada (PC desligou no meio da gravacao): ignora
            linhas.append(linha)
    return linhas


def medir_seguro() -> dict:
    try:
        return medir.medir()
    except SystemExit as e:  # Speedtest CLI ausente; nao pode vazar para o loop do servidor
        return {"erro": str(e)}


# ---------- Graficos (ECharts) ----------

BASE = {"backgroundColor": "transparent", "textStyle": {"fontFamily": "Segoe UI, system-ui, sans-serif"},
        "animationDuration": 1100, "animationEasing": "cubicOut"}


def regua(contratado: float, extras: list | None = None) -> dict:
    """Linha tracejada na velocidade contratada, com rotulo direto."""
    return {"silent": True, "symbol": "none", "animationDuration": 600,
            "data": [{"yAxis": contratado, "lineStyle": {"color": MUDO, "type": "dashed"},
                      "label": {"formatter": f"Contratado: {contratado:g} Mbps", "position": "insideEndTop", "color": MUDO}},
                     *(extras or [])]}


def degrade(cor: str) -> dict:
    return {"color": {"type": "linear", "x": 0, "y": 0, "x2": 0, "y2": 1,
                      "colorStops": [{"offset": 0, "color": cor + "55"}, {"offset": 1, "color": cor + "00"}]}}


def grafico_tempo(ok: list[dict], falhas: list[dict], contratado: float) -> dict:
    def serie(nome, campo, cor, **extra):
        return {"name": nome, "type": "line", "smooth": 0.25, "showSymbol": len(ok) <= 60, "symbolSize": 7,
                "lineStyle": {"width": 2}, "itemStyle": {"color": cor}, "emphasis": {"focus": "series"},
                "data": [[m["data_hora"].isoformat(), m[campo]] for m in ok], **extra}

    quedas = [{"xAxis": m["data_hora"].isoformat(), "lineStyle": {"color": CRITICO, "type": "solid", "opacity": .7},
               "label": {"show": False}} for m in falhas]
    return BASE | {
        "grid": {"left": 48, "right": 24, "top": 62, "bottom": 64},
        "legend": {"top": 0, "left": 0, "icon": "roundRect", "itemWidth": 12, "itemHeight": 4, "textStyle": {"color": TINTA2}},
        "tooltip": DICA | {":valueFormatter": "v => v == null ? '–' : v.toFixed(1) + ' Mbps'"},
        "xAxis": EIXO_TEMPO,
        "yAxis": EIXO | {"type": "value", "name": "Mbps", "nameTextStyle": {"color": MUDO}, "max": max(contratado, *(m["upload_mbps"] or 0 for m in ok), *(m["download_mbps"] for m in ok))},
        "dataZoom": [{"type": "inside"},
                     {"type": "slider", "height": 18, "bottom": 12, "borderColor": "transparent", "backgroundColor": GRADE,
                      "fillerColor": "rgba(57,135,229,.22)", "handleStyle": {"color": AZUL}, "textStyle": {"color": MUDO},
                      "dataBackground": {"lineStyle": {"color": LINHA_EIXO}, "areaStyle": {"color": LINHA_EIXO}}}],
        "series": [serie("Download", "download_mbps", AZUL, areaStyle=degrade(AZUL), markLine=regua(contratado, quedas)),
                   serie("Upload", "upload_mbps", LARANJA)],
    }


def grafico_hora(ok: list[dict], contratado: float) -> dict:
    medias = [round(mean(v), 1) if (v := [m["download_mbps"] for m in ok if m["data_hora"].hour == h]) else None
              for h in range(24)]
    return BASE | {
        "grid": {"left": 48, "right": 24, "top": 30, "bottom": 30},
        "tooltip": DICA | {"axisPointer": {"type": "shadow"}, ":valueFormatter": "v => v == null ? 'sem medição' : v.toFixed(1) + ' Mbps'"},
        "xAxis": EIXO | {"type": "category", "data": [f"{h}h" for h in range(24)], "splitLine": {"show": False}},
        "yAxis": EIXO | {"type": "value", "name": "Mbps", "nameTextStyle": {"color": MUDO}, "max": max(contratado, *(v or 0 for v in medias))},
        "series": [{"name": "Download médio", "type": "bar", "data": medias, "barMaxWidth": 22,
                    "itemStyle": {"color": AZUL, "borderRadius": [4, 4, 0, 0]}, "markLine": regua(contratado),
                    ":animationDelay": "i => i * 35"}],
    }


def grafico_ping(ok: list[dict]) -> dict:
    return BASE | {
        "grid": {"left": 48, "right": 24, "top": 30, "bottom": 30},
        "tooltip": DICA | {":valueFormatter": "v => v == null ? '–' : v.toFixed(1) + ' ms'"},
        "xAxis": EIXO_TEMPO,
        "yAxis": EIXO | {"type": "value", "name": "ms", "nameTextStyle": {"color": MUDO}},
        "series": [{"name": "Ping", "type": "line", "smooth": 0.25, "showSymbol": len(ok) <= 60, "symbolSize": 7,
                    "lineStyle": {"width": 2}, "itemStyle": {"color": VERDE}, "areaStyle": degrade(VERDE),
                    "data": [[m["data_hora"].isoformat(), m["ping_ms"]] for m in ok]}],
    }


def velocimetro(pct: float, cor: str) -> dict:
    return BASE | {"series": [{
        "type": "gauge", "startAngle": 215, "endAngle": -35, "min": 0, "max": max(100, round(pct)), "radius": "96%",
        "center": ["50%", "58%"], "animationDuration": 1600, "animationEasing": "cubicOut",
        "progress": {"show": True, "width": 16, "roundCap": True, "itemStyle": {"color": cor}},
        "axisLine": {"roundCap": True, "lineStyle": {"width": 16, "color": [[1, GRADE]]}},
        "pointer": {"show": False}, "axisTick": {"show": False}, "splitLine": {"show": False}, "axisLabel": {"show": False},
        "title": {"offsetCenter": [0, "34%"], "color": MUDO, "fontSize": 13},
        "detail": {"valueAnimation": True, "formatter": "{value}%", "offsetCenter": [0, "-2%"],
                   "color": TINTA, "fontSize": 46, "fontWeight": 600},
        "data": [{"value": round(pct), "name": "do contratado"}],
    }]}


# ---------- Componentes ----------

def cartao(i: int = 0, classes: str = "") -> ui.element:
    return ui.element("div").classes(f"cartao {classes}").style(f"--i: {i}")


def titulo(icone: str, texto: str) -> None:
    with ui.element("div").classes("cartao-titulo"):
        ui.icon(icone)
        ui.label(texto)


def kpi(i: int, icone: str, rotulo: str, valor: float, unidade: str, cor: str = AZUL) -> None:
    with cartao(i):
        with ui.element("div").classes("kpi-icone").style(f"color: {cor}; background: {cor}26"):
            ui.icon(icone)
        ui.label(rotulo).classes("kpi-rotulo")
        with ui.row().classes("items-baseline gap-1"):
            ui.label(f"{valor:.0f}").classes("kpi-valor").props(f'data-alvo="{valor:.0f}"')
            ui.label(unidade).classes("kpi-unidade")


def secao(icone: str, texto: str) -> None:
    with ui.element("div").classes("secao"):
        ui.icon(icone)
        ui.label(texto)


# ---------- Pagina ----------

@ui.page("/")
def pagina() -> None:
    ui.add_css(CSS)
    ui.add_head_html(f"<script>{JS}</script>")
    ui.colors(primary=TEMAS[True]["AZUL"], positive=BOM, negative=CRITICO, warning=ALERTA,
              dark=TEMAS[True]["SUPERFICIE"], dark_page=TEMAS[True]["PAGINA"])
    cfg = medir.config()
    modo = ui.dark_mode(value=cfg.get("tema", "escuro") == "escuro")
    aplicar_tema(modo.value)
    visto = {"mtime": None, "periodo": "Tudo", "slide": ""}

    def salvar_cfg() -> None:
        medir.CONFIG.write_text(json.dumps(cfg, indent=2, ensure_ascii=False), "utf-8")

    # ----- acoes -----
    async def testar() -> None:
        botao_testar.props("loading")
        aviso = ui.notification("Medindo a internet… leva uns 30 segundos", spinner=True, timeout=None)
        r = await run.io_bound(medir_seguro)
        aviso.dismiss()
        botao_testar.props(remove="loading")
        if r.get("erro"):
            ui.notify(f"Medição falhou: {r['erro']}", type="negative", icon="wifi_off", multi_line=True)
        else:
            ui.notify(f"{r['download_mbps']:.0f} Mbps de download, {r['upload_mbps']:.0f} de upload",
                      type="positive", icon="speed")
        painel.refresh()

    async def escolher_pasta() -> None:
        # Dialogo nativo do Windows, em processo separado (o tkinter exige a thread principal)
        r = await run.io_bound(lambda: subprocess.run(
            [sys.executable, "-X", "utf8", "-c", SELETOR], capture_output=True, encoding="utf-8", creationflags=SEM_JANELA))
        escolhida = (r.stdout or "").strip()
        if not escolhida:
            return
        antigo, novo = medir.caminho_csv(), Path(escolhida) / "medicoes.csv"
        if antigo.exists() and not novo.exists():
            shutil.move(antigo, novo)  # leva o historico junto
        cfg["pasta"] = str(Path(escolhida))
        salvar_cfg()
        caminho.text = cfg["pasta"]
        ui.notify("Medições serão salvas nesta pasta", type="positive", icon="folder")
        painel.refresh()

    def mudar_contratado(e) -> None:
        if (e.value or "").isdigit() and int(e.value) > 0:
            cfg["contratado"] = int(e.value)
            salvar_cfg()
            painel.refresh()

    async def criar_agendamento() -> None:
        r = await run.io_bound(agendar, intervalo.value)
        if r.returncode == 0:
            ui.notify(f"Agendado: uma medição a cada {INTERVALOS[intervalo.value]}", type="positive", icon="event_available")
        else:
            ui.notify((r.stderr or r.stdout).strip(), type="negative", multi_line=True)
        agendamento.refresh()

    def remover_agendamento() -> None:
        schtasks("/Delete", "/F", "/TN", TAREFA)
        ui.notify("Agendamento removido", icon="event_busy")
        agendamento.refresh()

    # ----- cabecalho -----
    def ao_trocar_tema(e) -> None:
        """Chamado pelo JS (trocarTema) de dentro da View Transition; avisa quando a pagina nova esta pronta."""
        modo.value = bool(e.args["escuro"])
        cfg["tema"] = "escuro" if modo.value else "claro"
        salvar_cfg()
        aplicar_tema(modo.value)
        visto["slide"] = "sem-entrada"  # sem animacao de entrada nos cartoes e graficos: a onda ja e a transicao
        BASE["animation"] = False
        painel.refresh()           # os graficos recebem as cores prontas, entao sao redesenhados
        BASE["animation"] = True
        ui.run_javascript("window.__temaPronto && window.__temaPronto()")

    ui.on("tema", ao_trocar_tema)

    with ui.header().classes("cabecalho items-center").classes(remove="text-white bg-primary"):
        ui.button(icon="menu", on_click=lambda: gaveta.toggle()).props("flat round dense color=grey-5") \
            .tooltip("Configurações")
        with ui.element("div").classes("logo"):
            ui.icon("signal_cellular_alt")
        ui.label("Internet Check").classes("titulo")
        ui.space()

        @ui.refreshable
        def agendamento() -> None:
            atual = intervalo_agendado()
            with ui.element("div").classes("selo"):
                ui.element("div").classes("ponto ativo" if atual else "ponto")
                ui.label(f"Medindo a cada {INTERVALOS.get(atual, f'{atual} min')}" if atual else "Sem agendamento")
            if atual:
                ui.button(icon="event_busy", on_click=remover_agendamento).props("flat round dense color=grey-6") \
                    .tooltip("Remover agendamento")

        agendamento()
        with ui.element("button").classes("tema-botao").props('type=button aria-label="Alternar tema claro/escuro"') \
                .on("click", js_handler="() => trocarTema()"):
            ui.html(ICONE_TEMA, sanitize=False)
        botao_testar = ui.button("Testar agora", icon="play_arrow", on_click=testar).props("unelevated no-caps rounded")

    # ----- barra lateral -----
    with ui.left_drawer().props("width=300") as gaveta, ui.column().classes("lateral w-full"):
        secao("sell", "Plano contratado")
        # texto com mascara em vez de type=number: sem setinhas e so digitos (inteiro)
        ui.input(value=str(int(cfg["contratado"])), on_change=mudar_contratado) \
            .props('outlined dense debounce=600 mask="######" inputmode=numeric suffix=Mbps').classes("w-full")

        secao("folder_open", "Pasta das medições")
        caminho = ui.label(cfg["pasta"]).classes("caminho")
        ui.button("Escolher pasta", icon="drive_file_move", on_click=escolher_pasta) \
            .props("outline no-caps").classes("w-full")

        secao("schedule", "Agendamento")
        intervalo = ui.select(INTERVALOS, value=30, label="Medir a cada").props("outlined dense").classes("w-full")
        ui.button("Agendar no Windows", icon="event_repeat", on_click=criar_agendamento) \
            .props("unelevated no-caps").classes("w-full")

        ui.label("Cada teste trafega bastante dados (centenas de MB em links rápidos). "
                 "O PC precisa estar ligado e com o usuário logado para medir.").classes("nota q-mt-md")

    # ----- conteudo -----
    with ui.column().classes("conteudo"):
        def mudar_periodo(e) -> None:
            nomes = list(PERIODOS)  # o painel entra pelo lado para onde o usuario foi
            visto["slide"] = "vai-dir" if nomes.index(e.value) > nomes.index(visto["periodo"]) else "vai-esq"
            visto["periodo"] = e.value
            painel.refresh()

        # q-tabs anima o indicador entre as abas; o CSS o transforma numa pilula deslizante
        with ui.tabs(value="Tudo", on_change=mudar_periodo).classes("periodo") \
                .props("dense no-caps indicator-color=primary active-color=white") as periodo:
            for nome in PERIODOS:
                ui.tab(nome)

        def desenhar() -> None:
            arquivo = medir.caminho_csv()
            visto["mtime"] = arquivo.stat().st_mtime if arquivo.exists() else None
            contratado = cfg["contratado"]

            dias = PERIODOS[periodo.value]
            hoje = datetime.now().replace(hour=0, minute=0, second=0, microsecond=0)
            inicio = datetime.min if dias is None else hoje - timedelta(days=dias)
            dados = [m for m in carregar() if m["data_hora"] >= inicio]
            ok = [m for m in dados if m["download_mbps"] is not None]
            falhas = [m for m in dados if m["download_mbps"] is None]

            if not ok:
                with cartao(classes="w-full"), ui.column().classes("vazio w-full"):
                    ui.icon("wifi_tethering")
                    ui.label("Nenhuma medição neste período").classes("text-h6")
                    ui.label(f"{len(falhas)} tentativas falharam." if falhas else
                             "Clique em Testar agora, ou agende as medições na barra lateral.").classes("nota")
                return

            downloads = [m["download_mbps"] for m in ok]
            pct = mean(downloads) / contratado * 100
            abaixo = sum(d < 0.8 * contratado for d in downloads) / len(downloads)
            # cor de status sempre acompanhada de icone + texto
            cor, icone, veredito = ((BOM, "check_circle", "Dentro do contratado") if pct >= 80 else
                                    (ALERTA, "warning", "Abaixo do contratado") if pct >= 40 else
                                    (CRITICO, "error", "Muito abaixo do contratado"))

            with ui.element("div").classes("grade-topo"):
                with cartao(0, "destaque"):
                    ui.echart(velocimetro(pct, cor)).classes("w-full").style("height: 230px")
                    with ui.element("div").classes("veredito").style(f"color: {cor}"):
                        ui.icon(icone)
                        ui.label(veredito).style(f"color: {TINTA}")
                    ui.label(f"{abaixo:.0%} das medições abaixo de 80% do plano ({0.8 * contratado:.0f} Mbps)").classes("sub")
                kpi(1, "download", "Download médio", mean(downloads), "Mbps")
                kpi(2, "trending_down", "Pior download", min(downloads), "Mbps")
                kpi(3, "upload", "Upload médio", mean(m["upload_mbps"] for m in ok), "Mbps", LARANJA)
                kpi(4, "timer", "Ping médio", mean(m["ping_ms"] for m in ok), "ms", VERDE)
                kpi(5, "fact_check", "Medições", len(ok), "no período", MUDO)
                kpi(6, "wifi_off", "Falhas", len(falhas), "quedas", CRITICO if falhas else MUDO)

            with cartao(7, "w-full"):
                titulo("show_chart", "Velocidade ao longo do tempo")
                ui.echart(grafico_tempo(ok, falhas, contratado)).classes("w-full").style("height: 360px")
                if falhas:
                    with ui.row().classes("items-center gap-1 nota"):
                        ui.icon("error", color="negative")
                        ui.label("Linhas verticais vermelhas: medição falhou (provável queda de internet).")

            with ui.element("div").classes("grade-dupla"):
                with cartao(8):
                    titulo("bar_chart", "Download médio por hora do dia")
                    ui.echart(grafico_hora(ok, contratado)).classes("w-full").style("height: 280px")
                with cartao(9):
                    titulo("network_check", "Ping (latência)")
                    ui.echart(grafico_ping(ok)).classes("w-full").style("height: 280px")

            with cartao(10, "w-full"):
                titulo("table_rows", "Todas as medições")
                num = lambda v, d=1: "–" if v is None else f"{v:.{d}f}"  # noqa: E731
                linhas = [{"id": i, "quando": m["data_hora"].strftime("%d/%m/%Y %H:%M"),
                           "download": num(m["download_mbps"]), "upload": num(m["upload_mbps"]),
                           "ping": num(m["ping_ms"]), "jitter": num(m["jitter_ms"]), "perda": num(m["perda_pct"], 2),
                           "servidor": m["servidor"] or f"Falha: {m['erro']}", "url": m["url"]}
                          for i, m in enumerate(reversed(dados))]
                colunas = [{"name": n, "label": r, "field": n, "align": a} for n, r, a in [
                    ("quando", "Data/hora", "left"), ("download", "Download (Mbps)", "right"), ("upload", "Upload (Mbps)", "right"),
                    ("ping", "Ping (ms)", "right"), ("jitter", "Jitter (ms)", "right"), ("perda", "Perda (%)", "right"),
                    ("servidor", "Servidor", "left"), ("url", "Comprovante", "left")]]
                tabela = ui.table(rows=linhas, columns=colunas, pagination=10).props("flat").classes("w-full")
                tabela.add_slot("body-cell-url", '''
                    <q-td :props="props">
                        <a v-if="props.value" :href="props.value" target="_blank" class="link-prova">
                            <q-icon name="open_in_new" /> abrir
                        </a>
                    </q-td>''')

        @ui.refreshable
        def painel() -> None:
            with ui.element("div").classes(f"painel {visto['slide']}"):
                visto["slide"] = ""  # so desliza na troca de periodo, nao nas atualizacoes automaticas
                desenhar()

        painel()

    def checar_novidade() -> None:
        """Redesenha sozinho quando o agendador grava uma medicao nova."""
        arquivo = medir.caminho_csv()
        if (arquivo.stat().st_mtime if arquivo.exists() else None) != visto["mtime"]:
            painel.refresh()

    ui.timer(30, checar_novidade)


if __name__ in {"__main__", "__mp_main__"}:
    ui.run(title="Internet Check", favicon=FAVICON, dark=True, language="pt-BR", port=8501,
           reload=False, show="--sem-navegador" not in sys.argv, show_welcome_message=False)
