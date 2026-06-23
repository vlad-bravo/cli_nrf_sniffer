import os
import serial
import time
from colorama import Fore, Style, init
from dotenv import load_dotenv

load_dotenv()
init()

# --- Константы ---
PORT = os.getenv('PORT', 'COM1')
BAUD_RATE = 647000

PACKET_MARKER = b'\xfcS'
PACKET_LENGTH = 7
CODE_OFFSET = 0x40

# Таймауты для статусов (в секундах)
TIMEOUT_NEW = 5
TIMEOUT_UPDATED = 60
TIMEOUT_OLD = 120

# Шаблоны для таблицы
HEADER_TEMPLATE = (
    f"{Fore.GREEN}{'Код':^5} | {'Значение':>9} | {'Время':>7} | {'Пакеты':>7} | "
    f"{'Статус':<10} | {'Код':^6} | {'(Код)':^7} | {'(К1)':^7} | {'(К2)':^7}{Style.RESET_ALL}"
)
SEPARATOR_TEMPLATE = (
    f"{Fore.GREEN}{'-'*5} + {'-'*9} + {'-'*7} + {'-'*7} + {'-'*10} + "
    f"{'-'*6} + {'-'*7} + {'-'*7} + {'-'*7}{Style.RESET_ALL}"
)
ROW_TEMPLATE = (
    f"{Fore.WHITE}{{code:^5}} {Fore.GREEN}| "
    f"{Fore.CYAN}{{value:>9.4f}} {Fore.GREEN}| "
    f"{{time_color}}{{elapsed:>7.1f}} {Fore.GREEN}| "
    f"{Fore.WHITE}{{count:>7}} {Fore.GREEN}| "
    f"{{status_color}}{{status:<11}}{Fore.GREEN}| "
    f"{Fore.WHITE}{{code:^6}} {Fore.GREEN}| "
    f"{Fore.WHITE}{{ord_code:^7X}} {Fore.GREEN}| "
    f"{Fore.WHITE}{{add1:^7X}} {Fore.GREEN}| "
    f"{Fore.WHITE}{{add2:^7X}} {Style.RESET_ALL}"
)


class SerialMonitor:
    def __init__(self, port, baud_rate):
        self.port = port
        self.baud_rate = baud_rate
        self.indicators = {}
        self.printed_lines = 0
        self.buffer = bytearray()

    def process_packet(self, packet):
        """Обрабатывает пакет данных и обновляет показатели."""
        code = packet[2]
        value = int.from_bytes(packet[3:5], byteorder='big')
        code |= CODE_OFFSET
        
        # Определение символа
        symbol = chr(packet[5] if code == 72 else code)
        if code == 68:  # 'D'
            if packet[5] == 0xA6:
                symbol = 'A'
            elif packet[5] == 0x4F:
                symbol = 'E'

        # Обработка значения
        if value > 32767:
            value -= 65536
        value /= 1 if symbol in 'cP' else 16

        # Обновление или добавление показателя (с инкрементацией счетчика пакетов)
        if symbol in self.indicators:
            self.indicators[symbol]['count'] += 1
            self.indicators[symbol]['value'] = value
            self.indicators[symbol]['last_updated'] = time.time()
            self.indicators[symbol]['add1'] = packet[5]
            self.indicators[symbol]['add2'] = packet[6]
        else:
            self.indicators[symbol] = {
                'value': value,
                'last_updated': time.time(),
                'count': 1,  # Инициализация счетчика
                'add1': packet[5],
                'add2': packet[6]
            }

    def parse_buffer(self):
        """Извлекает целые пакеты из буфера."""
        while True:
            # Быстрый поиск маркера начала пакета
            start_idx = self.buffer.find(PACKET_MARKER)
            if start_idx == -1:
                # Если маркера нет, очищаем буфер (оставляем последние байты на случай разорванного маркера)
                if len(self.buffer) > 1:
                    self.buffer = self.buffer[-1:]
                break

            # Проверяем,足够 ли данных для целого пакета
            if start_idx + PACKET_LENGTH > len(self.buffer):
                break

            # Отрезаем мусор до пакета, обрабатываем пакет, удаляем его из буфера
            if start_idx > 0:
                self.buffer = self.buffer[start_idx:]
                
            self.process_packet(self.buffer[:PACKET_LENGTH])
            self.buffer = self.buffer[PACKET_LENGTH:]

    def update_display(self):
        """Обновляет экран, выводя текущие показатели."""
        current_time = time.time()

        # Поднятие курсора вверх
        if self.printed_lines > 0:
            print(f"\033[{self.printed_lines}A", end="")

        # Вывод данных
        for code in sorted(self.indicators, key=lambda x: ord(x)):
            data = self.indicators[code]
            elapsed = current_time - data['last_updated']

            # Определение цвета и статуса
            if elapsed > TIMEOUT_OLD:
                time_color = Fore.LIGHTBLACK_EX
                status = "Архив"
                status_color = Fore.LIGHTBLACK_EX
            elif elapsed > TIMEOUT_UPDATED:
                time_color = Fore.RED
                status = "Устарел"
                status_color = Fore.RED
            elif elapsed > TIMEOUT_NEW:
                time_color = Fore.GREEN
                status = "Обновлен"
                status_color = Fore.GREEN
            else:
                time_color = Fore.YELLOW
                status = "Новый"
                status_color = Fore.YELLOW

            print(ROW_TEMPLATE.format(
                code=code,
                value=data['value'],
                time_color=time_color,
                elapsed=elapsed,
                count=data['count'],
                status_color=status_color,
                status=status,
                ord_code=ord(code),
                add1=data['add1'],
                add2=data['add2']
            ))

        self.printed_lines = len(self.indicators)

    def run(self):
        """Основной цикл программы."""
        try:
            ser = serial.Serial(self.port, self.baud_rate, timeout=0.2)
            ser.write(b's')
        except serial.SerialException as e:
            print(f"{Fore.RED}Ошибка открытия порта {self.port}: {e}{Style.RESET_ALL}")
            return

        # Печать заголовков один раз
        print(HEADER_TEMPLATE)
        print(SEPARATOR_TEMPLATE)

        try:
            while True:
                data = ser.read(100)
                if data:
                    self.buffer.extend(data)
                    self.parse_buffer()
                
                self.update_display()
                time.sleep(0.1)
                
        except KeyboardInterrupt:
            # При выходе печатаем пустые строки, чтобы затереть таблицу и избежать артефактов терминала
            if self.printed_lines > 0:
                print(f"\033[{self.printed_lines}A", end="")
                for _ in range(self.printed_lines):
                    print(" " * 80)
            print(f"\n{Fore.YELLOW}Программа остановлена.{Style.RESET_ALL}")
        finally:
            ser.close()


if __name__ == "__main__":
    monitor = SerialMonitor(PORT, BAUD_RATE)
    monitor.run()
