import pygame

# Собственный пиксельный персонаж. Сетка 44 x 42, один пиксель увеличен в 4 раза.
# Скачанные картинки не нужны; отдельные части позволяют менять позу.
INK = (30, 42, 48)
STEEL = (83, 108, 114)
LIGHT = (157, 177, 173)
ARMOR = (210, 139, 123)
SHADOW = (126, 81, 77)
GOLD = (222, 192, 131)
PALE = (239, 235, 199)
frames = {}


def make_frame(pose, phase, arm_step):
    sprite = pygame.Surface((44, 42), pygame.SRCALPHA)
    armor = (233, 184, 162) if pose == "hit" else ARMOR
    signal = (229, 151, 134) if phase == 2 else GOLD
    if pose == "attack":
        signal = PALE

    def block(color, x, y, width, height):
        pygame.draw.rect(sprite, color, (x, y, width, height))

    # Голова с уступами, боковыми антеннами и широким цифровым визором.
    head = [(13, 0), (31, 0), (31, 2), (33, 2), (33, 9),
            (31, 9), (31, 11), (13, 11), (13, 9), (11, 9), (11, 2), (13, 2)]
    pygame.draw.polygon(sprite, INK, head)
    block(armor, 13, 1, 18, 9)
    block(LIGHT, 14, 1, 14, 1)
    block(SHADOW, 13, 9, 18, 1)
    block(STEEL, 8, 3, 3, 6)
    block(STEEL, 33, 3, 3, 6)
    block(signal, 8, 2, 2, 2)
    block(signal, 34, 2, 2, 2)
    block(INK, 14, 3, 16, 5)
    block(signal, 15, 5, 5, 2)
    block(signal, 24, 5, 5, 2)
    block(armor, 15, 5, 1, 1)
    block(armor, 28, 5, 1, 1)
    block(STEEL, 18, 11, 8, 2)

    # Плечевые пластины и отдельные тяжёлые предплечья.
    raised = -2 if pose == "attack" else arm_step
    for x, direction in ((1, 1), (35, -1)):
        block(INK, x, 13, 8, 9)
        block(STEEL, x + 1, 14, 6, 7)
        block(LIGHT, x + 1, 14, 5, 1)
        block(armor, x + 2, 16, 4, 3)
        elbow_x = 2 if direction == 1 else 36
        block(INK, elbow_x, 22 + raised, 6, 3)
        forearm_x = 0 if direction == 1 else 37
        block(INK, forearm_x, 24 + raised, 7, 8)
        block(STEEL, forearm_x + 1, 24 + raised, 5, 7)
        block(LIGHT, forearm_x + 1, 25 + raised, 1, 5)
        block(INK, forearm_x + 1, 29 + raised, 5, 2)

    # Корпус имеет скошенные углы и внутренние механические детали.
    hull = [(12, 12), (32, 12), (35, 16), (33, 28), (28, 32),
            (16, 32), (11, 28), (9, 16)]
    pygame.draw.polygon(sprite, INK, hull)
    plate = [(13, 13), (31, 13), (33, 16), (31, 27), (27, 30),
             (17, 30), (13, 27), (11, 16)]
    pygame.draw.polygon(sprite, armor, plate)
    block(LIGHT, 14, 13, 15, 1)
    block(SHADOW, 13, 25, 3, 3)
    block(SHADOW, 28, 25, 3, 3)
    block(INK, 16, 16, 12, 10)
    block(STEEL, 17, 17, 10, 8)
    for y in (18, 21, 24):
        block(INK, 18, y, 8, 1)
    block(signal, 21, 18, 2, 6)
    block(PALE, 21, 19, 1, 2)

    # Нижнее ядро — заметное, доступное для мяча слабое место.
    block(INK, 18, 28, 8, 9)
    block(GOLD, 19, 28, 6, 8)
    block(SHADOW, 19, 28, 1, 8)
    block(PALE, 21, 30, 2, 4)

    # Две отдельные ноги и маленькие сопла дают узнаваемый силуэт.
    for x in (11, 25):
        block(INK, x, 32, 8, 6)
        block(STEEL, x + 1, 32, 6, 5)
        block(armor, x + 1, 33, 5, 2)
        block(LIGHT, x + 1, 36, 6, 1)
        if pose != "defeat":
            block(GOLD, x + 3, 38, 2, 2 + arm_step)
            block(PALE, x + 3, 38, 2, 1)
    return pygame.transform.scale(sprite, (176, 168))


def draw(surface, rect, pose, phase, time, defeat_progress=0.0):
    arm_step = int(time * 3) % 2
    key = (pose, phase, arm_step)
    if key not in frames:
        frames[key] = make_frame(*key)
    sprite = frames[key]
    if pose == "defeat":
        # Разбиваем образ на полосы: части расходятся и падают, затем исчезают.
        progress = max(0.0, min(1.0, defeat_progress))
        for index in range(8):
            piece = sprite.subsurface((0, index * 20, 176, 20)).copy()
            piece.set_alpha(round(255 * (1 - progress)))
            direction = -1 if index % 2 else 1
            x = rect.x + direction * progress * (18 + index * 8)
            y = rect.y + index * 20 + progress ** 2 * 95
            surface.blit(piece, (round(x), round(y)))
        return
    # Положение корпуса совпадает с логикой; двигаются только отдельные детали.
    surface.blit(sprite, rect.topleft)
