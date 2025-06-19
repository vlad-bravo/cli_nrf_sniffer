import time
import sys
from collections import defaultdict

class IndicatorDisplay:
    def __init__(self):
        self.indicators = defaultdict(lambda: {
            'value': 0,
            'additional': 0,
            'last_update': time.time()
        })
        self.display_lines = {}
        self.line_positions = {}
        self.setup_display()

    def setup_display(self):
        # Очищаем консоль и создаем места для показателей
        print("\n" * 8)  # Создаем 8 пустых строк
        sys.stdout.flush()

    def update_indicator(self, code, value, additional):
        self.indicators[code]['value'] = value
        self.indicators[code]['additional'] = additional
        self.indicators[code]['last_update'] = time.time()
        self.update_display()

    def update_display(self):
        # Перемещаем курсор в начало и обновляем строки
        for i, (code, data) in enumerate(self.indicators.items()):
            if code not in self.line_positions:
                self.line_positions[code] = i
            
            time_elapsed = time.time() - data['last_update']
            
            # Формируем строку с информацией
            line = f"Код: {code}, Значение: {data['value']}, Время с обновления: {time_elapsed:.1f}с, Доп: {data['additional']}"
            
            # Перемещаем курсор на нужную строку
            sys.stdout.write(f"\033[{self.line_positions[code] + 1}A")  # Перемещаемся вверх
            sys.stdout.write("\033[K")  # Очищаем строку
            print(line)
        
        # Возвращаем курсор вниз после обновления всех строк
        sys.stdout.write(f"\033[{len(self.indicators)}B")
        sys.stdout.flush()

def parse_packet(packet):
    if len(packet) < 7:
        return None
    
    if packet[0] != 252 or packet[1] != ord('S'):
        return None
    
    code = packet[2]
    value = (packet[3] << 8) | packet[4]
    additional = (packet[5] << 8) | packet[6]
    
    return code, value, additional

def main():
    import serial
    
    # Настройка COM-порта (замените на ваши параметры)
    ser = serial.Serial(
        port='COM1',      # Замените на нужный COM-порт
        baudrate=9600,
        timeout=1
    )
    
    display = IndicatorDisplay()
    
    buffer = bytearray()
    try:
        while True:
            data = ser.read(ser.in_waiting or 1)
            if data:
                buffer.extend(data)
                
                # Ищем начало пакета
                while len(buffer) >= 7:
                    start = buffer.find(252)
                    if start == -1:
                        buffer.clear()
                        break
                    
                    if start > 0:
                        buffer = buffer[start:]
                    
                    if len(buffer) < 7:
                        break
                    
                    # Проверяем второй байт
                    if buffer[1] == ord('S'):
                        # Полный пакет найден
                        packet = buffer[:7]
                        buffer = buffer[7:]
                        
                        # Парсим пакет
                        result = parse_packet(packet)
                        if result:
                            code, value, additional = result
                            display.update_indicator(code, value, additional)
                    else:
                        # Неверный маркер типа пакета, пропускаем
                        buffer = buffer[1:]
    
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
    finally:
        ser.close()

if __name__ == "__main__":
    main()