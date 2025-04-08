import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import json
import xml.etree.ElementTree as ET
from functools import lru_cache
from collections import deque
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import math  # Для нелинейных функций
# Константы
WIDTH, HEIGHT = 600, 600  # Размеры окна для симуляции
GRID_ROWS, GRID_COLS = 30, 30  # Размер сетки
CELL_SIZE = WIDTH // GRID_COLS  # Размер ячейки

# Определение типов клеток
EMPTY, WALL, DOOR, WINDOW, HEATER, AC, OUTSIDE, SENSOR = range(8)

# Константы для ключей
TEMPERATURES = "temperatures"
COEFFICIENTS = "coefficients"
OUTSIDE_TEMP = "OUTSIDE_TEMP"
HEATER_TEMP = "HEATER_TEMP"
AC_TEMP = "AC_TEMP"
INITIAL_ROOM_TEMP = "INITIAL_ROOM_TEMP"
WALL_RESISTANCE = "WALL_RESISTANCE"
AIR_FLOW = "AIR_FLOW"
OPEN_DOOR_FLOW = "OPEN_DOOR_FLOW"
WINDOW_FLOW = "WINDOW_FLOW"
TARGET_TEMP = "TARGET_TEMP"
WINDOW_OPENNESS= "WINDOW_OPENNESS"
KP="KP"  # Пропорциональный коэффициент
KI="KI"  # Интегральный коэффициент
KD="KD"

# Константы регуляторов
RELAY = 0
PI = 1
PID = 2

@lru_cache(maxsize=1000)
def get_color_for_temp(temp):
    """Возвращает цвет в формате HEX в зависимости от температуры."""
    if temp < -30:
        return "#0000FF"
    elif -30 <= temp < 0:
        ratio = (temp + 30) / 30
        blue = 255
        green = int(255 * ratio)
        red = 0
    elif 0 <= temp <= 32:
        ratio = temp / 32
        blue = int(255 * (1 - ratio))
        green = 255
        red = 0
    elif 32 < temp <= 70:
        ratio = (temp - 32) / 32
        blue = 0
        green = int(255 * (1 - ratio))
        red = 255
    else:
        return "#FF0000"

    red = max(0, min(255, red))
    green = max(0, min(255, green))
    blue = max(0, min(255, blue))
    return f"#{red:02x}{green:02x}{blue:02x}"

from collections import deque
import time

from collections import deque
import time

class TemperatureController:
    """Усовершенствованный регулятор температуры с плавными переходами"""
    def __init__(self, target_temp=22):
        self.target_temp = target_temp
        self.controller_type = RELAY
        
        # Состояние устройств
        self.heater_on = True
        self.ac_on = True
        self.heater_temp = 60.0    # Начальная температура нагревателя
        self.ac_temp = 18.0        # Начальная температура кондиционера
        self.window_openness = 0.5 # Степень открытия окон (0-1)
        
        # Параметры регуляторов
        self.Kp = 1.5    # Пропорциональный коэффициент
        self.Ki = 0.1    # Интегральный коэффициент
        self.Kd = 0.8    # Дифференциальный коэффициент
        self.integral = 0.0
        self.prev_error = 0.0
        self.prev_time = 0
        self.integral_max = 100.0
        
        # Параметры плавных переходов
        self.transition_factor = 0.9  # Коэффициент плавности (0.8-0.95)
        self.soft_start_steps = 10    # Шагов плавного старта
        self.current_step = 0
        
        # История для анализа
        self.temp_history = deque(maxlen=600)
        self.time_history = deque(maxlen=600)
        self.output_history = deque(maxlen=600)
        self.action_history = deque(maxlen=600)

    def set_target_temp(self, temp):
        """Установка целевой температуры с плавным переходом"""
        self.target_temp = temp
        self.reset(soft=True)

    def set_controller_type(self, c_type):
        """Смена типа регулятора с плавным переходом"""
        self.controller_type = c_type
        self.reset(soft=True)

    def reset(self, soft=True):
        """Плавный сброс состояния регулятора"""
        if soft:
            # Плавный сброс (сохраняем часть состояния)
            self.integral *= 0.7
            self.prev_error *= 0.5
            self.current_step = 0
            
            # Плавное изменение температуры устройств
            if self.heater_on:
                self.heater_temp *= 0.8
            if self.ac_on:
                self.ac_temp = min(22, self.ac_temp * 1.2)
        else:
            # Полный сброс
            self.integral = 0
            self.prev_error = 0
            self.current_step = 0
            self.heater_temp = 60
            self.ac_temp = 18
        
        self.window_openness = 0.5
        self.heater_on = False
        self.ac_on = False

    def update(self, current_temp, current_time):
        """Обновление состояния с плавными переходами"""
        # Расчет временного шага
        dt = max(1, current_time - self.prev_time)
        self.prev_time = current_time
        
        error = self.target_temp - current_temp
        self.temp_history.append(current_temp)
        self.time_history.append(current_time)
        
        # Режим плавного старта после сброса
        if self.current_step < self.soft_start_steps:
            self.current_step += 1
            smooth_factor = self.current_step / self.soft_start_steps
        else:
            smooth_factor = 1.0
        
        # Расчет выходного сигнала
        if self.controller_type == RELAY:
            output = self._relay_control(error)
        elif self.controller_type == PI:
            output = self._pi_control(error, dt, smooth_factor)
        elif self.controller_type == PID:
            output = self._pid_control(error, dt, smooth_factor)
        
        # Применение выходного сигнала
        self._apply_output(output, error, smooth_factor)
        
        self.output_history.append(output)
        return output

    def _relay_control(self, error):
        """Релейный регулятор с гистерезисом"""
        if error > 2:    # +2° гистерезис
            return 1.0
        elif error < -0.6: 
            return -1.0
        return 0.0

    def _pi_control(self, error, dt, smooth_factor):
        """PI регулятор с плавными переходами"""
        self.integral += error * dt * smooth_factor
        self.integral = max(min(self.integral, self.integral_max), -self.integral_max)
        return self.Kp * error + self.Ki * self.integral

    def _pid_control(self, error, dt, smooth_factor):
        """PID регулятор с плавными переходами"""
        self.integral += error * dt * smooth_factor
        self.integral = max(min(self.integral, self.integral_max), -self.integral_max)
        
        derivative = (error - self.prev_error) / dt if dt > 0 else 0
        self.prev_error = error
        
        return (self.Kp * error + 
                self.Ki * self.integral + 
                self.Kd * derivative * smooth_factor)

    def _apply_output(self, output, error, smooth_factor):
        """Плавное применение управляющих воздействий"""
        # Плавное управление нагревателем
        if output > 0.1:
            self.heater_on = True
            self.ac_on = False
            target_temp = 30 + min(30, abs(output) * 15)
            self.heater_temp = self._smooth_transition(self.heater_temp, target_temp)
            
            # Плавное управление окнами
            target_openness = max(0.1, 0.5 - abs(output)/3)
            self.window_openness = self._smooth_transition(self.window_openness, target_openness)
        
        # Плавное управление кондиционером
        elif output < -0.1:
            self.heater_on = False
            self.ac_on = True
            target_temp = 22 - min(10, abs(output) * 5)
            self.ac_temp = self._smooth_transition(self.ac_temp, target_temp)
            
            # Плавное управление окнами
            target_openness = min(0.9, 0.5 + abs(output)/3)
            self.window_openness = self._smooth_transition(self.window_openness, target_openness)
        
        # Нейтральный режим
        else:
            self.heater_on = False
            self.ac_on = False
            # Плавный возврат окон в нейтральное положение
            self.window_openness = self._smooth_transition(self.window_openness, 0.5)
            
            # Плавный сброс температур устройств
            if self.heater_temp > 30:
                self.heater_temp = self._smooth_transition(self.heater_temp, 30)
            if self.ac_temp < 22:
                self.ac_temp = self._smooth_transition(self.ac_temp, 22)

        # Дополнительная плавность при переходных процессах
        self.heater_temp = self._apply_smoothness(self.heater_temp, smooth_factor)
        self.ac_temp = self._apply_smoothness(self.ac_temp, smooth_factor)
        self.window_openness = self._apply_smoothness(self.window_openness, smooth_factor)

    def _smooth_transition(self, current, target):
        """Плавный переход между значениями"""
        return current * self.transition_factor + target * (1 - self.transition_factor)

    def _apply_smoothness(self, value, factor):
        """Применение коэффициента плавности"""
        return value * factor + value * (1 - factor) * self.transition_factor

class Sensor:
    """Класс датчика температуры с графиком"""
    def __init__(self, y, x):
        self.y = y
        self.x = x
        self.temp_history = []
        self.time_history = []
        self.figure = None
        self.canvas = None
        
    def update(self, temp,time):
        """Обновляет историю температур"""
        self.temp_history.append(temp)
        self.time_history.append(time/1000)
        if len(self.temp_history) > 600:
            self.temp_history.pop(0)
            self.time_history.pop(0)
        
    

class SmartHomeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Умный дом — Симуляция и Управление")
        self.time_tick = 0
        self.regulator_enabled = False  # Флаг активности регулятора

        # Основные фреймы
        main_frame = ttk.Frame(root)
        main_frame.pack(fill="both", expand=True)

        # Левая часть (Симуляция)
        sim_frame = ttk.Frame(main_frame)
        sim_frame.grid(row=0, column=0, padx=10, pady=10)
        self.canvas = tk.Canvas(sim_frame, width=WIDTH, height=HEIGHT)
        self.canvas.pack()

        # Правая часть (Панель управления)
        control_frame = ttk.Frame(main_frame)
        control_frame.grid(row=0, column=1, padx=10, pady=10, sticky="ns")

        # Инициализация данных
        self.initial_data = {
            TEMPERATURES: {
                OUTSIDE_TEMP: -25,
                HEATER_TEMP: 45,
                AC_TEMP: 18,
                INITIAL_ROOM_TEMP: -10,
                TARGET_TEMP: 22
            },
            COEFFICIENTS: {
                WALL_RESISTANCE: 0.01,
                AIR_FLOW: 0.4,
                OPEN_DOOR_FLOW: 0.7,
                WINDOW_FLOW: 0.6,
                WINDOW_OPENNESS: 0.5,
                KP: 1.5,  # Пропорциональный коэффициент
                KI: 0.1,  # Интегральный коэффициент
                KD: 0.8   # Дифференциальный коэффициент
            }
        }

        # Инициализация регулятора
        self.controller = TemperatureController(self.initial_data[TEMPERATURES][TARGET_TEMP])
        self.time_speed = tk.IntVar(value=10)
        self.selected_type = tk.IntVar(value=HEATER)
        self.controller_type = tk.IntVar(value=RELAY)
        self.sensors = []
        self.graph_window = None

        # Загрузка и инициализация
        self.load_json("default.json")
        self.draw_grid()
        self.root.after(1000, self.simulation_step)

        # Обработчики событий
        self.canvas.bind("<Button-1>", self.set_cell)
        self.canvas.bind("<Button-3>", self.clear_cell)
        self.canvas.bind("<Button-2>", self.curs)

        # Создание интерфейса
        self.create_control_panel(control_frame)
        self.add_cell_panel(control_frame)

    def initialize_matrices(self):
        """Создает и инициализирует основные матрицы."""
        type_matrix = np.full((GRID_ROWS, GRID_COLS), OUTSIDE, dtype=int)
        temp_matrix = np.full((GRID_ROWS, GRID_COLS), self.initial_data[TEMPERATURES][OUTSIDE_TEMP], dtype=float)

        # Устанавливаем стены дома
        type_matrix[1:-1, 1:-1] = EMPTY
        type_matrix[2:-2, 2:-2] = EMPTY

        type_matrix[2, 2:-2] = WALL
        type_matrix[-3, 2:-2] = WALL
        type_matrix[2:-2, 2] = WALL
        type_matrix[2:-2, -3] = WALL

        # Внутренняя температура
        temp_matrix[2:-2, 2:-2] = self.initial_data[TEMPERATURES][INITIAL_ROOM_TEMP]

        return type_matrix, temp_matrix

    def draw_grid(self):
        """Рисует сетку и температурное поле."""
        self.canvas.delete("all")

        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                cell_type = self.type_matrix[y, x]

                if cell_type == WALL:
                    color = "gray"
                elif cell_type == DOOR:
                    color = "orange"
                elif cell_type == WINDOW:
                    color = "lightgray"
                
                elif cell_type == AC:
                    color = "blue"
                elif cell_type == SENSOR:
                    color = "green"
                else:
                    temp = self.temp_matrix[y, x]
                    color = get_color_for_temp(temp)

                x1, y1 = x * CELL_SIZE, y * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")

    def get_flow_between_cells(self, y1, x1, y2, x2):
        """Возвращает коэффициент теплообмена между двумя клетками."""
        cell1_type = self.type_matrix[y1, x1]
        cell2_type = self.type_matrix[y2, x2]
        
        # Базовый коэффициент теплообмена
        flow = self.initial_data[COEFFICIENTS][AIR_FLOW]
        
        # Динамический коэффициент, зависящий от разницы температур
        temp_diff = self.temp_matrix[y2, x2] - self.temp_matrix[y1, x1]
        flow *= math.atan(abs(temp_diff)/10) * 2
        
        # Учитываем тип клеток
        if cell1_type == DOOR or cell2_type == DOOR:
            flow *= 2*self.initial_data[COEFFICIENTS][OPEN_DOOR_FLOW]
        elif cell1_type == WINDOW or cell2_type == WINDOW:
            flow *= 2*self.initial_data[COEFFICIENTS][WINDOW_FLOW]*self.initial_data[COEFFICIENTS][WINDOW_OPENNESS]
        elif cell1_type == WALL or cell2_type == WALL:
            flow *= self.initial_data[COEFFICIENTS][WALL_RESISTANCE]
        
        # Ограничиваем максимальный поток
        return max(min(flow, 5.0), -5.0)

    def calculate_temp_delta(self, y, x, current_temp):
        """Рассчитывает изменение температуры для клетки (y, x)."""
        total_delta = 0
        neighbor_count = 0
        
        neighbors = [(y-1, x), (y+1, x), (y, x-1), (y, x+1)]
        for ny, nx in neighbors:
            if 0 <= ny < GRID_ROWS and 0 <= nx < GRID_COLS:
                # Получаем температуру соседа
                if self.type_matrix[ny, nx] == OUTSIDE:
                    neighbor_temp = self.initial_data[TEMPERATURES][OUTSIDE_TEMP]
                else:
                    neighbor_temp = self.temp_matrix[ny, nx]
                
                # Рассчитываем поток
                flow = self.get_flow_between_cells(y, x, ny, nx)
                delta = (neighbor_temp - current_temp) * flow
                total_delta += delta
                neighbor_count += 1
        
        # Возвращаем среднее изменение
        return total_delta / neighbor_count if neighbor_count > 0 else 0

    def update_temperature(self):
        """Обновляет температуры в сетке с учетом регуляторов."""
        delta_matrix = np.zeros_like(self.temp_matrix, dtype=float)
        
        if self.regulator_enabled:
            # Сбор данных с датчиков
            sensor_temps = [self.temp_matrix[s.y, s.x] for s in self.sensors]
            avg_temp = np.mean(sensor_temps) if sensor_temps else self.initial_data[TEMPERATURES][INITIAL_ROOM_TEMP]
            
            # Обновление регулятора
            self.controller.update(avg_temp, self.time_tick)
            
            # Применение управляющих воздействий
            self.initial_data[TEMPERATURES][AC_TEMP] = self.controller.ac_temp
            self.initial_data[TEMPERATURES][HEATER_TEMP] = self.controller.heater_temp
            self.initial_data[COEFFICIENTS][WINDOW_OPENNESS] = self.controller.window_openness
        
        # Вычисляем изменения температуры
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                if self.type_matrix[y, x] == HEATER and self.controller.heater_on:
                    self.temp_matrix[y, x] = self.initial_data[TEMPERATURES][HEATER_TEMP]
                    continue
                elif self.type_matrix[y, x] == AC and self.controller.ac_on: 
                    self.temp_matrix[y, x] = self.initial_data[TEMPERATURES][AC_TEMP] 
                    continue
                elif self.type_matrix[y, x] == OUTSIDE:
                    self.temp_matrix[y, x] = self.initial_data[TEMPERATURES][OUTSIDE_TEMP]
                    continue
                current_temp = self.temp_matrix[y, x]
                delta = self.calculate_temp_delta(y, x, current_temp)
                delta_matrix[y, x] = delta
        
        # Применяем изменения с ограничениями
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):                
                new_temp = self.temp_matrix[y, x] + delta_matrix[y, x]
                self.temp_matrix[y, x] = max(min(new_temp, 200.0), -100.0)

    def simulation_step(self):
        """Один шаг симуляции."""
        self.update_temperature()
        self.draw_grid()
        self.time_tick+=1
        speed = self.time_speed.get()
        if self.graph_window:
            self.graph_update_job = self.root.after(int(1000 / speed) if speed != 0 else 1, self.update_graphs)
        self.root.after(int(1000 / speed) if speed != 0 else 1, self.simulation_step)

    def clear_cell(self, event):
        """Очищает клетку."""
        x, y = event.x // CELL_SIZE, event.y // CELL_SIZE
        # Удаляем датчик, если он был
        self.sensors = [s for s in self.sensors if not (s.y == y and s.x == x)]
        self.type_matrix[y, x] = EMPTY
        self.draw_grid()

    def curs(self, event):
        """Отображает информацию о клетке."""
        x, y = event.x // CELL_SIZE, event.y // CELL_SIZE

        if 0 <= x < GRID_COLS and 0 <= y < GRID_ROWS:
            temp = self.temp_matrix[y, x]
            cell_type = self.type_matrix[y, x]

            cell_types = {
                EMPTY: "Воздух",
                WALL: "Стена",
                DOOR: "Дверь",
                WINDOW: "Окно",
                HEATER: "Батарея",
                AC: "Кондиционер",
                OUTSIDE: "Улица",
                SENSOR: "Датчик"
            }
            cell_type_name = cell_types.get(cell_type, "Неизвестно")

            info_text = f"Температура: {temp:.2f}°C\nТип: {cell_type_name}"

            if hasattr(self, "info_label"):
                self.info_label.destroy()

            self.info_label = tk.Label(self.canvas, text=info_text, bg="white", fg="black", font=("Arial", 10))
            self.info_label.place(x=event.x + 10, y=event.y + 10)
            self.info_label.after(2000, self.info_label.destroy)

    def add_cell_panel(self, frame):
        """Добавляет панель выбора типа клетки."""
        ttk.Label(frame, text="Выберите тип клетки:").grid(row=21, column=1, padx=10, pady=10, sticky="w")
        cell_types = ["Пустота", "Стена", "Дверь", "Окно", "Батарея", "Кондиционер", "Датчик"]
        values = [EMPTY, WALL, DOOR, WINDOW, HEATER, AC, SENSOR]
        dropdown = ttk.Combobox(frame, values=cell_types, state="readonly")
        dropdown.grid(row=21, column=2, padx=10, pady=10, sticky="w")
        dropdown.current(4)

        def update_type(event):
            self.selected_type.set(values[dropdown.current()])

        dropdown.bind("<<ComboboxSelected>>", update_type)

    def set_cell(self, event):
        """Устанавливает тип клетки."""
        x, y = event.x // CELL_SIZE, event.y // CELL_SIZE
        cell_type = self.selected_type.get()
        
        # Если добавляем датчик
        if cell_type == SENSOR:
            # Проверяем, нет ли уже датчика в этой клетке
            for sensor in self.sensors:
                if sensor.y == y and sensor.x == x:
                    return
                    
            self.sensors.append(Sensor(y, x))
            
        self.type_matrix[y, x] = cell_type
        
        if self.type_matrix[y, x] == HEATER:
            self.temp_matrix[y, x] = self.initial_data[TEMPERATURES][HEATER_TEMP]
        elif self.type_matrix[y, x] == AC:
            self.temp_matrix[y, x] = self.initial_data[TEMPERATURES][AC_TEMP]
        self.draw_grid()

    def create_control_panel(self, parent):
        """Создает упорядоченную панель управления"""
        # Группа температурных параметров
        ttk.Label(parent, text="Температуры", font=('Arial', 10, 'bold')).grid(row=0, column=0, columnspan=3, pady=5)
        self.add_slider(parent, "На улице", TEMPERATURES, OUTSIDE_TEMP, -50, 50, 1)
        self.add_slider(parent, "Батарей", TEMPERATURES, HEATER_TEMP, 20, 90, 2)
        self.add_slider(parent, "Кондиционера", TEMPERATURES, AC_TEMP, 10, 30, 3)
        self.add_slider(parent, "Начальная", TEMPERATURES, INITIAL_ROOM_TEMP, -30, 40, 4)
        self.add_slider(parent, "Целевая", TEMPERATURES, TARGET_TEMP, 10, 30, 5)

        # Группа коэффициентов
        ttk.Label(parent, text="Коэффициенты", font=('Arial', 10, 'bold')).grid(row=6, column=0, columnspan=3, pady=5)
        self.add_slider(parent, "Стен", COEFFICIENTS, WALL_RESISTANCE, 0.001, 0.1, 7)
        self.add_slider(parent, "Воздуха", COEFFICIENTS, AIR_FLOW, 0.1, 1.0, 8)
        self.add_slider(parent, "Дверей", COEFFICIENTS, OPEN_DOOR_FLOW, 0.1, 1.0, 9)
        self.add_slider(parent, "Окон", COEFFICIENTS, WINDOW_FLOW, 0.1, 1.0, 10)
        self.add_slider(parent, "Открытие окон", COEFFICIENTS, WINDOW_OPENNESS, 0.0, 1.0, 11)

        # Группа PID параметров
        ttk.Label(parent, text="PID параметры", font=('Arial', 10, 'bold')).grid(row=12, column=0, columnspan=3, pady=5)
        self.add_slider(parent, "Kp", COEFFICIENTS, KP, 0.1, 5.0, 13)
        self.add_slider(parent, "Ki", COEFFICIENTS, KI, 0.01, 0.5, 14)
        self.add_slider(parent, "Kd", COEFFICIENTS, KD, 0.0, 2.0, 15)

        # Управление системой
        ttk.Label(parent, text="Управление", font=('Arial', 10, 'bold')).grid(row=16, column=0, columnspan=3, pady=5)
        
        # Кнопка включения/выключения регулятора
        self.regulator_btn = ttk.Button(parent, text="Включить регулятор", 
                                      command=self.toggle_regulator)
        self.regulator_btn.grid(row=17, column=0, columnspan=3, pady=5)

        # Выбор типа регулятора
        ttk.Label(parent, text="Тип регулятора:").grid(row=18, column=0, sticky='w')
        controller_types = ["Релейный", "PI", "PID"]
        controller_dropdown = ttk.Combobox(parent, values=controller_types, state="readonly")
        controller_dropdown.current(0)
        controller_dropdown.grid(row=18, column=1, columnspan=2, sticky='ew')
        controller_dropdown.bind("<<ComboboxSelected>>", 
                               lambda e: self.controller.set_controller_type(controller_dropdown.current()))

        # Скорость симуляции
        self.add_slider(parent, "Скорость", None, None, 1, 100, 19, var=self.time_speed)

        # Основные кнопки управления
        ttk.Button(parent, text="Применить", command=self.update_settings).grid(row=20, column=0, columnspan=3, pady=5)
        ttk.Button(parent, text="Сбросить поле", command=self.reset_field).grid(row=21, column=0)
        ttk.Button(parent, text="Графики", command=self.show_sensors_graph).grid(row=22, column=0, pady=10)
        ttk.Button(parent, text="Сохранить", command=self.save_json).grid(row=22, column=1, pady=10)
        ttk.Button(parent, text="Загрузить", command=self.load_json).grid(row=22, column=2, pady=10)
    
    def reset_field(self):
        """Сбрасывает поле к начальному состоянию."""
        self.type_matrix, self.temp_matrix = self.initialize_matrices()
        self.sensors = []
        self.draw_grid()
    def show_sensors_graph(self):
        """Показывает графики датчиков с обновлением в реальном времени"""
        if not self.sensors:
            messagebox.showinfo("Информация", "Нет датчиков для отображения")
            return
        
        # Закрываем старое окно, если оно есть
        if hasattr(self, 'graph_window') and self.graph_window:
            try:
                self.graph_window.destroy()
            except:
                pass
        
        # Создаем новое окно
        self.graph_window = tk.Toplevel(self.root)
        self.graph_window.title("Графики датчиков")
        self.graph_window.protocol("WM_DELETE_WINDOW", self.close_graph_window)
        
        # Создаем Notebook для вкладок
        self.sensor_notebook = ttk.Notebook(self.graph_window)
        self.sensor_notebook.pack(fill='both', expand=True)
        
        # Создаем фреймы и графики для каждого датчика
        self.sensor_frames = []
        self.sensor_figures = []
        self.sensor_axes = []
        self.sensor_lines = []
        self.sensor_canvases = []
        # Создаем фрейм для вкладки
        frame = ttk.Frame(self.sensor_notebook)
        self.sensor_frames.append(frame)
        self.sensor_notebook.add(frame, text=f"Регулятор")
        
        # Создаем фигуру matplotlib
        fig, ax = plt.subplots(figsize=(8, 4))
        line, = ax.plot(self.controller.time_history, self.controller.temp_history, 'r-')
        
        # Настраиваем график
        ax.set_title(f"Температура на вход регулятора ")
        ax.set_xlabel("Время ")
        ax.set_ylabel("Температура (°C)")
        ax.grid(True)
        
        # Создаем холст для встраивания в Tkinter
        canvas = FigureCanvasTkAgg(fig, master=frame)
        canvas.draw()
        canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
        
        # Сохраняем компоненты для обновления
        self.sensor_figures.append(fig)
        self.sensor_axes.append(ax)
        self.sensor_lines.append(line)
        self.sensor_canvases.append(canvas)
        for sensor in self.sensors:
            # Создаем фрейм для вкладки
            frame = ttk.Frame(self.sensor_notebook)
            self.sensor_frames.append(frame)
            self.sensor_notebook.add(frame, text=f"Датчик ({sensor.y}, {sensor.x})")
            
            # Создаем фигуру matplotlib
            fig, ax = plt.subplots(figsize=(8, 4))
            line, = ax.plot(sensor.time_history, sensor.temp_history, 'r-')
            
            # Настраиваем график
            ax.set_title(f"Температура в точке ({sensor.y}, {sensor.x})")
            ax.set_xlabel("Время ")
            ax.set_ylabel("Температура (°C)")
            ax.grid(True)
            
            # Создаем холст для встраивания в Tkinter
            canvas = FigureCanvasTkAgg(fig, master=frame)
            canvas.draw()
            canvas.get_tk_widget().pack(fill=tk.BOTH, expand=True)
            
            # Сохраняем компоненты для обновления
            self.sensor_figures.append(fig)
            self.sensor_axes.append(ax)
            self.sensor_lines.append(line)
            self.sensor_canvases.append(canvas)
        
        
        
        # Запускаем обновление графиков
        self.update_graphs()

    def close_graph_window(self):
        """Корректно закрывает окно графиков"""
        if hasattr(self, 'graph_window') and self.graph_window:
            self.graph_window.destroy()
            self.graph_window = None
            
        # Останавливаем обновление графиков
        if hasattr(self, 'graph_update_job'):
            self.root.after_cancel(self.graph_update_job)
            del self.graph_update_job

    def update_graphs(self):
        """Обновляет только активную вкладку с графиком датчика"""
        if not hasattr(self, 'graph_window') or not self.graph_window or not tk.Toplevel.winfo_exists(self.graph_window):
            return
        
        try:
            # Получаем индекс активной вкладки
            current_tab = self.sensor_notebook.index(self.sensor_notebook.select())
            
                
            # Обновляем только активный график
            if 0 <= current_tab < len(self.sensors):
                if current_tab!=0:
                    sensor = self.sensors[current_tab-1]
                else:
                    sensor = self.controller
                fig, canvas = self.sensor_figures[current_tab], self.sensor_canvases[current_tab]
                ax = fig.axes[0]
                
                # Обновляем данные
                ax.lines[0].set_data(sensor.time_history, sensor.temp_history)
                ax.relim()
                ax.autoscale_view()
                canvas.draw()
        except Exception as e:
            print(f"Ошибка обновления графика: {e}")
            self.close_graphs_window()
            return
        
    def add_slider(self, parent, label, category, param, from_, to, row, var=None):
        """Добавляет слайдер с меткой"""
        ttk.Label(parent, text=label+":").grid(row=row, column=0, padx=5, pady=2, sticky='w')
        
        if not var:
            var = tk.DoubleVar(value=self.initial_data[category][param] if category else 0)
            setattr(self, f"{param}_var", var)
        
        ttk.Scale(parent, from_=from_, to=to, variable=var, 
                 orient='horizontal', length=150).grid(row=row, column=1, padx=5)
        ttk.Entry(parent, textvariable=var, width=6).grid(row=row, column=2, padx=5)
        
    def toggle_regulator(self):
        """Включает/выключает регулятор температуры"""
        self.regulator_enabled = not self.regulator_enabled
        if self.regulator_enabled:
            self.regulator_btn.config(text="Выключить регулятор")
            self.controller.reset(soft=True)
        else:
            self.regulator_btn.config(text="Включить регулятор")
            # Отключаем все устройства при выключении регулятора
            # self.controller.heater_on = False
            # self.controller.ac_on = False
    
    def update_settings(self):
        """Обновляет все параметры системы"""
        # Обновление температур
        for param in [OUTSIDE_TEMP, HEATER_TEMP, AC_TEMP, INITIAL_ROOM_TEMP, TARGET_TEMP]:
            self.initial_data[TEMPERATURES][param] = getattr(self, f"{param}_var").get()
        
        # Обновление коэффициентов
        for param in [WALL_RESISTANCE, AIR_FLOW, OPEN_DOOR_FLOW, WINDOW_FLOW, WINDOW_OPENNESS]:
            self.initial_data[COEFFICIENTS][param] = getattr(self, f"{param}_var").get()
        if self.regulator_enabled:
            # Обновление PID параметров
            for param in [KP, KI, KD]:
                self.initial_data[COEFFICIENTS][param] = getattr(self, f"{param}_var").get()
                setattr(self.controller, f"K{param[-1].lower()}", self.initial_data[COEFFICIENTS][param])
        
            # Применение целевой температуры
            self.controller.set_target_temp(self.initial_data[TEMPERATURES][TARGET_TEMP])
        
        # Обновление температур на карте
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                if self.type_matrix[y, x] == OUTSIDE:
                    self.temp_matrix[y, x] = self.initial_data[TEMPERATURES][OUTSIDE_TEMP]
                elif self.type_matrix[y, x] == HEATER:
                    self.temp_matrix[y, x] = self.initial_data[TEMPERATURES][HEATER_TEMP]
                elif self.type_matrix[y, x] == AC:
                    self.temp_matrix[y, x] = self.initial_data[TEMPERATURES][AC_TEMP]  
    
    def load_json(self, file_path=None):
        """Загружает конфигурацию из JSON файла."""
        if file_path is None:
            file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])

        if file_path:
            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
                    if 'type_matrix' not in data or 'temp_matrix' not in data:
                        raise ValueError("Некорректный формат JSON файла.")

                    self.type_matrix = np.array(data['type_matrix'])
                    self.temp_matrix = np.array(data['temp_matrix'])
                    
                    # Восстанавливаем датчики
                    self.sensors = []
                    for y in range(GRID_ROWS):
                        for x in range(GRID_COLS):
                            if self.type_matrix[y, x] == SENSOR:
                                self.sensors.append(Sensor(y, x))
                    
                    self.draw_grid()
                    messagebox.showinfo("Успех", "Конфигурация загружена из JSON файла.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")

    def save_json(self, file_path=None):
        """Сохраняет конфигурацию в JSON файл."""
        if file_path is None:
            file_path = filedialog.asksaveasfilename(defaultextension=".json", filetypes=[("JSON files", "*.json")])

        if file_path:
            try:
                data = {
                    'type_matrix': self.type_matrix.tolist(),
                    'temp_matrix': self.temp_matrix.tolist()
                }
                with open(file_path, 'w') as file:
                    json.dump(data, file, indent=4)
                messagebox.showinfo("Успех", "Конфигурация сохранена в JSON файл.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

    

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartHomeApp(root)
    root.mainloop()