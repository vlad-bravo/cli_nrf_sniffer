import time
import sys
from collections import defaultdict
from struct import unpack as struct_unpack

class IndicatorDisplay:
    def __init__(self):
        self.indicators = defaultdict(lambda: {
            'value': 0,
            'byte1': 0,
            'byte2': 0,
            'last_update': time.time()
        })
        self.display_lines = {}
        self.line_positions = {}
        self.setup_display()

    def setup_display(self):
        # Очищаем консоль и создаем места для показателей
        print("\n" * 8)  # Создаем 8 пустых строк
        sys.stdout.flush()

    def update_indicator(self, code, value, byte1, byte2):
        self.indicators[code]['value'] = value
        self.indicators[code]['byte1'] = byte1
        self.indicators[code]['byte2'] = byte2
        self.indicators[code]['last_update'] = time.time()
        self.update_display()

    def update_display(self):
        # Перемещаем курсор в начало и обновляем строки
        for i, (code, data) in enumerate(self.indicators.items()):
            if code not in self.line_positions:
                self.line_positions[code] = i
            
            time_elapsed = time.time() - data['last_update']
            
            # Формируем строку с информацией
            line = f"Код: {code} ({ord(code):3}), Значение: {data['value']:10.4f}, Время с обновления: {time_elapsed:4.1f}с, Доп: {data['byte1']} {data['byte2']}"
            
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
    
    marker, packet_type, code, value, byte1, byte2 = struct_unpack('>BcBH2B', packet)
    code |= 0x40
    symbol = chr(byte1 if code == 72 else code)
    if value > 32767:
        value -= 65536
    value /= 1 if symbol in 'cP' else 16
    
    return symbol, value, byte1, byte2

def main():
    import serial
    
    # Настройка COM-порта (замените на ваши параметры)
    ser = serial.Serial(
        port='COM7',      # Замените на нужный COM-порт
        baudrate=647000,
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
                            code, value, byte1, byte2 = result
                            display.update_indicator(code, value, byte1, byte2)
                    else:
                        # Неверный маркер типа пакета, пропускаем
                        buffer = buffer[1:]
    
    except KeyboardInterrupt:
        print("\nЗавершение работы...")
    finally:
        ser.close()

if __name__ == "__main__":
    main()