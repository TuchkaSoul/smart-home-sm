import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib import colors as mcolors
import numpy as np
import math
import random
import sympy
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

lamd=10
mu_1=2
mu_2=8
kanal_mu={
    "канал 1": mu_1,
    "канал 2": mu_2
}
N=70
class RequestCar:
    def __init__(self, id, input_time):
        self.id = id  # Уникальный идентификатор заявки
        self.input_time = input_time  # Время поступления заявки
        self.start_service_time = None  # Время начала обслуживания
        self.served_in = []  # Каналы обслуживания, через которые прошла заявка
        self.rejected = False  # Флаг отказа в обслуживании
        self.output_time = None  # Время завершения обслуживания
        self.queue_time = 0  # Общее время ожидания в очереди
        self.service_time = 0  # Общее время обслуживания
        self.total_time_in_system = 0  # Время пребывания в системе

    def set_service_start(self, start_time, channel):
        """Фиксирует начало обслуживания заявки."""
        self.start_service_time = start_time
        self.served_in.append(channel)
        self.queue_time = start_time - self.input_time  # Время в очереди

    def set_service_end(self, end_time):
        """Фиксирует завершение обслуживания заявки."""
        self.output_time = end_time
        self.service_time = end_time - self.start_service_time
        self.total_time_in_system = end_time - self.input_time

    def mark_rejected(self):
        """Помечает заявку как отклоненную."""
        self.rejected = True
        self.total_time_in_system = 0  # Заявка не обслужена, значит, не находилась в системе
    def __str__(self):
        """Вывод информации о заявке."""
        status = "Отклонена" if self.rejected else "Обслужена"
        return (f"Заявка {self.id}\t: Время поступления {self.input_time}, "
                f"Статус: {status}, Время ожидания: {self.queue_time}, "
                f"Обслуживалась в: {self.served_in}, Время завершения: {self.output_time}")

def generator_gap(x):
    return (-1/x)*math.log(random.uniform(0,1))

requests=[round(generator_gap(lamd),3)]
for i in range(0,N,1):
    requests.append(round(requests[-1]+generator_gap(lamd),3))
print(requests)

def service_class(requests, number_queue):
    kanal_mu = {"канал 1": 3, "канал 2": 7}  # Интенсивность обслуживания
    request_objects = [RequestCar(idx,requests[idx]) for idx in range(len(requests))]

    table = {
        "запросы": requests,
        "канал 1": [],
        "канал 2": [],
        "обслуженно": [],
        "отказ": [],
    }

    for i in range(number_queue):
        table[f"очередь {i+1}"] = []

    choice_col = list(table.keys())[2:0:-1]
    choice_queue = list(table.keys())[5:]

    for req_obj in request_objects:
        req = req_obj.input_time
        is_served = False

        for kanal in choice_col:
            if not table[kanal] or table[kanal][-1][1] <= req:
                start_time = req
                end_time = round(req + generator_gap(kanal_mu[kanal]), 3)
                table[kanal].append((start_time, end_time))
                table['обслуженно'].append((table[kanal][-1], req_obj.id))

                req_obj.set_service_start(start_time, kanal)
                req_obj.set_service_end(end_time)
                is_served = True
                break

        if is_served:
            continue

        near_time = min(table["канал 1"][-1][1], table["канал 2"][-1][1])
        near_kanal = "канал 2" if table["канал 2"][-1][1] == near_time else "канал 1"

        if table[f"очередь {number_queue}"]:
            if table[f"очередь {number_queue}"][-1][1] >= req:
                table['отказ'].append((req, req_obj.id))
                req_obj.mark_rejected()
                continue

        near_queue = number_queue
        for i in range(number_queue - 1, 0, -1):
            if not table[f"очередь {i}"] or table[f"очередь {i}"][-1][1] <= req:
                near_queue = i

        enum = [near_kanal] + choice_queue[:near_queue]
        enum.reverse()
        prev = req

        for i in range(1, len(enum)):
            if not table[enum[i - 1]] or table[enum[i - 1]][-1][1]:
                a = (prev, table[enum[i]][-1][1])
                table[enum[i - 1]].append(a)
                prev = table[enum[i]][-1][1]
                req_obj.served_in.append(enum[i - 1])

        start_time = prev
        end_time = round(near_time + generator_gap(kanal_mu[near_kanal]), 3)
        table[near_kanal].append((start_time, end_time))
        table['обслуженно'].append((table[near_kanal][-1], req_obj.id))

        req_obj.set_service_start(start_time, near_kanal)
        req_obj.set_service_end(end_time)

    return table, request_objects

table, request_objects = service_class(requests, 3)
for i in zip(table.keys(),table.values()):
    print(len(i[1]),i)  
for req_obj in request_objects:
    print(req_obj)

def visualize_service_system(table, num_queues=3):
    fig, ax = plt.subplots(figsize=(100, 6))
    
    # Настройки внешнего вида
    colors = {
        'запросы': 'lightgray',
        'канал 1': 'lightblue',
        'канал 2': 'lightgreen',
        'очередь 1': 'mistyrose',
        'очередь 2': 'peachpuff',
        'очередь 3': 'lavender',
        'отказ': 'red',
        'обслуженно': 'limegreen'  # Новый цвет для обслуженных заявок
    }
    
    # Определение вертикальных позиций для каждой строки
    y_positions = {
        'запросы': 7,  # Сдвигаем вверх на 1
        'обслуженно': 6,  # Новая строка для обслуженных заявок
        'канал 1': 5,
        'канал 2': 4,
        'очередь 1': 3,
        'очередь 2': 2,
        'очередь 3': 1,
        'отказ': 0
    }
    
    # Отрисовка заявок (временные точки с индексами)
    for idx, time in enumerate(table['запросы']):
        # Точка заявки
        ax.plot(time, y_positions['запросы'], 'o', color=colors['запросы'], markersize=6)
        
        # Текст с индексом и временем
        ax.text(time, y_positions['запросы'] + 0.2, f"{idx}\n{time:.2f}", 
                ha='center', va='bottom', fontsize=7)
        
        # Вертикальная пунктирная линия через всю высоту графика
        ax.axvline(x=time, color='gray', linestyle=':', alpha=0.6, linewidth=0.8)
    
    # Отрисовка обслуженных заявок
    for segment, req_id in table['обслуженно']:
        start, end = segment
        # Прямоугольник для периода обслуживания
        ax.add_patch(patches.Rectangle(
            (start, y_positions['обслуженно'] - 0.4), end-start, 0.8,
            facecolor=colors['обслуженно'], edgecolor='black', alpha=0.6
        ))
        # Текст с ID заявки в центре отрезка
        ax.text((start + end)/2, y_positions['обслуженно'], 
                f"{req_id}", ha='center', va='center', fontsize=8)
    
    # Функция для отображения временных меток на отрезках
    def draw_segment_labels(start, end, y_pos, color='black'):
        duration = end - start
        mid_x = (start + end) / 2
        
        # Время начала
        ax.text(start, y_pos - 0.3, f"{start:.2f}", 
                ha='left', va='top', fontsize=7, color=color)
        
        # Время конца
        ax.text(end, y_pos - 0.3, f"{end:.2f}", 
                ha='right', va='top', fontsize=7, color=color)
        
        # Длительность в центре
        ax.text(mid_x, y_pos, f"{duration:.2f}", 
                ha='center', va='center', fontsize=8, color=color, weight='bold')
    
    # Отрисовка каналов обслуживания с подписями
    for channel in ['канал 1', 'канал 2']:
        for start, end in table[channel]:
            ax.add_patch(patches.Rectangle(
                (start, y_positions[channel] - 0.4), end-start, 0.8,
                facecolor=colors[channel], edgecolor='black'
            ))
            draw_segment_labels(start, end, y_positions[channel])
    
    # Отрисовка очередей с подписями
    for queue in [f'очередь {i+1}' for i in range(num_queues)]:
        if queue in table:
            for start, end in table[queue]:
                ax.add_patch(patches.Rectangle(
                    (start, y_positions[queue] - 0.4), end-start, 0.8,
                    facecolor=colors[queue], edgecolor='black'
                ))
                draw_segment_labels(start, end, y_positions[queue])
    
    # Отрисовка отказов
    for time, req_id in table['отказ']:
        ax.plot(time, y_positions['отказ'], 'ro', markersize=6)
        ax.text(time, y_positions['отказ'] - 0.3, f"{req_id}\n{time:.2f}", 
                ha='center', va='top', fontsize=7, color='red')
    
    # Настройка осей и подписей
    ax.set_yticks([y_positions[k] for k in y_positions])
    ax.set_yticklabels(['Заявки', 'Обслуженно', '1 канал', '2 канал', 
                       '1 место', '2 место', '3 место', 'Отказ'])
    ax.set_xlabel('Время (Тн)')
    ax.set_title('Схема обслуживания заявок с временными метками')
    
    # Настройка сетки
    ax.xaxis.set_major_locator(MultipleLocator(1))
    ax.grid(which='major', linestyle='-', alpha=0.8)
    plt.minorticks_on()
    plt.tight_layout()
    
    plt.show()
# Пример использования с вашими данными

def filter_table_by_time_range(table, start_time, end_time):
    """
    Фильтрует данные в таблице, оставляя только те, которые попадают в указанный временной диапазон.
    
    Параметры:
        table (dict): Исходная таблица с данными
        start_time (float): Начальное время диапазона
        end_time (float): Конечное время диапазона
    
    Возвращает:
        dict: Отфильтрованная таблица
    """
    filtered_table = {}
    
    for key, data_list in table.items():
        filtered_data = []
        
        for item in data_list:
            # Определяем временные границы элемента
            if isinstance(item, (int, float)):
                # Для простых временных меток
                time = item
                time_start = time_end = time
            elif len(item) == 2:
                if isinstance(item[0], (int, float)):
                    # Для пар (время, ID)
                    time = item[0]
                    time_start = time_end = time
                else:
                    # Для интервалов (start, end)
                    time_start, time_end = item[0]
            else:
                continue  # Пропускаем неподдерживаемые форматы
            
            # Проверяем попадание в диапазон
            if time_end >= start_time and time_start <= end_time:
                filtered_data.append(item)
        
        filtered_table[key] = filtered_data
    
    return filtered_table
table1=filter_table_by_time_range(table,table["запросы"][-1]*0.15,table["запросы"][-1]*0.85)
for i in zip(table1.keys(),table1.values()):
    print(len(i[1]),i)
    
visualize_service_system(table)
visualize_service_system(table1)