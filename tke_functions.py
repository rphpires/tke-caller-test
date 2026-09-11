import socket
import time
from datetime import datetime

import serial
from pyModbusTCP.client import ModbusClient

import crc16

# Transportes (valores do dropdown da UI)
TRANSPORT_SERIAL = "Modbus RTU - Serial"
TRANSPORT_IP = "Conversor IP"

# Dois tipos de conversor, indistinguiveis na conexao TCP - so o primeiro envio
# revela qual e. O app tenta os dois e memoriza o que responder.
#   IP_MODE_MODBUS_TCP: gateway Modbus TCP->RTU. Recebe header MBAP e sem CRC,
#                       reenquadra sozinho no lado serial. E o que o site
#                       controller usa no modo 3.
#   IP_MODE_RTU:        conversor transparente (Moxa NPort e afins em TCP Server /
#                       RAW). O socket e um cabo serial esticado: vai o frame RTU
#                       cru, com CRC e sem MBAP.
IP_MODE_MODBUS_TCP = "Modbus TCP (gateway)"
IP_MODE_RTU = "RTU cru (conversor transparente)"

# Modbus
MODBUS_FUNC_WRITE_MULTIPLE_REGISTERS = 0x10
MODBUS_START_REGISTER = 0x0000
MODBUS_REGISTER_COUNT = 8
MODBUS_REPLY_LEN = 8  # slave + func + addr(2) + n_reg(2) + crc(2)

SERIAL_BAUD_RATE = 19200
SERIAL_STALE_SECONDS = 5
TCP_TIMEOUT = 2.0

# Mensagens de texto do display TKE
TKE_MSG_NONE = 0
TKE_MSG_ALREADY_ON_FLOOR = 2
TKE_MSG_ACCESS_DENIED = 11

DEFAULT_MCO = 1
DEFAULT_GATEWAY = 1


def u16(value):
    """Quebra um inteiro em 2 bytes big-endian, como exige o registro Modbus."""
    value &= 0xFFFF
    return [(value >> 8) & 0xFF, value & 0xFF]


def to_int(value, default=0):
    """Converte campos da UI/W-Access ('', None, '_3') em inteiro."""
    if value is None:
        return default
    text = str(value).strip().strip('_')
    if not text:
        return default
    return int(text)


class ThyssenCommunication:
    def __init__(self):
        self.reply_msg = ""
        self.msg_count = 0
        self.transport = None
        self.device_fd = None
        self.comm_port = None
        self._client = None
        self._sock = None
        self.ip = None
        self.port = None
        self._ip_mode = None
        self.__last_operation_start_time = 0
        self.elv_tke_target_mcos = []

    # ------------------------------------------------------------------ log

    def reset_log(self):
        self.reply_msg = ""

    def print_msg(self, msg):
        print(msg)
        dt_now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.reply_msg += f"{dt_now} - {msg}\n"

    # ------------------------------------------------------------- conexao

    def disconnect(self):
        self.close_port()
        self.close_modbus_client()
        self.close_socket()
        self.transport = None

    def is_connected(self):
        return bool(self.device_fd or self._client or self._sock)

    def _parse_endereco(self, ip, port):
        """Valida ip/porta vindos da UI. Devolve (porta, mensagem_de_erro)."""
        if not ip:
            return None, "Error: no gateway IP informed"
        try:
            port = to_int(port)
        except ValueError as ex:
            return None, f"Error: invalid IP port: {ex}"
        if not port:
            return None, "Error: no gateway TCP port informed"
        return port, None

    def open_terminal_loop(self, comm_port):
        """Modo 2 equivalente: Modbus RTU direto na serial."""
        self.reset_log()
        self.disconnect()

        if not comm_port:
            self.print_msg("Error: no COM port selected")
            return self.reply_msg, False

        self.print_msg(f"Trying to connect on CommPort: {comm_port}")
        try:
            self.device_fd = serial.Serial(
                port=comm_port,
                baudrate=SERIAL_BAUD_RATE,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0.1,
                write_timeout=0.1
            )
        except (IOError, ValueError) as ex:
            self.device_fd = None
            self.print_msg(f"Error: Unable to open serial {comm_port}: {ex}")
            return self.reply_msg, False

        self.transport = TRANSPORT_SERIAL
        self.comm_port = comm_port
        self.print_msg(f"Connected on Serial PORT: {comm_port}")
        return self.reply_msg, True

    def open_gateway_ip(self, ip, port, unit_id=DEFAULT_GATEWAY):
        """Modo 3: conversor IP. Abre os dois enquadramentos; o envio decide qual vale."""
        self.reset_log()
        self.disconnect()

        port, erro = self._parse_endereco(ip, port)
        if erro:
            self.print_msg(erro)
            return self.reply_msg, False

        try:
            unit_id = to_int(unit_id, DEFAULT_GATEWAY)
        except ValueError as ex:
            self.print_msg(f"Error: invalid gateway address: {ex}")
            return self.reply_msg, False

        self.print_msg(f"Trying to connect on {ip}:{port} (unit_id={unit_id})")
        if not self._abrir_socket(ip, port):
            return self.reply_msg, False

        try:
            # auto_close=False: reabrir a conexao a cada chamada custa um handshake
            # TCP inteiro dentro do tempo de resposta do elevador.
            self._client = ModbusClient(
                host=ip, port=port, unit_id=unit_id,
                timeout=TCP_TIMEOUT, auto_open=True, auto_close=False
            )
        except ValueError as ex:
            self._client = None
            self.print_msg(f"Error: Unable to create Modbus client: {ex}")

        self.transport = TRANSPORT_IP
        self.ip, self.port = ip, port
        self._ip_mode = None
        self.print_msg(f"Connected on {ip}:{port}")
        self.print_msg("O tipo de conversor sera detectado no primeiro envio.")
        self.print_msg("Conversor transparente precisa estar em %s bps, 8 bits, "
                       "paridade PAR (even), 1 stop bit." % SERIAL_BAUD_RATE)
        return self.reply_msg, True

    def _abrir_socket(self, ip, port):
        try:
            self._sock = socket.create_connection((ip, port), timeout=TCP_TIMEOUT)
            self._sock.settimeout(TCP_TIMEOUT)
        except OSError as ex:
            self._sock = None
            self.print_msg(f"Error: Unable to connect on {ip}:{port}: {ex}")
            return False
        return True

    def close_socket(self):
        if not self._sock:
            return
        try:
            self._sock.close()
        except OSError:
            pass
        finally:
            self._sock = None

    def close_port(self):
        if not self.device_fd:
            return
        try:
            self.device_fd.close()
        except IOError:
            pass
        finally:
            self.device_fd = None

    def close_modbus_client(self):
        if not self._client:
            return
        try:
            self._client.close()
        except Exception:
            pass
        finally:
            self._client = None

    # --------------------------------------------------------------- chamada

    def send_message(self, dados, message_text_id=TKE_MSG_NONE):
        self.reset_log()

        try:
            reader_floor = to_int(dados["andar_origem"])
            target_device = to_int(dados["dispositivo"])
            ch_floor = to_int(dados["andar_destino"])
            controller_offset = to_int(dados["ajuste_pavimento"])
            gateway = to_int(dados["gateway"], DEFAULT_GATEWAY)
            self.elv_tke_target_mcos = self.parse_tke_target_mcos(dados["mco_destino"])
        except (KeyError, ValueError) as ex:
            self.print_msg(f"Error: invalid call parameters: {ex}")
            return self.reply_msg

        target_mco = self.get_target_mco_for_floor(ch_floor)
        self.send_message_single_mco(
            gateway, reader_floor, target_device, target_mco,
            ch_floor, controller_offset, message_text_id
        )
        return self.reply_msg

    def build_registers(self, reader_floor, target_device, target_mco,
                        ch_floor, controller_offset, message_count, message_text_id):
        """Os 8 registros da chamada. Mesmo layout nos dois transportes."""
        for name, floor in (("origin", reader_floor), ("destination", ch_floor)):
            if floor - controller_offset < 0:
                self.print_msg("Warning: %s floor %s minus offset %s is negative. "
                               "Check the floor adjustment." % (name, floor, controller_offset))

        return [
            (reader_floor - controller_offset) & 0xFFFF,  # Pavimento origem
            target_device & 0xFFFF,                       # Dispositivo na origem
            (ch_floor - controller_offset) & 0xFFFF,      # Pavimento destino
            target_mco & 0xFFFF,                          # MCO destino
            0,                                            # Modo + tipo (fixo)
            0,                                            # Parametro da chamada (fixo)
            message_count & 0xFFFF,                       # Contador de chamadas
            message_text_id & 0xFFFF,                     # Mensagem do display
        ]

    def send_message_single_mco(self, gateway, reader_floor, target_device, target_mco,
                                ch_floor, controller_offset, message_text_id=TKE_MSG_NONE):
        if not self.is_connected():
            self.print_msg("Error: not connected to the TKE gateway")
            return self.reply_msg

        self.msg_count += 1
        message_count = self.msg_count % (1 << 16)

        if reader_floor == ch_floor and message_text_id == TKE_MSG_NONE:
            message_text_id = TKE_MSG_ALREADY_ON_FLOOR

        registers = self.build_registers(
            reader_floor, target_device, target_mco,
            ch_floor, controller_offset, message_count, message_text_id
        )

        if message_text_id:
            self.print_msg("Sending display message %s (TKETargetDevice=%s, TKETargetMCO=%s)"
                           % (message_text_id, target_device, target_mco))
        else:
            self.print_msg("Sending message (Origin Floor=%s, TKE device=%s, DestFloor=%s, MCO=%s, offset floor=%s)"
                           % (reader_floor, target_device, ch_floor, target_mco, controller_offset))

        if self.transport == TRANSPORT_IP:
            self.__send_ip(gateway, registers)
        else:
            self.__send_modbus_rtu(gateway, registers)

        return self.reply_msg

    # ------------------------------------------------------- transporte RTU

    def build_rtu_frame(self, gateway, registers):
        """Frame Modbus RTU completo, com CRC. Igual na serial e no socket cru."""
        msg = [
            gateway & 0xFF,                          # Endereco do escravo
            MODBUS_FUNC_WRITE_MULTIPLE_REGISTERS,    # Funcao
        ]
        msg += u16(MODBUS_START_REGISTER)            # Registro inicial
        msg += u16(MODBUS_REGISTER_COUNT)            # N de registros
        msg += [MODBUS_REGISTER_COUNT * 2]           # N de bytes de dados
        for register in registers:
            msg += u16(register)

        crc = crc16.calcBytes(msg, 0xFFFF)
        return bytes(msg + [crc & 0xFF, (crc >> 8) & 0xFF])  # Modbus: CRC low byte first

    def __send_modbus_rtu(self, gateway, registers):
        msg = self.build_rtu_frame(gateway, registers)
        self.print_msg("Message = %s" % (" ".join("0x%02X" % b for b in msg)))

        for attempt in range(3):
            try:
                if self.__last_operation_start_time:
                    elapsed = time.monotonic() - self.__last_operation_start_time
                    if elapsed > SERIAL_STALE_SECONDS:
                        self.print_msg(f"Previous operation stale after {elapsed:.1f}s. Reopening serial port")
                        port = self.comm_port
                        self.close_port()
                        self.open_terminal_loop(port)
                        if not self.device_fd:
                            break

                reply = self.__send_and_receive(msg)
                self.print_msg(f"Got {len(reply)} bytes as reply: {[hex(b) for b in reply]}")
                if not reply:
                    self.print_msg("Warning: no reply from TKE gateway")

            except IOError as ex:
                self.print_msg("Error sending serial command (%s). Attempt %s/3" % (ex, attempt + 1))
                time.sleep(0.1)
                continue
            break

    def __send_and_receive(self, msg: bytes):
        self.__last_operation_start_time = time.monotonic()
        sent_count = self.device_fd.write(msg)

        self.print_msg(f"Serial sent message: {sent_count}/{len(msg)} bytes")
        time.sleep(0.05)
        ret = self.device_fd.read(MODBUS_REPLY_LEN)

        self.print_msg(f"Received message: {len(ret)} bytes")
        self.__last_operation_start_time = 0

        return ret

    # ---------------------------------------------------- transporte por IP

    def __send_ip(self, gateway, registers):
        """Tenta os dois enquadramentos e memoriza o que o conversor aceitar."""
        tentativas = {
            IP_MODE_MODBUS_TCP: lambda: self.__try_modbus_tcp(registers),
            IP_MODE_RTU: lambda: self.__try_rtu_over_tcp(gateway, registers),
        }

        if self._ip_mode:
            ordem = [self._ip_mode]
        else:
            # Modbus TCP primeiro: um gateway de verdade sempre responde (nem que
            # seja com excecao), entao o silencio dele ja descarta essa hipotese.
            ordem = [IP_MODE_MODBUS_TCP, IP_MODE_RTU]

        for rodada in range(3):
            for modo in ordem:
                if tentativas[modo]():
                    if self._ip_mode != modo:
                        self._ip_mode = modo
                        self.print_msg(f"Conversor detectado: {modo}")
                    return
            time.sleep(0.1)
            if rodada == 0 and not self._ip_mode:
                self.print_msg("Nenhum dos dois enquadramentos respondeu. Repetindo...")

        self._ip_mode = None
        self.print_msg("Error: o conversor nao respondeu em nenhum dos dois enquadramentos")
        self.print_msg("Verifique no conversor: modo TCP Server/RAW, %s bps, 8 bits, "
                       "paridade PAR (even), 1 stop bit, e a fiacao RS-485 (A/B)."
                       % SERIAL_BAUD_RATE)
        self.print_msg(f"Confira tambem se o endereco de escravo do gateway TKE e {gateway}.")

    def __try_rtu_over_tcp(self, gateway, registers):
        msg = self.build_rtu_frame(gateway, registers)
        self.print_msg("RTU cru = %s" % (" ".join("0x%02X" % b for b in msg)))

        try:
            if self._sock is None and not self._abrir_socket(self.ip, self.port):
                return False

            self._sock.sendall(msg)
            reply = self._sock.recv(MODBUS_REPLY_LEN)
            if not reply:
                # recv vazio = o outro lado fechou; nao adianta reusar o socket.
                self.print_msg("  sem resposta: conexao fechada pelo conversor")
                self.close_socket()
                return False

            self.print_msg(f"  resposta de {len(reply)} bytes: {[hex(b) for b in reply]}")
            return True

        except socket.timeout:
            self.print_msg("  sem resposta em %ss (RTU cru)" % TCP_TIMEOUT)
            return False
        except OSError as ex:
            self.print_msg(f"  erro de socket: {ex}")
            self.close_socket()
            return False

    def __try_modbus_tcp(self, registers):
        if not self._client:
            return False

        self.print_msg(f"Modbus TCP registers = {registers}")
        if not self._client.is_open and not self._client.open():
            self.print_msg(f"  nao reconectou: {self._client.last_error_as_txt}")
            return False

        if self._client.write_multiple_registers(MODBUS_START_REGISTER, registers):
            self.print_msg("  aceito por %s:%s (unit_id=%s)"
                           % (self._client.host, self._client.port, self._client.unit_id))
            return True

        self.print_msg("  recusado: %s / %s" % (self._client.last_error_as_txt,
                                                self._client.last_except_as_txt))
        self._client.close()
        return False

    # ------------------------------------------------------------------- MCO

    def get_target_mco_for_floor(self, floor):
        """Resolve o MCO pelo pavimento de destino. Entradas sem faixa viram fallback."""
        try:
            floor = to_int(floor)
        except ValueError:
            self.print_msg(f"Error: invalid destination floor. Using default MCO {DEFAULT_MCO}")
            return DEFAULT_MCO

        fallback = DEFAULT_MCO
        for mco, floors in self.elv_tke_target_mcos:
            if not floors:
                fallback = mco
                continue
            if floor in floors:
                return mco

        self.print_msg(f"Floor {floor} not mapped in MCO config. Using MCO {fallback}")
        return fallback

    def parse_tke_target_mcos(self, value):
        """Interpreta '1:4,6,7-18;2:20-99'. Um MCO sem faixa ('2') vale para todos."""
        elv_tke_target_mcos = []
        if not value:
            return elv_tke_target_mcos

        for target_mco_config in str(value).split(';'):
            target_mco_config = target_mco_config.strip()
            if not target_mco_config:
                continue

            target_mco_and_floors = target_mco_config.split(':')
            if len(target_mco_and_floors) != 2:
                elv_tke_target_mcos.append((to_int(target_mco_config, DEFAULT_MCO), []))
                continue

            target_mco = to_int(target_mco_and_floors[0], DEFAULT_MCO)
            floors_int = []
            for floor in target_mco_and_floors[1].split(','):
                limits = floor.split('-')
                if len(limits) == 1:
                    floors_int.append(to_int(limits[0]))
                else:
                    floors_int.extend(range(to_int(limits[0]), to_int(limits[1]) + 1))
            elv_tke_target_mcos.append((target_mco, floors_int))

        return elv_tke_target_mcos
