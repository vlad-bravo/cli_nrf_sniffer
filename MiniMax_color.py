import serial
import time
import os
from colorama import Fore, Style, init

# Инициализация colorama
init()

# Настройки COM-порта
PORT = 'COM7'  # Укажите ваш COM-порт
BAUD_RATE = 647000

# Словарь для хранения показателей
indicators = {}

def process_packet(packet):
    """Обрабатывает пакет данных и обновляет показатели."""
    if len(packet) < 7:
        return
    if packet[0] != 0xFC or packet[1] != ord('S'):
        return  # Проверка маркера и типа пакета
    code = packet[2]
    value = int.from_bytes(packet[3:5], byteorder='big')
    code |= 0x40
    symbol = chr(packet[5] if code == 72 else code)
    if value > 32767:
        value -= 65536
    value /= 1 if symbol in 'cP' else 16
    # Обновляем или добавляем показатель
    indicators[symbol] = {
        'value': value,
        'last_updated': time.time()
    }

def update_display():
    """Обновляет экран, выводя текущие показатели."""
    os.system('cls' if os.name == 'nt' else 'clear')  # Очистка экрана
    current_time = time.time()
    
    # Заголовок с цветной рамкой
    print(f"\n{Fore.CYAN}╔{'═'*60}╗{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL}   {Fore.GREEN}Система мониторинга показателей{Style.RESET_ALL}   {Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}╠{'═'*60}╣{Style.RESET_ALL}")
    print(f"{Fore.CYAN}║{Style.RESET_ALL}   Время обновления: {Fore.YELLOW}{time.strftime('%Y-%m-%d %H:%M:%S')}{Style.RESET_ALL}   {Fore.CYAN}║{Style.RESET_ALL}")
    print(f"{Fore.CYAN}╚{'═'*60}╝{Style.RESET_ALL}\n")
    
    # Заголовок таблицы
    print(f"{Fore.GREEN}{'Код':<6} | {'Значение':>12} | {'Время (сек)':>12} | {'Статус':<10}{Style.RESET_ALL}")
    print(f"{Fore.GREEN}{'-'*6} | {'-'*12} | {'-'*12} | {'-'*10}{Style.RESET_ALL}")
    
    # Вывод данных
    for code in sorted(indicators, key=lambda x: ord(x)):
        data = indicators[code]
        elapsed = current_time - data['last_updated']
        value = data['value']
        
        # Определение цвета времени
        if elapsed > 10:
            time_color = Fore.RED
            status = "Устарел"
            status_color = Fore.RED
        elif elapsed > 5:
            time_color = Fore.YELLOW
            status = "Обновлен"
            status_color = Fore.YELLOW
        else:
            time_color = Fore.GREEN
            status = "Обновлен"
            status_color = Fore.GREEN
        
        print(
            f"{Fore.WHITE}{code:<6} | "
            f"{Fore.CYAN}{value:>12.2f} | "
            f"{time_color}{elapsed:>12.1f} | "
            f"{status_color}{status:<10}{Style.RESET_ALL}"
        )

def main():
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=0.2)
    except serial.SerialException as e:
        print(f"{Fore.RED}Ошибка открытия порта {PORT}: {e}{Style.RESET_ALL}")
        return

    buffer = bytearray()

    try:
        while True:
            data = ser.read(100)
            if data:
                buffer.extend(data)
                while True:
                    start_idx = None
                    for i in range(len(buffer) - 1):
                        if buffer[i] == 0xFC and buffer[i+1] == ord('S'):
                            start_idx = i
                            break
                    if start_idx is None:
                        break
                    if start_idx + 6 >= len(buffer):
                        break
                    packet = buffer[start_idx:start_idx+7]
                    process_packet(packet)
                    buffer = buffer[start_idx+7:]
            update_display()
            time.sleep(0.1)
    except KeyboardInterrupt:
        print(f"\n{Fore.YELLOW}Программа остановлена.{Style.RESET_ALL}")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
