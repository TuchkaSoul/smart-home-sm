import pygame
import numpy as np
import time

# Константы
WIDTH, HEIGHT = 600, 600  # Размеры окна
GRID_ROWS, GRID_COLS = 30, 30  # Размер сетки
CELL_SIZE = WIDTH // GRID_COLS  # Размер ячейки

# Температурные параметры
OUTSIDE_TEMP = -25    # Температура на улице
HEATER_TEMP = 60    # Температура батарей
AC_TEMP = 18        # Температура кондиционера
INITIAL_ROOM_TEMP = -10  # Начальная температура в доме

# Коэффициенты теплообмена
WALL_RESISTANCE = 0.01  # Стены почти не пропускают тепло
AIR_FLOW = 0.2         # Свободный теплообмен между соседними ячейками
OPEN_DOOR_FLOW = 0.8   # Быстрый теплообмен через открытые двери
WINDOW_FLOW = 0.7      # Теплообмен через окна

# Определение типов клеток
EMPTY, WALL, DOOR, WINDOW, HEATER, AC, OUTSIDE = range(7)

def initialize_matrices():
    """Создает и инициализирует основные матрицы."""
    type_matrix = np.full((GRID_ROWS, GRID_COLS), EMPTY, dtype=int)
    temp_matrix = np.full((GRID_ROWS, GRID_COLS), INITIAL_ROOM_TEMP, dtype=float)
    
    # Устанавливаем стены по краям
    type_matrix[0, :] = WALL
    type_matrix[-1, :] = WALL
    type_matrix[:, 0] = WALL
    type_matrix[:, -1] = WALL
    
    # Внутренние перегородки
    type_matrix[9, :] = WALL  # Вертикальная перегородка слева
    type_matrix[GRID_ROWS-5, :] = WALL  # Вертикальная перегородка справа
    type_matrix[:, 8] = WALL  # Горизонтальная перегородка сверху
    type_matrix[:8, GRID_COLS-7] = WALL  # Горизонтальная перегородка снизу
    
    # Устанавливаем двери
    type_matrix[GRID_ROWS // 2, 8] = DOOR
    type_matrix[GRID_ROWS // 2, GRID_COLS-1] = DOOR
    type_matrix[9, GRID_COLS // 2] = DOOR
    type_matrix[GRID_ROWS - 5, GRID_COLS // 2] = DOOR
    type_matrix[8, GRID_COLS -7] = DOOR
    type_matrix[7, 8] = DOOR
    # Устанавливаем окна
    
    type_matrix[0,5] = WINDOW
    type_matrix[1, 5] = HEATER
    type_matrix[6, 0] = WINDOW
    type_matrix[6, 1] = HEATER
    type_matrix[GRID_ROWS-1,26] = WINDOW
    type_matrix[GRID_ROWS-2,26] = HEATER
    type_matrix[GRID_ROWS-1, 6] = WINDOW
    type_matrix[GRID_ROWS-2,6] = HEATER
    
    # Устанавливаем батареи
    type_matrix[7, 2] = HEATER
    temp_matrix[7, 2] = HEATER_TEMP
    type_matrix[GRID_ROWS-8, GRID_COLS-3] = HEATER
    temp_matrix[GRID_ROWS-8, GRID_COLS-3] = HEATER_TEMP

    # Устанавливаем кондиционеры
    type_matrix[7, GRID_COLS-3] = AC
    temp_matrix[7, GRID_COLS-3] = AC_TEMP
    type_matrix[GRID_ROWS-8, 2] = AC
    temp_matrix[GRID_ROWS-8, 2] = AC_TEMP
    
    return type_matrix, temp_matrix



def update_temperature(self,type_matrix, temp_matrix):
    """Обновляет температуры в сетке, учитывая теплообмен между ячейками."""
    delta_matrix = np.zeros_like(temp_matrix, dtype=float)
    
    for y in range(GRID_ROWS):
        for x in range(GRID_COLS):
            if type_matrix[y, x] in {HEATER, AC}:  # Батареи и кондиционеры имеют фиксированную температуру
                continue
            
            current_temp = temp_matrix[y, x]
            total_delta = 0
            neighbor_count = 0  # Количество соседей, участвующих в теплообмене
            
            neighbors = [(y-1, x), 
                         (y+1, x), 
                         (y, x-1), 
                         (y, x+1)]
            
            for ny, nx in neighbors:
                if 0 <= ny < GRID_ROWS and 0 <= nx < GRID_COLS:
                    neighbor_temp = temp_matrix[ny, nx]
                    flow = AIR_FLOW  
                    if type_matrix[y, x] == DOOR or type_matrix[ny, nx] == DOOR:
                        flow = OPEN_DOOR_FLOW
                    elif type_matrix[y, x] == WINDOW or type_matrix[ny, nx] == WINDOW:
                        flow = WINDOW_FLOW
                        delta = (OUTSIDE_TEMP - current_temp) * flow
                        total_delta += delta
                        neighbor_count += 1.0
                        
                    elif type_matrix[y, x] == WALL or type_matrix[ny, nx] == WALL:
                        flow = WALL_RESISTANCE  
                    delta = (neighbor_temp - current_temp) * flow
                    total_delta += delta
                    neighbor_count += 1.0  # Считаем активных соседей
            
            if neighbor_count > 0:
                total_delta /= neighbor_count  # Нормируем по количеству соседей
            
            if (temp_matrix[y, x]+ total_delta>-257.3):
                delta_matrix[y, x] += total_delta
            else :
                delta_matrix[y, x]=-257.3# Применяем изменение температуры
    
    temp_matrix += delta_matrix  # Обновляем температуры


def print_matrix(matrix):
    I,J=matrix.shape
    for i in range(I):
        for j in range(J):
            print(matrix[i,j],end=" ")
        print("\n")
            
def draw_grid(screen, type_matrix, temp_matrix):
    """Отображает температурное поле на экране."""
    for y in range(GRID_ROWS):
        for x in range(GRID_COLS):
            temp = temp_matrix[y, x]
            if type_matrix[y, x] == WALL:
                color = (100, 100, 100)  # Серый цвет для стен
            elif type_matrix[y, x] == DOOR:
                color = (200, 150, 50)  # Оранжевый цвет для двери
            elif type_matrix[y, x] == WINDOW:
                color = (150, 200, 255)  # Голубой цвет для окна
            else:
                color = (255, min(255,max(0, 255 - int((temp - 5) * 10))), min(255,max(0, 255 - int((temp - 5) * 10))))
            pygame.draw.rect(screen, color, (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE))
            pygame.draw.rect(screen, (0, 0, 0), (x * CELL_SIZE, y * CELL_SIZE, CELL_SIZE, CELL_SIZE), 1)

def main():
    pygame.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Модель умного дома")
    
    type_matrix, temp_matrix = initialize_matrices()
    clock = pygame.time.Clock()
    running = True
    def pos_cell(event,value):
        pos=event.pos
        x,y=int(pos[0]//CELL_SIZE),int(pos[1]//CELL_SIZE)
        type_matrix[y,x]=value
        
        
    while running:
        screen.fill((255, 255, 255))
        
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            if event.type == pygame.MOUSEBUTTONDOWN:
                if event.button == 1:
                    pos_cell(event,WALL)
                elif event.button == 3:
                    pos_cell(event,DOOR)
        i=0
        while i<=1:
            update_temperature(type_matrix, temp_matrix)
            
            i+=1
        
        draw_grid(screen, type_matrix, temp_matrix)
        pygame.display.flip()
        clock.tick(140)
    
    pygame.quit()

if __name__ == "__main__":
    main()

