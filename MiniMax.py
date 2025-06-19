import serial
import time
import os

# Настройки COM-порта
PORT = 'COM7'  # Укажите ваш COM-порт (например, '/dev/ttyUSB0' для Linux)
BAUD_RATE = 647000

# Словарь для хранения показателей: {код: {'value': значение, 'last_updated': время}}
indicators = {}

def process_packet(packet):
    """Обрабатывает пакет данных и обновляет показатели."""
    if len(packet) < 7:
        return
    if packet[0] != 0xFC or packet[1] != ord('S'):
        return  # Проверка маркера и типа пакета
    code = packet[2]
    value = int.from_bytes(packet[3:5], byteorder='big')
    # Обновляем или добавляем показатель
    indicators[code] = {
        'value': value,
        'last_updated': time.time()
    }

def update_display():
    """Обновляет экран, выводя текущие показатели."""
    os.system('cls' if os.name == 'nt' else 'clear')  # Очистка экрана
    current_time = time.time()
    # Сортируем коды для упорядоченного вывода
    for code in sorted(indicators):
        data = indicators[code]
        elapsed = current_time - data['last_updated']
        print(f"Код: {code}, Значение: {data['value']}, Время: {elapsed:.1f} сек")

def main():
    try:
        ser = serial.Serial(PORT, BAUD_RATE, timeout=0.1)
    except serial.SerialException as e:
        print(f"Ошибка открытия порта {PORT}: {e}")
        return

    buffer = bytearray()

    try:
        while True:
            # Чтение данных из порта
            data = ser.read(100)
            if data:
                buffer.extend(data)
                # Обработка буфера для извлечения пакетов
                while True:
                    # Поиск начала пакета (0xFC, 0x53)
                    start_idx = None
                    for i in range(len(buffer) - 1):
                        if buffer[i] == 0xFC and buffer[i+1] == ord('S'):
                            start_idx = i
                            break
                    if start_idx is None:
                        break  # Нет начала пакета
                    # Проверка наличия всех 7 байт пакета
                    if start_idx + 6 >= len(buffer):
                        break  # Недостаточно данных
                    # Извлечение и обработка пакета
                    packet = buffer[start_idx:start_idx+7]
                    process_packet(packet)
                    # Удаление обработанных байтов из буфера
                    buffer = buffer[start_idx+7:]
            # Обновление экрана
            update_display()
            time.sleep(0.1)  # Задержка для снижения нагрузки
    except KeyboardInterrupt:
        print("\nПрограмма остановлена.")
    finally:
        ser.close()

if __name__ == "__main__":
    main()
