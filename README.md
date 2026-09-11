# TKE — Chamada Antecipada

Ferramenta de bancada/campo para disparar chamadas antecipadas de elevador
ThyssenKrupp (TKE) e conferir o quadro Modbus no fio, sem depender do Site
Controller.

Espelha a lógica de `ThyssenCommunication.py` do `wxs-site-controller`:

| Modo de operação | Transporte na ferramenta |
|---|---|
| 2 — `ELEVATOR_TYPE_THYSSENKRUPP_MODBUS` | **Modbus RTU - Serial** |
| 3 — `ELEVATOR_TYPE_THYSSENKRUPP_IP_SERIAL` | **Modbus TCP - Conversor IP** |

## Protocolo

Os dois transportes escrevem os **mesmos 8 registros** a partir do endereço
`0x0000`, via função `0x10` (write multiple registers).

Serial: Modbus RTU, 19200 8E1, CRC-16 byte baixo primeiro, resposta de 8 bytes.
IP: Modbus TCP contra o conversor; o campo **Unit ID do gateway** vira o
`unit_id` do frame MBAP — é o endereço do escravo RTU do outro lado do
conversor, e precisa bater com o gateway TKE.

Registros:

| Reg | Conteúdo |
|-----|----------|
| 0 | Pavimento de origem − ajuste de pavimento |
| 1 | Número do dispositivo na origem |
| 2 | Pavimento de destino − ajuste de pavimento |
| 3 | MCO de destino |
| 4 | Modo + tipo (fixo `0`) |
| 5 | Parâmetro da chamada (fixo `0`) |
| 6 | Contador de chamadas (`msg_count % 65536`) |
| 7 | Mensagem do display (`0` nenhuma, `2` já está no andar, `11` acesso negado) |

## MCOs de destino

Formato do campo **MCOs de destino**:

```
1:4,6,7-18;2:20-99
```

MCO `1` atende os pavimentos 4, 6 e 7 a 18; MCO `2` atende 20 a 99. Uma entrada
sem faixa (`2`) vale como fallback para qualquer pavimento não mapeado.

## Rodar

```
venv\Scripts\activate
pip install -r requirements.txt
python tke_chamada_antecipada.py
```

## Build

```
build.bat
```

Gera `dist\tke_chamada_antecipada\` via PyInstaller, com `assets/` embutido.

## Arquivos

| Arquivo | Papel |
|---------|-------|
| `tke_chamada_antecipada.py` | UI tkinter/ttk |
| `tke_functions.py` | Montagem dos registros e os dois transportes (RTU serial / TCP) |
| `crc16.py` | Tabela CRC-16 Modbus |
| `assets/` | Logos usados na UI |
