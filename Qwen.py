import serial
import time
from datetime import datetime

# Настройки COM-порта
PORT = 'COM7'  # Заменить на нужный порт
BAUD_RATE = 647000

# Инициализация порта
ser = serial.Serial(PORT, BAUD_RATE, timeout=1)

# Словарь для хранения данных показателей
indicators = {}  # {code: (value, timestamp)}

def clear_line(n=1):
    """Очистка n строк выше текущей"""
    for _ in range(n):
        print('\x1b[A\x1b[2K', end='')

def update_display():
    """Обновление отображения показателей"""
    global indicators
    clear_line(len(indicators))
    for code in sorted(indicators):
        value, timestamp = indicators[code]
        delta = int(time.time() - timestamp)
        print(f"Код: {code} | Значение: {value} | Время без обновления: {delta} сек")

try:
    print("Ожидание данных...")
    while True:
        if ser.in_waiting >= 7:  # Минимальная длина пакета — 7 байт
            data = ser.read(7)

            start_byte = data[0]
            packet_type = data[1]
            code = data[2]
            value = int.from_bytes(data[3:5], byteorder='big')
            code |= 0x40
            code = chr(data[5] if code == 72 else code)
            if value > 32767:
                value -= 65536
            value /= 1 if code in 'cP' else 16
            extra = data[5:7]  # Не используется в этом примере

            if start_byte == 252 and packet_type == ord('S'):
                current_time = time.time()
                if code in indicators:
                    # Обновляем существующий показатель
                    indicators[code] = (value, current_time)
                else:
                    # Добавляем новый показатель
                    indicators[code] = (value, current_time)
                update_display()

        time.sleep(0.1)  # Защита от перегрузки процессора

except KeyboardInterrupt:
    print("\nПрограмма остановлена пользователем.")

except Exception as e:
    print(f"\nОшибка: {e}")

finally:
    ser.close()