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


@lru_cache(maxsize=1000)
def get_color_for_temp(temp):
    """
    Возвращает цвет в формате HEX в зависимости от температуры.
    Кэширует результаты для ускорения работы.
    """
    if temp < -30:
        return "#0000FF"
    elif -30 <= temp < 0:
        ratio = (temp + 30) / 30
        blue = 255
        green = int(255 * ratio)
        red = 0
    elif 0 <= temp <= 35:
        ratio = temp / 35
        blue = int(255 * (1 - ratio))
        green = 255
        red = 0
    elif 35 < temp <= 70:
        ratio = (temp - 35) / 35
        blue = 0
        green = int(255 * (1 - ratio))
        red = 255
    else:
        return "#FF0000"

    red = max(0, min(255, red))
    green = max(0, min(255, green))
    blue = max(0, min(255, blue))
    return f"#{red:02x}{green:02x}{blue:02x}"


class SmartHomeApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Умный дом — Симуляция и Управление")

        # Основной фрейм
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

        # Инициализация начальных данных
        self.initial_data = {
            TEMPERATURES: {
                OUTSIDE_TEMP: -25,
                HEATER_TEMP: 60,
                AC_TEMP: 18,
                INITIAL_ROOM_TEMP: -10,
            },
            COEFFICIENTS: {
                WALL_RESISTANCE: 0.005,
                AIR_FLOW: 0.2,
                OPEN_DOOR_FLOW: 0.8,
                WINDOW_FLOW: 0.6,
            }
        }

        self.time_speed = tk.IntVar(value=10)
        self.selected_type = tk.IntVar(value=HEATER)

        # Инициализация матриц
        self.load_json("defult.json")
        # self.type_matrix, self.temp_matrix = self.initialize_matrices()

        # Рисуем сетку и запускаем симуляцию
        self.draw_grid()
        self.root.after(1000, self.simulation_step)

        # Обработчики кликов
        self.canvas.bind("<Button-1>", self.set_cell)
        self.canvas.bind("<Button-3>", self.clear_cell)
        self.canvas.bind("<Button-2>", self.curs)

        # Панель управления
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
                    color = "lightblue"
                elif cell_type in {HEATER, AC}:
                    color = "red" if cell_type == HEATER else "blue"
                else:
                    temp = self.temp_matrix[y, x]
                    color = get_color_for_temp(temp)

                x1, y1 = x * CELL_SIZE, y * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")

    def get_flow_between_cells(self, y1, x1, y2, x2):
        """
        Улучшенная версия с защитой от переполнений и плавным теплообменом.
        Возвращает коэффициент теплообмена между двумя клетками.
        """
        # Защита от выхода за границы массива
        if not (0 <= y1 < GRID_ROWS and 0 <= x1 < GRID_COLS and 
                0 <= y2 < GRID_ROWS and 0 <= x2 < GRID_COLS):
            return 0

        # Базовый коэффициент теплообмена
        flow = self.initial_data[COEFFICIENTS][AIR_FLOW]

        # Безопасный расчет разницы температур
        temp_diff = self.temp_matrix[y2, x2] - self.temp_matrix[y1, x1]
        
        # Плавная зависимость от разницы температур (используем atan для насыщения)
        flow *= math.atan(abs(temp_diff)/10) * 2  # Ограничиваем влияние больших перепадов

        # Учитываем тип клеток с защитой от деления на ноль
        if self.type_matrix[y1, x1] == DOOR or self.type_matrix[y2, x2] == DOOR:
            flow = 2*self.initial_data[COEFFICIENTS][OPEN_DOOR_FLOW]
        elif self.type_matrix[y1, x1] == WINDOW or self.type_matrix[y2, x2] == WINDOW:
            flow = 2*self.initial_data[COEFFICIENTS][WINDOW_FLOW]
        elif self.type_matrix[y1, x1] == WALL or self.type_matrix[y2, x2] == WALL:
            flow *= max(self.initial_data[COEFFICIENTS][WALL_RESISTANCE], 0.001)  # Защита от нуля

        # Жесткое ограничение потока
        return max(min(flow, 5.0), -5.0)

    def calculate_temp_delta(self, y, x, current_temp):
        """
        Улучшенный расчет изменения температуры с защитой от аномалий.
        """
        total_delta = 0
        valid_neighbors = 0

        neighbors = [(y-1, x), (y+1, x), (y, x-1), (y, x+1)]
        
        for ny, nx in neighbors:
            if 0 <= ny < GRID_ROWS and 0 <= nx < GRID_COLS:
                # Безопасное получение температуры соседа
                if self.type_matrix[ny, nx] == OUTSIDE:
                    neighbor_temp = self.initial_data[TEMPERATURES][OUTSIDE_TEMP]
                else:
                    neighbor_temp = self.temp_matrix[ny, nx]

                # Безопасный расчет потока
                flow = self.get_flow_between_cells(y, x, ny, nx)
                
                # Накопление изменений
                delta = (neighbor_temp - current_temp) * flow
                total_delta += delta
                valid_neighbors += 1

        # Защита от деления на ноль
        if valid_neighbors == 0:
            return 0
            
        # Возвращаем среднее изменение
        avg_delta = total_delta / valid_neighbors
        
        # Дополнительное ограничение скорости изменения
        return max(min(avg_delta, 2.0), -2.0)

    def update_temperature(self):
        """Обновление температур с защитой от переполнений."""
        delta_matrix = np.zeros_like(self.temp_matrix, dtype=float)
        
        # Сначала вычисляем все изменения
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                if self.type_matrix[y, x] == OUTSIDE:
                    self.temp_matrix[y, x] = self.initial_data[TEMPERATURES][OUTSIDE_TEMP]
                    continue
                
                if self.type_matrix[y, x] in {HEATER, AC}:
                    continue
                    
                current_temp = self.temp_matrix[y, x]
                delta = self.calculate_temp_delta(y, x, current_temp)
                delta_matrix[y, x] = delta

        # Затем применяем изменения с ограничениями
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                if self.type_matrix[y, x] not in {OUTSIDE, HEATER, AC}:
                    new_temp = self.temp_matrix[y, x] + delta_matrix[y, x]
                    # Жесткое ограничение температуры
                    self.temp_matrix[y, x] = max(min(new_temp, 200.0), -100.0)    
        

    def simulation_step(self):
        """Один шаг симуляции."""
        self.update_temperature()
        self.draw_grid()
        speed = self.time_speed.get()
        self.root.after(int(1000 / speed) if speed != 0 else 1, self.simulation_step)

    def clear_cell(self, event):
        """Очищает клетку."""
        x, y = event.x // CELL_SIZE, event.y // CELL_SIZE
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
                OUTSIDE: "Улица"
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
        ttk.Label(frame, text="Выберите тип клетки:").grid(row=9, column=0, padx=10, pady=10, sticky="w")
        cell_types = ["Пустота", "Стена", "Дверь", "Окно", "Батарея", "Кондиционер"]
        values = [EMPTY, WALL, DOOR, WINDOW, HEATER, AC]
        dropdown = ttk.Combobox(frame, values=cell_types, state="readonly")
        dropdown.grid(row=9, column=0, padx=10, pady=10, sticky="w")
        dropdown.current(4)

        def update_type(event):
            self.selected_type.set(values[dropdown.current()])

        dropdown.bind("<<ComboboxSelected>>", update_type)

    def set_cell(self, event):
        """Устанавливает тип клетки."""
        x, y = event.x // CELL_SIZE, event.y // CELL_SIZE
        self.type_matrix[y, x] = self.selected_type.get()
        if self.type_matrix[y, x] == HEATER:
            self.temp_matrix[y, x] = self.initial_data[TEMPERATURES][HEATER_TEMP]
        elif self.type_matrix[y, x] == AC:
            self.temp_matrix[y, x] = self.initial_data[TEMPERATURES][AC_TEMP]
        self.draw_grid()

    def create_control_panel(self, parent):
        """Создает панель управления."""
        outside_temp_var = tk.DoubleVar(value=self.initial_data[TEMPERATURES][OUTSIDE_TEMP])
        heater_temp_var = tk.DoubleVar(value=self.initial_data[TEMPERATURES][HEATER_TEMP])
        ac_temp_var = tk.DoubleVar(value=self.initial_data[TEMPERATURES][AC_TEMP])
        initial_room_temp_var = tk.DoubleVar(value=self.initial_data[TEMPERATURES][INITIAL_ROOM_TEMP])

        air_flow_var = tk.DoubleVar(value=self.initial_data[COEFFICIENTS][AIR_FLOW])
        open_door_flow_var = tk.DoubleVar(value=self.initial_data[COEFFICIENTS][OPEN_DOOR_FLOW])
        window_flow_var = tk.DoubleVar(value=self.initial_data[COEFFICIENTS][WINDOW_FLOW])

        def create_slider(label, variable, from_, to, row):
            ttk.Label(parent, text=label).grid(row=row, column=0, padx=10, pady=5, sticky='w')
            slider = ttk.Scale(parent, from_=from_, to=to, variable=variable, orient='horizontal')
            slider.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
            entry = ttk.Entry(parent, textvariable=variable, width=10)
            entry.grid(row=row, column=2, padx=10, pady=5)

        create_slider("Температура на улице", outside_temp_var, -100, 100, 0)
        create_slider("Температура батарей", heater_temp_var, -20, 80, 1)
        create_slider("Температура кондиционера", ac_temp_var, -10, 50, 2)
        create_slider("Начальная температура в доме", initial_room_temp_var, -130, 130, 3)
        create_slider("Теплообмен (воздух)", air_flow_var, 0.01, 1.0, 4)
        create_slider("Теплообмен (дверь)", open_door_flow_var, 0.01, 1.0, 5)
        create_slider("Скорость времени", self.time_speed, 1, 100, 7)

        def update_constants():
            self.initial_data[TEMPERATURES][OUTSIDE_TEMP] = outside_temp_var.get()
            self.initial_data[TEMPERATURES][HEATER_TEMP] = heater_temp_var.get()
            self.initial_data[TEMPERATURES][AC_TEMP] = ac_temp_var.get()
            self.initial_data[TEMPERATURES][INITIAL_ROOM_TEMP] = initial_room_temp_var.get()

            self.initial_data[COEFFICIENTS][AIR_FLOW] = air_flow_var.get()
            self.initial_data[COEFFICIENTS][OPEN_DOOR_FLOW] = open_door_flow_var.get()
            self.initial_data[COEFFICIENTS][WINDOW_FLOW] = window_flow_var.get()

            # Обновляем температуры для HEATER, AC и OUTSIDE
            buf = (
                self.initial_data[TEMPERATURES][OUTSIDE_TEMP],
                self.initial_data[TEMPERATURES][HEATER_TEMP],
                self.initial_data[TEMPERATURES][AC_TEMP]
            )
            type_buf = (OUTSIDE, HEATER, AC)

            for y in range(GRID_ROWS):
                for x in range(GRID_COLS):
                    if self.type_matrix[y, x] in type_buf:
                        self.temp_matrix[y, x] = buf[type_buf.index(self.type_matrix[y, x])]

        def reset_field():
            """Сбрасывает поле к начальному состоянию."""
            self.type_matrix, self.temp_matrix = self.initialize_matrices()
            self.draw_grid()

        update_button = ttk.Button(parent, text="Применить", command=update_constants)
        update_button.grid(row=8, column=0, columnspan=3, pady=10)
        reset_button = ttk.Button(parent, text="Очистить поле", command=reset_field)
        reset_button.grid(row=8, column=1, columnspan=3, pady=10)

        ttk.Button(parent, text="Загрузить JSON", command=self.load_json).grid(row=15, column=0, pady=10)
        ttk.Button(parent, text="Сохранить JSON", command=self.save_json).grid(row=15, column=1, pady=10)
        ttk.Button(parent, text="Загрузить XML", command=self.load_xml).grid(row=16, column=0, pady=10)
        ttk.Button(parent, text="Сохранить XML", command=self.save_xml).grid(row=16, column=1, pady=10)

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

    def load_xml(self):
        """Загружает конфигурацию из XML файла."""
        file_path = filedialog.askopenfilename(filetypes=[("XML files", "*.xml")])
        if file_path:
            try:
                tree = ET.parse(file_path)
                root = tree.getroot()
                type_matrix = []
                temp_matrix = []
                for row in root.find('type_matrix'):
                    type_matrix.append([int(cell.text) for cell in row])
                for row in root.find('temp_matrix'):
                    temp_matrix.append([float(cell.text) for cell in row])
                self.type_matrix = np.array(type_matrix)
                self.temp_matrix = np.array(temp_matrix)
                self.draw_grid()
                messagebox.showinfo("Успех", "Конфигурация загружена из XML файла.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")

    def save_xml(self):
        """Сохраняет конфигурацию в XML файл."""
        file_path = filedialog.asksaveasfilename(defaultextension=".xml", filetypes=[("XML files", "*.xml")])
        if file_path:
            try:
                root = ET.Element('config')
                type_matrix_elem = ET.SubElement(root, 'type_matrix')
                for row in self.type_matrix:
                    row_elem = ET.SubElement(type_matrix_elem, 'row')
                    for cell in row:
                        cell_elem = ET.SubElement(row_elem, 'cell')
                        cell_elem.text = str(cell)
                temp_matrix_elem = ET.SubElement(root, 'temp_matrix')
                for row in self.temp_matrix:
                    row_elem = ET.SubElement(temp_matrix_elem, 'row')
                    for cell in row:
                        cell_elem = ET.SubElement(row_elem, 'cell')
                        cell_elem.text = str(cell)
                tree = ET.ElementTree(root)
                tree.write(file_path)
                messagebox.showinfo("Успех", "Конфигурация сохранена в XML файл.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")


if __name__ == "__main__":
    root = tk.Tk()
    app = SmartHomeApp(root)
    root.mainloop()