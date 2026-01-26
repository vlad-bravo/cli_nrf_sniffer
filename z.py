import serial
import time
import sys
import os
import threading
from dotenv import load_dotenv

load_dotenv()

# Настройки COM-порта
PORT_NAME = os.getenv('PORT', 'COM1')
BAUD_RATE = 647000

# --- ГЛОБАЛЬНЫЕ ПЕРЕМЕННЫЕ ---
indicators = {}     # Словарь для хранения данных: {code: {'value': val, 'time': ts}}
display_order = []  # Список для сохранения порядка появления кодов
last_update_time = 0 # Время последнего обновления данных

def read_serial_thread(ser):
    """
    Поток для чтения данных из COM-порта.
    """
    global last_update_time
    buffer = bytearray()

    while True:
        # Читаем доступные байты
        data = ser.read(ser.in_waiting or 1)
        if not data:
            time.sleep(0.01)
            continue
        
        buffer.extend(data)

        # Обработка буфера
        while len(buffer) > 0:
            # Ищем маркер начала пакета (252)
            start_idx = buffer.find(252)
            
            # Если маркер не найден, очищаем буфер (мусор)
            if start_idx == -1:
                buffer.clear()
                continue
            
            # Удаляем всё, что было до маркера (если были лишние байты)
            if start_idx > 0:
                del buffer[:start_idx]
            
            # Проверяем, достаточно ли данных для пакета (7 байт)
            if len(buffer) < 7:
                break
            
            # Проверяем тип пакета (должен быть 'S')
            if buffer[1] != ord('S'):
                # Если это не 'S', сдвигаемся на 1 байт и ищем заново (resync)
                del buffer[:1]
                continue
            
            # --- ПАРСИНГ ПАКЕТА ---
            # Byte 0: 252 (уже проверено)
            # Byte 1: 'S' (уже проверено)
            code = buffer[2]
            
            # Bytes 3-4: Big Endian величина показателя
            value = int.from_bytes(buffer[3:5], byteorder='big')
            
            # Bytes 5-6: Дополнительные данные (не используются для отображения по заданию)
            
            # Сохраняем данные
            current_time = time.time()
            
            if code not in indicators:
                indicators[code] = {}
                display_order.append(code)
            
            indicators[code]['value'] = value
            indicators[code]['time'] = current_time
            last_update_time = current_time
            
            # Удаляем обработанный пакет из буфера
            del buffer[:7]

def update_display():
    """
    Функция обновления текста в консоли.
    Использует ANSI-коды для перемещения курсора в начало (Home).
    """
    # Перемещаем курсор в начало консоли
    sys.stdout.write("\033[H")
    sys.stdout.flush()
    
    current_time = time.time()
    
    print(f"Мониторинг порта: {PORT_NAME} | Получено показателей: {len(indicators)}")
    print("-" * 60)
    
    # Проходим по всем известным кодам в порядке их появления
    for code in display_order:
        data = indicators[code]
        val = data['value']
        last_ts = data['time']
        
        # Вычисляем время с последнего обновления
        elapsed = current_time - last_ts
        
        # Формируем строку
        # \033[K - очистка строки до конца (чтобы не оставались артефакты от предыдущих длинных строк)
        line = f"Код: {code} | Величина: {val:<5} | Время после обновления: {elapsed:.1f} с"
        print(f"\033[K{line}")

def main():
    try:
        ser = serial.Serial(PORT_NAME, BAUD_RATE, timeout=1)
    except serial.SerialException as e:
        print(f"Ошибка открытия порта {PORT_NAME}: {e}")
        return

    print(f"Ожидание данных на {PORT_NAME}...")
    
    # Очищаем экран при старте для красоты
    print("\033[2J", end="")

    # Запускаем поток чтения в фоновом режиме
    thread = threading.Thread(target=read_serial_thread, args=(ser,), daemon=True)
    thread.start()

    try:
        while True:
            # Обновляем дисплей
            update_display()
            time.sleep(0.1) # Частота обновления экрана (10 раз в секунду)
            
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
        ser.close()

if __name__ == "__main__":
    main()
