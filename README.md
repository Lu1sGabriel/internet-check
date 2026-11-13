# Internet Check

Mede a velocidade da internet de tempos em tempos, guarda cada medição e mostra tudo num painel com gráficos. Serve para comprovar, com histórico, quando a operadora entrega menos do que foi contratado.

- Mede download, upload, ping, jitter e perda de pacotes com o Speedtest CLI oficial da Ookla.
- Agenda as medições no Agendador de Tarefas do Windows; elas rodam em segundo plano, mesmo com o painel fechado.
- Registra também as falhas (quedas de internet).
- Cada medição traz um link público do resultado na Speedtest, que serve de comprovante.

## Requisitos

- Windows 10 ou 11
- [Python 3.10 ou mais novo](https://www.python.org/downloads/) (na instalação, marque "Add python.exe to PATH")
- `winget`, que já vem no Windows 10/11 atualizado

## Instalação

1. Baixe ou clone este repositório:

   ```bash
   git clone https://github.com/Lu1sGabriel/internet-check.git
   ```

2. Dê dois cliques em `iniciar.bat`.

Na primeira execução o `iniciar.bat` instala o que falta e depois abre o painel no navegador:

- o Speedtest CLI da Ookla, via `winget` (o Windows pode pedir confirmação);
- um ambiente Python isolado na pasta `.venv`, com a biblioteca NiceGUI.

Nas próximas vezes ele só abre o painel, em `http://localhost:8501`.

> O Speedtest CLI é gratuito para uso pessoal e não comercial. O programa aceita a licença e o aviso de privacidade da Ookla automaticamente ao medir.

## Como usar

Abra o painel pelo `iniciar.bat` e configure na barra lateral (em janela estreita, ela abre pelo botão de menu no canto superior esquerdo):

1. **Plano contratado:** digite a velocidade do seu plano em Mbps (padrão: 600).
2. **Pasta das medições:** clique em **Escolher pasta** para definir onde o arquivo `medicoes.csv` será salvo. Se já houver histórico, ele é movido junto.
3. **Agendamento:** escolha o intervalo e clique em **Agendar no Windows**.

Pronto: o Windows passa a medir sozinho no intervalo escolhido. Você pode fechar o painel e a janela preta do `iniciar.bat`; as medições continuam.

Outros controles:

- **Testar agora** (canto superior direito): faz uma medição na hora. Leva uns 30 segundos.
- **Remover agendamento:** ícone de calendário ao lado do status no cabeçalho, visível quando há agendamento ativo.
- **Hoje / 7 dias / 30 dias / Tudo:** filtra o período mostrado.
- **Tema claro/escuro:** botão de sol/lua no cabeçalho.

## Configuração

Tudo se configura pelo painel; não é preciso editar arquivos. As escolhas ficam salvas no `config.json`, na pasta do programa, e valem nas próximas aberturas.

| O que | Onde no painel | Padrão |
|---|---|---|
| Velocidade contratada (Mbps, só números inteiros) | Barra lateral, **Plano contratado** | 600 |
| Pasta onde o `medicoes.csv` é salvo | Barra lateral, **Escolher pasta** | Pasta do programa |
| Intervalo entre medições (de 5 minutos a 12 horas) | Barra lateral, **Agendamento** | 30 minutos |
| Tema claro ou escuro | Botão de sol/lua no cabeçalho | Escuro |

Detalhes:

- **Trocar a pasta não exige reagendar.** A medição agendada lê a pasta do `config.json` a cada execução.
- **Trocar o intervalo:** escolha o novo valor e clique em **Agendar no Windows** de novo; o agendamento anterior é substituído.
- **O agendamento fica no Windows**, não no `config.json`. É uma tarefa chamada `InternetCheck` no Agendador de Tarefas, criada para rodar também na bateria.
- **Mover a pasta do programa** quebra o agendamento, que guarda o caminho antigo. Depois de mover, abra o painel e clique em **Agendar no Windows** outra vez.

Exemplo de `config.json`:

```json
{
  "pasta": "D:\\Medicoes",
  "contratado": 600,
  "tema": "escuro"
}
```

Para voltar ao padrão, apague o `config.json`.

A porta do painel (8501) é fixa; para mudar, altere `port=8501` no fim do `app.py`.

## O que o painel mostra

- **Velocímetro:** quanto do plano contratado está chegando, em média.
- **Indicadores:** download médio, pior download, upload médio, ping médio, número de medições e de falhas.
- **Velocidade ao longo do tempo:** download e upload contra a linha do contratado. Linhas vermelhas verticais marcam medições que falharam.
- **Download médio por hora do dia:** mostra se a velocidade cai no horário de pico.
- **Ping:** latência ao longo do tempo.
- **Todas as medições:** tabela com o link **abrir** do comprovante de cada resultado.

O painel se atualiza sozinho quando chega uma medição nova.

## Para medir direito

- **Use cabo de rede.** Por Wi-Fi o resultado mede também o Wi-Fi, e a operadora vai usar isso para contestar.
- **O PC precisa estar ligado e com o usuário logado.** Com o PC desligado ou suspenso não há medição.
- **Cada teste gasta dados:** centenas de MB em conexões rápidas. Um intervalo de 30 minutos é um bom equilíbrio.
- **Evite uso pesado durante os testes** (downloads, streaming em 4K), que derruba o número medido.

## Onde ficam os dados

- `medicoes.csv`: uma linha por medição, na pasta escolhida no painel (por padrão, a pasta do programa). Abre no Excel ou no Power BI.
- `config.json`: a pasta escolhida, a velocidade contratada e o tema. Fica na pasta do programa.

Os dois arquivos são locais de cada máquina e não vão para o repositório.

## Desinstalar

1. No painel, remova o agendamento. Ou, pelo terminal:

   ```bash
   schtasks /Delete /TN InternetCheck /F
   ```

2. Apague a pasta do programa.
3. Opcional: remova o Speedtest CLI.

   ```bash
   winget uninstall Ookla.Speedtest.CLI
   ```

## Problemas comuns

| Sintoma | O que fazer |
|---|---|
| "Speedtest CLI nao encontrado" | Instale com `winget install -e --id Ookla.Speedtest.CLI` e abra o painel de novo. |
| O `iniciar.bat` pede para instalar o Python | Instale o Python pelo link acima, marcando "Add python.exe to PATH", e rode de novo. |
| O painel não abre | Confira se a janela do `iniciar.bat` está aberta e acesse `http://localhost:8501`. |
| Buracos no histórico | O PC estava desligado, suspenso ou sem usuário logado nesses horários. |

## Arquivos

| Arquivo | Função |
|---|---|
| `iniciar.bat` | Instala o que falta e abre o painel. |
| `app.py` | O painel (NiceGUI) e o agendamento no Windows. |
| `medir.py` | Faz uma medição e grava no CSV. É o que o Agendador executa. |
| `test_medir.py` | Checagem rápida: `.venv\Scripts\python test_medir.py`. |
