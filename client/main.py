import pygame
pygame.init()

screen = pygame.display.set_mode((800,600)) # размер окна
pygame.display.set_caption("Brickfall") # название окна


running = True
clock = pygame.time.Clock() #ограничиваем фпс

paddle = pygame.Rect(350, 550, 100, 15) #создаем платформу x y ширина высота

while running:

    for event in pygame.event.get(): # получение событий
        if event.type == pygame.QUIT: # проверка события выхода
            running = False 
    
    keys = pygame.key.get_pressed() # узнает какие клавиши сейчас удерживаются
    if keys[pygame.K_LEFT]:
        paddle.x = paddle.x - 5
    
    if keys[pygame.K_RIGHT]:
        paddle.x = paddle.x + 5


    screen.fill((25, 30, 40)) 
    pygame.draw.rect(screen, (80, 170, 255), paddle) # рисуем прямоугольник
    pygame.display.flip() # показывает что мы нарисовали
    clock.tick(60) # 60 кадров в секунду


pygame.quit()
