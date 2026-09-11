import serial
import time
import crc16

from datetime import datetime


class TKEMessageTypes:
    HEARTBEAT = "00"
    ACK_NAK = "01"
    ES_STATUS = "02"
    ES_CONFIGURATION = "03"
    CARD_SWIPE = "04"
    PIN_ENTRY = "05"
    DISPATCH_EVENT = "06"
    REGISTER_CALL = "07"
    DED_CARD_SWIPE = "09"
    IMS_PIN_ENTRY_REQUEST = "82"
    IMS_PIN_ENTRY_RESPONSE = "83"


class ThyssenCommunication:
    def __init__(self):
        self.reply_msg = ""
        self.msg_count = 0
        self.__last_operation_start_time = 0
        self.thyssen_communication_modbus = None
        self.elv_tke_target_mcos = None

    def print_msg(self, msg):
        print(msg)
        dt_now = datetime.now().strftime("%H:%M:%S.%f")[:-3]
        self.reply_msg += f"{dt_now} - {msg}\n"

    def open_terminal_loop(self, comm_port):
        self.device_fd = None
        __baud_rate__ = 19200

        self.print_msg(f'Trying to connect on CommPort: {comm_port}')
        try:
            self.device_fd = serial.Serial(
                port=comm_port,
                baudrate=__baud_rate__,
                parity=serial.PARITY_EVEN,
                stopbits=serial.STOPBITS_ONE,
                bytesize=serial.EIGHTBITS,
                timeout=0.1,
                write_timeout=0.1
            )
        except IOError as ex:
            self.print_msg(f"Error: Unable to open serial {comm_port}: {ex}")
            return self.reply_msg, False

        self.print_msg(f"Connected on Serial PORT: {comm_port}")
        return self.reply_msg, True

    def send_message(self, dados, message_text_id=0):
        try:
            TKETargetMCO = dados["mco_destino"]
            ReaderFloor = int(dados["andar_origem"])
            TKETargetDevice = int(dados["dispositivo"])
            CHFloor = int(dados["andar_destino"]) if dados["andar_destino"] else 0
            controller_offset = int(dados["ajuste_pavimento"])
            gateway = int(dados["gateway"])

            self.elv_tke_target_mcos = self.parse_tke_target_mcos(TKETargetMCO)
        except Exception as ex:
            print(f"*** Error: {ex}")
            return

        try:
            targetMCO = self.get_target_mco_for_floor(CHFloor)
            self.send_message_single_mco(gateway, ReaderFloor, TKETargetDevice, targetMCO, CHFloor, controller_offset, message_text_id)

            return self.reply_msg

        except Exception as ex:
            self.print_msg(ex)

    def assert_fd(self):
        if self.device_fd:
            return True
        else:
            self.print_msg("Error trying to open TKE serial")
            return False

    def send_message_single_mco(self, gateway, ReaderFloor, TKETargetDevice, TKETargetMCO, CHFloor, controller_offset, message_text_id=0):
        try:
            if not self.device_fd:
                self.print_msg("Error trying to open TKE serial")
                return self.reply_msg

            self.msg_count += 1
            message_count = self.msg_count % (1 << 16)

            ReaderFloor = int(ReaderFloor)
            controller_offset = int(str(controller_offset).strip('_'))
            CHFloor = int(str(CHFloor).strip('_'))
            message_text_id = int(message_text_id)

            if ReaderFloor == CHFloor and message_text_id == 0:
                message_text_id = 2  # Already on CH floor

            # msg_modbus = [ReaderFloor - controller_offset, TKETargetDevice, CHFloor - controller_offset, TKETargetMCO, 0, 0, message_count, 0]

            msg = [
                # Endereco do escravo
                gateway & 0xFF,

                # Fixo
                0x10,  # funcao
                0x00,
                0x00,
                0x00,  # n reg
                0x08,  # n reg
                0x10,  # n bytes de dados

                # Pavimento Origem
                ((ReaderFloor - controller_offset) << 8) & 0xFF,
                ((ReaderFloor - controller_offset) << 0) & 0xFF,

                # Numero do dispositivo na origem
                (TKETargetDevice << 8) & 0xFF,
                (TKETargetDevice << 0) & 0xFF,

                # Pavimento destino
                ((CHFloor - controller_offset) << 8) & 0xFF,
                ((CHFloor - controller_offset) << 0) & 0xFF,

                # MCO Destino
                (TKETargetMCO << 8) & 0xFF,
                (TKETargetMCO << 0) & 0xFF,

                # Fixo - Modo + tipo
                0x00,
                0x00,

                # Fixo - Parametro da chamada
                0x00,
                0x00,

                # Contador de Chamadas
                (message_count << 8) & 0xFF,
                (message_count << 0) & 0xFF,

                # Mensagem - Fixo
                (message_text_id << 8) & 0xFF,
                (message_text_id << 0) & 0xFF,

                # CRC
                0x00,
                0x00
            ]

            crc = crc16.calcBytes(msg[:-2], 0xFFFF)
            # print hex(crc)

            msg = bytes(msg[:-2] + [(crc >> 0) & 0xFF, (crc >> 8) & 0xFF])

            self.print_msg("Message = %s" % (" ".join(["0x%02X" % (x) for x in msg])))
        except Exception as ex:
            print(f"*** Error: {ex}")
            return

        if message_text_id:
            self.print_msg("Sending access denied message (TKETargetDevice=%s, TKETargetMCO=%s)" % (TKETargetDevice, TKETargetMCO))
        else:
            self.print_msg("Sending message (Origin Floor=%s, TKE device=%s, DestFloor=%s, MCO=%s, offset floor=%s)" % (ReaderFloor, TKETargetDevice, CHFloor, TKETargetMCO, controller_offset))
        for i in range(3):
            try:
                if self.__last_operation_start_time:
                    now_time = time.monotonic()
                    if now_time - self.__last_operation_start_time > 5:
                        self.print_msg(f"Closing serial port now_time={now_time} last_operation_start_time={self.__last_operation_start_time}")

                reply = self.__send_and_receive_win32(msg)

                self.print_msg(f"Got {len(reply)} bytes as reply: {[ hex(x) for x in reply ]}")

            except IOError:
                self.print_msg("Error sending serial command. Attempt %s/3" % (i + 1))
                time.sleep(0.1)
                continue
            break

    def __send_and_receive_win32(self, msg: bytes):
        self.__last_operation_start_time = time.monotonic()
        sent_count = self.device_fd.write(msg)

        self.print_msg(f"Serial sent message: {sent_count}/{len(msg)} bytes")
        time.sleep(0.05)
        ret = self.device_fd.read(8)

        self.print_msg(f"Received message: {len(ret)} bytes")
        self.__last_operation_start_time = 0

        return ret

    def get_target_mco_for_floor(self, floor):
        try:
            default_mco = 1
            if isinstance(floor, str):
                floor = int(str(floor).strip('_'))

            print(f"Getting target MCO for floor {floor} | elv_tke_target_mcos: {self.elv_tke_target_mcos}")
            for mco, floors in self.elv_tke_target_mcos:
                if floor in floors:
                    return int(mco)
            return default_mco

        except Exception as ex:
            print(f"*** Error: {ex}")
            print("Returning default MCO")
            return default_mco

    def parse_tke_target_mcos(self, value):
        elv_tke_target_mcos = []
        try:
            # 1:4,6,7-18;2:20-99
            target_mcos_config = value.split(';')
            for target_mco_config in target_mcos_config:
                target_mco_and_floors = target_mco_config.split(':')
                if len(target_mco_and_floors) != 2:
                    elv_tke_target_mcos.append((target_mco_config, []))
                    continue

                target_mco = target_mco_and_floors[0].strip()
                floors = target_mco_and_floors[1].split(',')
                floors_int = []
                for floor in floors:
                    l = floor.split('-')
                    if len(l) == 1:
                        floors_int.append(int(l[0]))
                    else:
                        floors_int += list(range(int(l[0]), int(l[1]) + 1))
                elv_tke_target_mcos.append((target_mco, floors_int))
        
        except ValueError:
            print("Error getting elv_tke_target_mcos")
        return elv_tke_target_mcos


if __name__ == "__main__":
    tke = ThyssenCommunication()
    mco = tke.parse_tke_target_mcos('2')
    print(mco)