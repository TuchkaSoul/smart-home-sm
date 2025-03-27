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

# Определение типов клеток
EMPTY, WALL, DOOR, WINDOW, HEATER, AC, OUTSIDE, RELAY = range(8)

class PIDController:
    def __init__(self, Kp=1.0, Ki=0.1, Kd=0.01, setpoint=20):
        self.Kp = Kp
        self.Ki = Ki
        self.Kd = Kd
        self.setpoint = setpoint
        self.last_error = 0
        self.integral = 0
    
    def update(self, current_value, dt=1):
        error = self.setpoint - current_value
        self.integral += error * dt
        derivative = (error - self.last_error) / dt
        output = self.Kp * error + self.Ki * self.integral + self.Kd * derivative
        self.last_error = error
        return output

class PController:
    def __init__(self, Kp=1.0, setpoint=20):
        self.Kp = Kp
        self.setpoint = setpoint
    
    def update(self, current_value):
        error = self.setpoint - current_value
        return self.Kp * error

@lru_cache(maxsize=8000)
def get_color_for_temp(temp):
    """Возвращает цвет в формате HEX в зависимости от температуры."""
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
        
        # Инициализация регуляторов
        self.pid_controller = PIDController()
        self.p_controller = PController()
        self.active_controller = None
        self.control_target = None
        
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
        
        self.initial_data = {
            "temperatures": {
                "OUTSIDE_TEMP": -25,
                "HEATER_TEMP": 60,
                "AC_TEMP": 18,
                "INITIAL_ROOM_TEMP": -10,
                "TARGET_TEMP": 22
            },
            "coefficients": {
                "WALL_RESISTANCE": 0.005,
                "AIR_FLOW": 0.2,
                "OPEN_DOOR_FLOW": 0.8,
                "WINDOW_FLOW": 0.6,
            },
            "pid": {
                "Kp": 1.0,
                "Ki": 0.1,
                "Kd": 0.01
            },
            "p": {
                "Kp": 1.0
            }
        }

        self.time_speed = tk.IntVar(value=10)
        self.selected_type = tk.IntVar(value=HEATER)
        
        # Инициализация матриц
        self.type_matrix, self.temp_matrix = self.initialize_matrices()
        self.load_json("default.json")
        
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
        self.create_regulator_panel(control_frame)

    def initialize_matrices(self):
        """Создает и инициализирует основные матрицы."""
        type_matrix = np.full((GRID_ROWS, GRID_COLS), OUTSIDE, dtype=int)
        temp_matrix = np.full((GRID_ROWS, GRID_COLS), self.initial_data["temperatures"]["OUTSIDE_TEMP"], dtype=float)
        
        # Создаем дом
        type_matrix[1:-1, 1:-1] = EMPTY
        type_matrix[2:-2, 2:-2] = EMPTY
        
        # Стены дома
        type_matrix[2, 2:-2] = WALL
        type_matrix[-3, 2:-2] = WALL
        type_matrix[2:-2, 2] = WALL
        type_matrix[2:-2, -3] = WALL
        
        # Внутренняя температура
        temp_matrix[2:-2, 2:-2] = self.initial_data["temperatures"]["INITIAL_ROOM_TEMP"]

        return type_matrix, temp_matrix

    def draw_grid(self):
        """Рисует сетку и температурное поле."""
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
                elif cell_type == RELAY:
                    color = "purple"
                else:
                    color = get_color_for_temp(temp)

                x1, y1 = x * CELL_SIZE, y * CELL_SIZE
                x2, y2 = x1 + CELL_SIZE, y1 + CELL_SIZE

                self.canvas.create_rectangle(x1, y1, x2, y2, fill=color, outline="black")
                
                # Подписи для реле и регуляторов
                if cell_type == RELAY:
                    self.canvas.create_text((x1 + x2) // 2, (y1 + y2) // 2, 
                                          text="R", fill="white", font=("Arial", 10))

    def get_flow_between_cells(self, y1, x1, y2, x2):
        """Возвращает коэффициент теплообмена между двумя клетками."""
        flow = self.initial_data["coefficients"]["AIR_FLOW"]
        temp_diff = abs(self.temp_matrix[y2, x2] - self.temp_matrix[y1, x1])
        flow *= (1 + 0.1 * temp_diff)

        # Учитываем тип клеток
        cell_types = [self.type_matrix[y1, x1], self.type_matrix[y2, x2]]
        
        if DOOR in cell_types:
            flow *= self.initial_data["coefficients"]["OPEN_DOOR_FLOW"]
        elif WINDOW in cell_types:
            flow *= self.initial_data["coefficients"]["WINDOW_FLOW"]
        elif WALL in cell_types:
            flow *= self.initial_data["coefficients"]["WALL_RESISTANCE"]

        return flow
   
    def calculate_temp_delta(self, y, x, current_temp):
        """Рассчитывает изменение температуры для клетки (y, x)."""
        total_delta = 0
        neighbor_count = 0

        # Соседи клетки (вверх, вниз, влево, вправо)
        directions = [(-1, 0), (1, 0), (0, -1), (0, 1)]

        for dy, dx in directions:
            ny, nx = y + dy, x + dx
            
            # Проверяем границы
            if 0 <= ny < GRID_ROWS and 0 <= nx < GRID_COLS:
                neighbor_type = self.type_matrix[ny, nx]
                
                # Если сосед - стена, пропускаем
                if neighbor_type == WALL:
                    continue
                
                # Если текущая клетка - реле, учитываем только выходное направление
                if self.type_matrix[y, x] == RELAY and (dy, dx) != (0, 1):
                    continue
                
                flow = self.get_flow_between_cells(y, x, ny, nx)
                delta = (self.temp_matrix[ny, nx] - current_temp) * flow
                total_delta += delta
                neighbor_count += 1

        return total_delta / neighbor_count if neighbor_count > 0 else 0
            
    def update_temperature(self):
        """Обновляет температуры в сетке."""
        delta_matrix = np.zeros_like(self.temp_matrix, dtype=float)

        # Применяем регуляторы если они активны
        if self.active_controller and self.control_target:
            y, x = self.control_target
            current_temp = self.temp_matrix[y, x]
            
            if self.active_controller == "PID":
                control_value = self.pid_controller.update(current_temp)
            else:
                control_value = self.p_controller.update(current_temp)
            
            # Применяем управляющее воздействие к ближайшему нагревателю/охладителю
            for dy, dx in [(0, 1), (1, 0), (0, -1), (-1, 0)]:
                ny, nx = y + dy, x + dx
                if 0 <= ny < GRID_ROWS and 0 <= nx < GRID_COLS:
                    if self.type_matrix[ny, nx] in [HEATER, AC]:
                        self.temp_matrix[ny, nx] += control_value * 0.1
                        break

        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                cell_type = self.type_matrix[y, x]
                
                # Фиксированные температуры для специальных клеток
                if cell_type == OUTSIDE:
                    self.temp_matrix[y, x] = self.initial_data["temperatures"]["OUTSIDE_TEMP"]
                elif cell_type == HEATER:
                    self.temp_matrix[y, x] = self.initial_data["temperatures"]["HEATER_TEMP"]
                elif cell_type == AC:
                    self.temp_matrix[y, x] = self.initial_data["temperatures"]["AC_TEMP"]
                elif cell_type not in [WALL, RELAY]:  # Для воздуха, окон, дверей
                    delta = self.calculate_temp_delta(y, x, self.temp_matrix[y, x])
                    delta_matrix[y, x] = delta

        # Применяем изменения температуры
        self.temp_matrix += delta_matrix
    
    def simulation_step(self):
        """Один шаг симуляции."""
        self.update_temperature()
        self.draw_grid()
        speed = self.time_speed.get()
        self.root.after(int(1000/speed) if speed !=0 else 1, self.simulation_step)
        
    def clear_cell(self, event):
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
                OUTSIDE: "Улица",
                RELAY: "Реле"
            }
            cell_type_name = cell_types.get(cell_type, "Неизвестно")

            info_text = f"Температура: {temp:.2f}°C\nТип: {cell_type_name}"

            if hasattr(self, "info_label"):
                self.info_label.destroy()

            self.info_label = tk.Label(self.canvas, text=info_text, bg="white", fg="black", font=("Arial", 10))
            self.info_label.place(x=event.x + 10, y=event.y + 10)
            self.info_label.after(2000, self.info_label.destroy)
    
    def add_cell_panel(self, frame):        
        ttk.Label(frame, text="Выберите тип клетки:").grid(row=9, column=0, padx=10, pady=10, sticky="w")
        cell_types = ["Пустота", "Стена", "Дверь", "Окно", "Батарея", "Кондиционер", "Реле"]
        values = [EMPTY, WALL, DOOR, WINDOW, HEATER, AC, RELAY]
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
            self.temp_matrix[y, x] = self.initial_data["temperatures"]["HEATER_TEMP"]
        elif self.type_matrix[y, x] == AC:
            self.temp_matrix[y, x] = self.initial_data["temperatures"]["AC_TEMP"]
        elif self.type_matrix[y, x] == RELAY:
            self.temp_matrix[y, x] = self.initial_data["temperatures"]["INITIAL_ROOM_TEMP"]
        
        self.draw_grid()
        
    def create_control_panel(self, parent):
        """Создает панель управления настройками."""
        def update_constants():
            self.initial_data["temperatures"]["OUTSIDE_TEMP"] = outside_temp_var.get()
            self.initial_data["temperatures"]["HEATER_TEMP"] = heater_temp_var.get()
            self.initial_data["temperatures"]["AC_TEMP"] = ac_temp_var.get()
            self.initial_data["temperatures"]["INITIAL_ROOM_TEMP"] = initial_room_temp_var.get()
            self.initial_data["temperatures"]["TARGET_TEMP"] = target_temp_var.get()
            
            self.initial_data["coefficients"]["AIR_FLOW"] = air_flow_var.get()
            self.initial_data["coefficients"]["OPEN_DOOR_FLOW"] = open_door_flow_var.get()
            self.initial_data["coefficients"]["WINDOW_FLOW"] = window_flow_var.get()
            
            # Обновляем фиксированные температуры
            type_map = {
                OUTSIDE: self.initial_data["temperatures"]["OUTSIDE_TEMP"],
                HEATER: self.initial_data["temperatures"]["HEATER_TEMP"],
                AC: self.initial_data["temperatures"]["AC_TEMP"]
            }
            
            for y in range(GRID_ROWS):
                for x in range(GRID_COLS):
                    if self.type_matrix[y, x] in type_map:
                        self.temp_matrix[y, x] = type_map[self.type_matrix[y, x]]

        # Переменные для слайдеров
        outside_temp_var = tk.DoubleVar(value=self.initial_data["temperatures"]["OUTSIDE_TEMP"])
        heater_temp_var = tk.DoubleVar(value=self.initial_data["temperatures"]["HEATER_TEMP"])
        ac_temp_var = tk.DoubleVar(value=self.initial_data["temperatures"]["AC_TEMP"])
        initial_room_temp_var = tk.DoubleVar(value=self.initial_data["temperatures"]["INITIAL_ROOM_TEMP"])
        target_temp_var = tk.DoubleVar(value=self.initial_data["temperatures"]["TARGET_TEMP"])

        air_flow_var = tk.DoubleVar(value=self.initial_data["coefficients"]["AIR_FLOW"])
        open_door_flow_var = tk.DoubleVar(value=self.initial_data["coefficients"]["OPEN_DOOR_FLOW"])
        window_flow_var = tk.DoubleVar(value=self.initial_data["coefficients"]["WINDOW_FLOW"])

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
        create_slider("Целевая температура", target_temp_var, -50, 50, 4)
        create_slider("Теплообмен (воздух)", air_flow_var, 0.01, 1.0, 5)
        create_slider("Теплообмен (дверь)", open_door_flow_var, 0.01, 1.0, 6)
        create_slider("Скорость времени", self.time_speed, 1, 100, 7)
        
        def clean_field():
            self.type_matrix, self.temp_matrix = self.initialize_matrices()
            self.draw_grid()
        
        # Кнопка обновления
        update_button = ttk.Button(parent, text="Применить", command=update_constants)
        update_button.grid(row=8, column=0, columnspan=3, pady=10)
        clean_button = ttk.Button(parent, text="Очистить поле", command=clean_field)
        clean_button.grid(row=8, column=1, columnspan=3, pady=10)
        
        # Кнопки для загрузки и сохранения конфигурации
        ttk.Button(parent, text="Загрузить JSON", command=lambda: self.load_json()).grid(row=15, column=0, pady=10)
        ttk.Button(parent, text="Сохранить JSON", command=lambda: self.save_json()).grid(row=15, column=1, pady=10)
        ttk.Button(parent, text="Загрузить XML", command=self.load_xml).grid(row=16, column=0, pady=10)
        ttk.Button(parent, text="Сохранить XML", command=self.save_xml).grid(row=16, column=1, pady=10)

    def create_regulator_panel(self, parent):
        """Создает панель управления регуляторами."""
        reg_frame = ttk.LabelFrame(parent, text="Управление регуляторами", padding=10)
        reg_frame.grid(row=17, column=0, columnspan=2, pady=10, sticky="ew")
        
        # Переменные для параметров регуляторов
        pid_kp_var = tk.DoubleVar(value=self.initial_data["pid"]["Kp"])
        pid_ki_var = tk.DoubleVar(value=self.initial_data["pid"]["Ki"])
        pid_kd_var = tk.DoubleVar(value=self.initial_data["pid"]["Kd"])
        p_kp_var = tk.DoubleVar(value=self.initial_data["p"]["Kp"])
        
        # Параметры PID регулятора
        ttk.Label(reg_frame, text="PID Kp:").grid(row=0, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(reg_frame, textvariable=pid_kp_var, width=8).grid(row=0, column=1, padx=5, pady=2)
        
        ttk.Label(reg_frame, text="PID Ki:").grid(row=1, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(reg_frame, textvariable=pid_ki_var, width=8).grid(row=1, column=1, padx=5, pady=2)
        
        ttk.Label(reg_frame, text="PID Kd:").grid(row=2, column=0, padx=5, pady=2, sticky="e")
        ttk.Entry(reg_frame, textvariable=pid_kd_var, width=8).grid(row=2, column=1, padx=5, pady=2)
        
        # Параметры P регулятора
        ttk.Label(reg_frame, text="P Kp:").grid(row=0, column=2, padx=5, pady=2, sticky="e")
        ttk.Entry(reg_frame, textvariable=p_kp_var, width=8).grid(row=0, column=3, padx=5, pady=2)
        
        # Кнопки управления
        def set_pid():
            self.pid_controller = PIDController(
                Kp=pid_kp_var.get(),
                Ki=pid_ki_var.get(),
                Kd=pid_kd_var.get(),
                setpoint=self.initial_data["temperatures"]["TARGET_TEMP"]
            )
            self.active_controller = "PID"
            self.control_target = self.find_relay()
            messagebox.showinfo("Регулятор", "Активирован PID регулятор")
        
        def set_p():
            self.p_controller = PController(
                Kp=p_kp_var.get(),
                setpoint=self.initial_data["temperatures"]["TARGET_TEMP"]
            )
            self.active_controller = "P"
            self.control_target = self.find_relay()
            messagebox.showinfo("Регулятор", "Активирован P регулятор")
        
        def disable_controller():
            self.active_controller = None
            self.control_target = None
            messagebox.showinfo("Регулятор", "Регулятор отключен")
        
        ttk.Button(reg_frame, text="PID", command=set_pid).grid(row=3, column=0, columnspan=2, pady=5)
        ttk.Button(reg_frame, text="P", command=set_p).grid(row=3, column=2, columnspan=2, pady=5)
        ttk.Button(reg_frame, text="Отключить", command=disable_controller).grid(row=4, column=0, columnspan=4, pady=5)
    
    def find_relay(self):
        """Находит координаты реле в матрице."""
        for y in range(GRID_ROWS):
            for x in range(GRID_COLS):
                if self.type_matrix[y, x] == RELAY:
                    return (y, x)
        return None

    def load_json(self, file_path=None):
        """Загружает конфигурацию из JSON файла."""
        is_mess = False
        if file_path is None:
            file_path = filedialog.askopenfilename(filetypes=[("JSON files", "*.json")])
            is_mess = True
        
        if file_path:
            try:
                with open(file_path, 'r') as file:
                    data = json.load(file)
                    self.type_matrix = np.array(data['type_matrix'])
                    self.temp_matrix = np.array(data['temp_matrix'])
                    if 'initial_data' in data:
                        self.initial_data = data['initial_data']
                self.draw_grid()
                if is_mess:
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
                    'temp_matrix': self.temp_matrix.tolist(),
                    'initial_data': self.initial_data
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
                
                # Загрузка initial_data если есть
                initial_data = root.find('initial_data')
                if initial_data is not None:
                    for section in initial_data:
                        self.initial_data[section.tag] = {item.tag: float(item.text) for item in section}
                
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
                
                # Сохраняем матрицы
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
                
                # Сохраняем initial_data
                initial_data_elem = ET.SubElement(root, 'initial_data')
                for section, values in self.initial_data.items():
                    section_elem = ET.SubElement(initial_data_elem, section)
                    for key, value in values.items():
                        item_elem = ET.SubElement(section_elem, key)
                        item_elem.text = str(value)
                
                tree = ET.ElementTree(root)
                tree.write(file_path)
                messagebox.showinfo("Успех", "Конфигурация сохранена в XML файл.")
            except Exception as e:
                messagebox.showerror("Ошибка", f"Не удалось сохранить файл: {e}")

if __name__ == "__main__":
    root = tk.Tk()
    app = SmartHomeApp(root)
    root.mainloop()