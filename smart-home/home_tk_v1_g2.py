import tkinter as tk
from tkinter import ttk, filedialog, messagebox
import numpy as np
import json
import xml.etree.ElementTree as ET
from functools import lru_cache

# Константы
WIDTH, HEIGHT = 600, 600  # Размеры окна для симуляции
GRID_ROWS, GRID_COLS = 30, 30  # Размер сетки
CELL_SIZE = WIDTH // GRID_COLS  # Размер ячейки

# Температурные параметры
OUTSIDE_TEMP = -25    # Температура на улице
HEATER_TEMP = 60      # Температура батарей
AC_TEMP = 18          # Температура кондиционера
INITIAL_ROOM_TEMP = -10  # Начальная температура в доме

# Коэффициенты теплообмена
WALL_RESISTANCE = 0.01  # Стены почти не пропускают тепло
AIR_FLOW = 0.2
OPEN_DOOR_FLOW = 0.8
WINDOW_FLOW = 0.7

# Определение типов клеток
EMPTY, WALL, DOOR, WINDOW, HEATER, AC, OUTSIDE = range(7)

def initialize_matrices():
    """Создает и инициализирует основные матрицы."""
    type_matrix = np.full((GRID_ROWS, GRID_COLS), OUTSIDE, dtype=int)  # Весь мир - улица
    temp_matrix = np.full((GRID_ROWS, GRID_COLS), OUTSIDE_TEMP, dtype=float)  # Улица холодная
    # Устанавливаем стены дома (на одну клетку меньше, чем границы системы)
    type_matrix[1:-1, 1:-1] = EMPTY  # Внутри дома пустые клетки
    type_matrix[2:-2, 2:-2] = EMPTY  # Гарантируем, что внутри дома пусто
    
    # Стены дома
    type_matrix[2, 2:-2] = WALL
    type_matrix[-3, 2:-2] = WALL
    type_matrix[2:-2, 2] = WALL
    type_matrix[2:-2, -3] = WALL
    
    # Внутреннюю температуру заполняем начальной температурой дома
    temp_matrix[2:-2, 2:-2] = INITIAL_ROOM_TEMP

    return type_matrix, temp_matrix

@lru_cache(maxsize=8000)
def get_color_for_temp(temp):
    """Возвращает цвет в зависимости от температуры."""
    if temp < 0:
        blue = 255
        green = max(0, min(255, int(255 * (temp + 30) / 30)))
        red = 0
    elif 0 <= temp <= 35:
        blue = max(0, min(255, int(255 * (1 - temp / 35))))
        green = 255
        red = 0
    else:
        blue = 0
        green = max(0, min(255, int(255 * (1 - (temp - 35) / 35))))
        red = 255
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

        self.time_speed = tk.IntVar(value=10)
        # Выпадающее меню выбора типа клетки
        self.selected_type = tk.IntVar(value=HEATER)
        
        # Инициализация матриц
        
        self.load_json("defult.json")
        # Рисуем сетку и обновляем температуру
        self.draw_grid()
        self.root.after(1000, self.simulation_step)

        # Обработчики кликов
        self.canvas.bind("<Button-1>", self.set_cell)
        self.canvas.bind("<Button-3>", self.clear_cell)
        self.canvas.bind("<Button-2>", self.curs)
        # Панель управления
        self.create_control_panel(control_frame)
        self.add_cell_panel(control_frame)

    def create_time_speed_control(self):
        """Создает слайдер для управления скоростью времени."""
        frame = tk.Frame(self.root)
        frame.pack()

        tk.Label(frame, text="Скорость времени (мс)").pack(side="left")
        speed_slider = tk.Scale(frame, from_=10, to=1000, variable=self.time_speed, orient="horizontal")
        speed_slider.pack(side="left")

    def simulation_step(self):
        """Один шаг симуляции."""
        self.update_temperature()
        self.draw_grid()
        s=self.time_speed.get()
        self.root.after(int(1000/s) if s!=0 else 1 , self.simulation_step)
    
    

    def draw_grid(self):
        """Рисует сетку и температурное поле с плавным градиентом."""
        self.canvas.delete("all")

        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                temp = self.temp_matrix[y, x]
                cell_type = self.type_matrix[y, x]

                if cell_type == WALL:
                    color = "gray"
                elif cell_type == DOOR:
                    color = "orange"
                elif cell_type == WINDOW:
                    color = "lightblue"
                else:
                    color = get_color_for_temp(temp)

                x1, y1 = x * CELL_SIZE, y * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
    
    
    def get_flow_between_cells(self, y1, x1, y2, x2):
        """
        Возвращает коэффициент теплообмена между двумя клетками (y1, x1) и (y2, x2).
        Учитывает тип клеток (стены, двери, окна) и базовый коэффициент теплообмена.
        """
        flow = AIR_FLOW  # Базовый коэффициент теплообмена

        # Динамический коэффициент, зависящий от разницы температур
        temp_diff = abs(self.temp_matrix[y2, x2] - self.temp_matrix[y1, x1])
        flow *= (1 + 0.1 * temp_diff)  # Коэффициент k = 0.1

        # Учитываем стены, двери и окна
        if self.type_matrix[y1, x1] == DOOR or self.type_matrix[y2, x2] == DOOR:
            flow *= OPEN_DOOR_FLOW
        elif self.type_matrix[y1, x1] == WINDOW or self.type_matrix[y2, x2] == WINDOW:
            flow *= WINDOW_FLOW
        elif self.type_matrix[y1, x1] == WALL or self.type_matrix[y2, x2] == WALL:
            flow *= WALL_RESISTANCE

        return flow
   
    def calculate_temp_delta(self, y, x, current_temp):
        """
        Рассчитывает изменение температуры для клетки (y, x) на основе температуры соседей.
        """
        total_delta = 0
        neighbor_count = 0

        # Соседи клетки (вверх, вниз, влево, вправо)
        neighbors = [(y-1, x), (y+1, x), (y, x-1), (y, x+1)]
        
        for ny, nx in neighbors:
            if 0 <= ny < GRID_ROWS and 0 <= nx < GRID_COLS:
                # Температура соседа
                neighbor_temp = OUTSIDE_TEMP if self.type_matrix[ny, nx] == OUTSIDE else self.temp_matrix[ny, nx]
                
                # Коэффициент теплообмена между текущей клеткой и соседом
                flow = self.get_flow_between_cells(y, x, ny, nx)
                
                # Изменение температуры
                delta = (neighbor_temp - current_temp) * flow
                total_delta += delta
                neighbor_count += 1

        # Возвращаем среднее изменение температуры
        return total_delta / neighbor_count if neighbor_count > 0 else 0        
    def update_temperature(self):
        """Обновляет температуры в сетке, учитывая теплообмен между ячейками."""
        delta_matrix = np.zeros_like(self.temp_matrix, dtype=float)
        
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                # Если клетка — улица, её температура фиксирована
                if self.type_matrix[y, x] == OUTSIDE:
                    self.temp_matrix[y, x] = OUTSIDE_TEMP
                    continue
                
                # Если клетка — батарея или кондиционер, её температура фиксирована
                if self.type_matrix[y, x] in {HEATER, AC}:
                    continue
                
                # Текущая температура клетки
                current_temp = self.temp_matrix[y, x]
                
                # Рассчитываем изменение температуры
                delta = self.calculate_temp_delta(y, x, current_temp)
                delta_matrix[y, x] = delta

        # Применяем изменения температуры
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                if self.type_matrix[y, x] not in {OUTSIDE, HEATER, AC}:
                    self.temp_matrix[y, x] += delta_matrix[y, x]
    
    def clear_cell(self, event):
        x, y = event.x // CELL_SIZE, event.y // CELL_SIZE
        self.type_matrix[y, x] = EMPTY        
        self.draw_grid()
        
    def curs(self, event):
        """Отображает информацию о температуре и типе клетки рядом с курсором."""
        x, y = event.x // CELL_SIZE, event.y // CELL_SIZE

        # Проверяем, что координаты находятся в пределах сетки
        if 0 <= x < GRID_COLS and 0 <= y < GRID_ROWS:
            # Получаем температуру и тип клетки
            temp = self.temp_matrix[y, x]
            cell_type = self.type_matrix[y, x]

            # Определяем текстовое описание типа клетки
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

            # Создаем текст для отображения
            info_text = f"Температура: {temp:.2f}°C\nТип: {cell_type_name}"

            # Удаляем предыдущий label, если он существует
            if hasattr(self, "info_label"):
                self.info_label.destroy()

            # Создаем новый label с информацией
            self.info_label = tk.Label(self.canvas, text=info_text, bg="white", fg="black", font=("Arial", 10))
            
            # Позиционируем label рядом с курсором
            self.info_label.place(x=event.x + 10, y=event.y + 10)

            # Удаляем label через 2 секунды
            self.info_label.after(2000, self.info_label.destroy)
        
    
    
    

    def add_cell_panel(self,frame):        
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
        x, y = event.x // CELL_SIZE, event.y // CELL_SIZE
        self.type_matrix[y, x] = self.selected_type.get()
        if self.type_matrix[y, x] == HEATER:
            self.temp_matrix[y, x] = HEATER_TEMP
        elif self.type_matrix[y, x] == AC:
            self.temp_matrix[y, x] = AC_TEMP
        self.draw_grid()
        
    def create_control_panel(self, parent):
        """Создает панель управления настройками."""
        global OUTSIDE_TEMP, HEATER_TEMP, AC_TEMP, INITIAL_ROOM_TEMP
        global AIR_FLOW, OPEN_DOOR_FLOW, WINDOW_FLOW

        def update_constants():
            global OUTSIDE_TEMP, HEATER_TEMP, AC_TEMP, INITIAL_ROOM_TEMP
            global AIR_FLOW, OPEN_DOOR_FLOW, WINDOW_FLOW
            
            OUTSIDE_TEMP = outside_temp_var.get()
            HEATER_TEMP = heater_temp_var.get()
            AC_TEMP = ac_temp_var.get()
            INITIAL_ROOM_TEMP = initial_room_temp_var.get()
            
            AIR_FLOW = air_flow_var.get()
            OPEN_DOOR_FLOW = open_door_flow_var.get()
            WINDOW_FLOW = window_flow_var.get()
            
            print("Обновлены константы:", OUTSIDE_TEMP, HEATER_TEMP, AC_TEMP, INITIAL_ROOM_TEMP)
            print("Коэффициенты теплообмена:", AIR_FLOW, OPEN_DOOR_FLOW, WINDOW_FLOW)
            self.type_matrix, self.temp_matrix = initialize_matrices()

        # Переменные для слайдеров
        outside_temp_var = tk.DoubleVar(value=OUTSIDE_TEMP)
        heater_temp_var = tk.DoubleVar(value=HEATER_TEMP)
        ac_temp_var = tk.DoubleVar(value=AC_TEMP)
        initial_room_temp_var = tk.DoubleVar(value=INITIAL_ROOM_TEMP)

        air_flow_var = tk.DoubleVar(value=AIR_FLOW)
        open_door_flow_var = tk.DoubleVar(value=OPEN_DOOR_FLOW)
        window_flow_var = tk.DoubleVar(value=WINDOW_FLOW)

        # Функция для создания слайдера
        def create_slider(label, variable, from_, to, row):
            ttk.Label(parent, text=label).grid(row=row, column=0, padx=10, pady=5, sticky='w')
            slider = ttk.Scale(parent, from_=from_, to=to, variable=variable, orient='horizontal')
            slider.grid(row=row, column=1, padx=10, pady=5, sticky='ew')
            entry = ttk.Entry(parent, textvariable=variable, width=10)
            entry.grid(row=row, column=2, padx=10, pady=5)

        # Добавляем слайдеры
        create_slider("Температура на улице", outside_temp_var, -100, 100, 0)
        create_slider("Температура батарей", heater_temp_var, -20, 80, 1)
        create_slider("Температура кондиционера", ac_temp_var, -10, 50, 2)
        create_slider("Начальная температура в доме", initial_room_temp_var, -130, 130, 3)
        create_slider("Теплообмен (воздух)", air_flow_var, 0.01, 1.0, 4)
        create_slider("Теплообмен (дверь)", open_door_flow_var, 0.01, 1.0, 5)
        create_slider("Скорость времени", self.time_speed, 1, 100, 7)
        

        # Кнопка обновления
        update_button = ttk.Button(parent, text="Применить", command=update_constants)
        update_button.grid(row=8, column=0, columnspan=3, pady=10)

        # Кнопки для загрузки и сохранения конфигурации
        ttk.Button(parent, text="Загрузить JSON", command=self.load_json).grid(row=15, column=0, pady=10)
        ttk.Button(parent, text="Сохранить JSON", command=self.save_json).grid(row=15, column=1, pady=10)
        ttk.Button(parent, text="Загрузить XML", command=self.load_xml).grid(row=16, column=0, pady=10)
        ttk.Button(parent, text="Сохранить XML", command=self.save_xml).grid(row=16, column=1, pady=10)

    def load_json(self,file_path=None):
        """Загружает конфигурацию из JSON файла."""
        is_mess=False
        if file_path is None:
            file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
            is_mess=True
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
                    self.type_matrix = np.array(data['type_matrix'])
                    self.temp_matrix = np.array(data['temp_matrix'])
                self.draw_grid()
                if is_mess:
                    messagebox.showinfo("Успех", "Конфигурация загружена из JSON файла.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось загрузить файл: {e}")

    def save_json(self,file_path=None):
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
                    json.dump(data, file)
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