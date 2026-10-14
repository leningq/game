import pygame

from . import robot

# Спокойная палитра. Весь визуал рисуется фигурами, без внешних картинок.
BG = (13, 20, 26)
PANEL = (20, 29, 36)
LINE = (43, 58, 65)
TEXT = (237, 242, 235)
MUTED = (143, 161, 163)
MINT = (156, 218, 195)
CORAL = (229, 151, 134)
GOLD = (222, 192, 131)
BRICK_COLORS = [MINT, (139, 184, 203), (166, 158, 198), GOLD, CORAL, (131, 184, 163)]
fonts = {}
button_progress = {}
demo_visibility = 1.0
DEBUFF_STYLES = {
    "slow": ("Slow paddle", BRICK_COLORS[1]),
    "narrow": ("Narrow paddle", GOLD),
    "reverse": ("Reverse controls", CORAL),
}

# Одни и те же прямоугольники нужны для рисования кнопок и проверки клика.
MENU_BUTTONS = {
    "start": pygame.Rect(52, 316, 336, 44),
    "controls": pygame.Rect(52, 364, 336, 44),
    "boss_test": pygame.Rect(52, 412, 336, 44),
    "exit": pygame.Rect(52, 460, 336, 44),
}
PAUSE_BUTTONS = {
    "resume": pygame.Rect(286, 326, 328, 46),
    "menu": pygame.Rect(286, 385, 328, 42),
}
END_BUTTONS = {
    "retry": pygame.Rect(286, 326, 328, 46),
    "menu": pygame.Rect(286, 385, 328, 42),
}
CONTROLS_BUTTONS = {"menu": pygame.Rect(286, 493, 328, 40)}
PLAY_BUTTONS = {"pause": pygame.Rect(783, 30, 74, 28)}


def initialize_fonts():
    # Если Segoe UI нет, SysFont автоматически подставит доступный шрифт.
    for name, size, bold in (
        ("title", 72, True), ("heading", 34, True), ("number", 18, False),
        ("body", 20, False), ("button", 18, False), ("small", 14, False),
        ("tiny", 11, False), ("logo", 16, False),
    ):
        fonts[name] = pygame.font.SysFont("segoeui,arial", size, bold=bold)


def text(surface, value, pos, size="small", color=TEXT, center=False):
    image = fonts[size].render(str(value), True, color)
    rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
    surface.blit(image, rect)


def pygame_rect(rect):
    # Перевод числового прямоугольника из game/ в объект для рисования.
    return pygame.Rect(round(rect.x), round(rect.y), round(rect.width), round(rect.height))


def buttons_for_state(state):
    if state == "menu":
        return MENU_BUTTONS
    if state == "paused":
        return PAUSE_BUTTONS
    if state in ("game_over", "win"):
        return END_BUTTONS
    if state == "controls":
        return CONTROLS_BUTTONS
    if state in ("playing", "boss_defeated"):
        return PLAY_BUTTONS
    return {}


def draw_button(surface, rect, label, shortcut="", primary=False, selected=False):
    amount = button_progress.get(tuple(rect), 1.0 if selected else 0.0)
    base = MINT if primary else PANEL
    hover = (183, 235, 214) if primary else (34, 49, 56)
    fill = tuple(round(base[i] + (hover[i] - base[i]) * amount) for i in range(3))
    pygame.draw.rect(surface, fill, rect, border_radius=9)
    if not primary:
        pygame.draw.rect(surface, MINT if amount > 0.5 else LINE, rect, 1, border_radius=9)
    color = BG if primary else TEXT
    y = rect.y + (rect.height - fonts["button"].get_height()) // 2
    text(surface, label, (rect.x + 18, y), "button", color)
    if shortcut:
        image = fonts["tiny"].render(shortcut, True, BG if primary else MUTED)
        surface.blit(image, image.get_rect(midright=(rect.right - 18, rect.centery)))


def draw_base(surface):
    surface.fill(BG)
    # Едва заметные точки вместо шумного фонового изображения.
    for x in range(28, 900, 32):
        for y in range(100, 554, 32):
            pygame.draw.circle(surface, (25, 36, 43), (x, y), 1)


def draw_brick(surface, rect, color):
    pygame.draw.rect(surface, (7, 13, 18), rect.move(0, 3), border_radius=5)
    pygame.draw.rect(surface, color, rect, border_radius=5)
    highlight = tuple(min(255, channel + 22) for channel in color)
    pygame.draw.line(surface, highlight, (rect.left + 7, rect.top + 3),
                     (rect.right - 7, rect.top + 3), 1)


def draw_paddle(surface, rect, shrunken=False):
    color = GOLD if shrunken else MINT
    pygame.draw.rect(surface, (29, 45, 47), rect.inflate(8, 6), border_radius=10)
    pygame.draw.rect(surface, color, rect, border_radius=6)
    pygame.draw.line(surface, TEXT, (rect.left + 12, rect.top + 2),
                     (rect.right - 12, rect.top + 2))
    pygame.draw.line(surface, BG, (rect.centerx - 8, rect.centery),
                     (rect.centerx + 8, rect.centery), 2)


def draw_ball(surface, x, y, radius, trail, slowed=False):
    color = GOLD if slowed else MINT
    # Короткий след показывает направление и не закрывает кирпичи.
    trail_color = tuple(round(BG[c] + (color[c] - BG[c]) * 0.3) for c in range(3))
    for index, (trail_x, trail_y) in enumerate(trail):
        trail_radius = max(1, round(radius * (index + 1) / (len(trail) + 2)))
        pygame.draw.circle(surface, trail_color, (round(trail_x), round(trail_y)), trail_radius)
    position = (round(x), round(y))
    pygame.draw.circle(surface, (32, 52, 54), position, radius + 3)
    pygame.draw.circle(surface, color, position, radius)
    pygame.draw.circle(surface, TEXT, position, max(2, radius - 3))
    pygame.draw.circle(surface, (255, 255, 248), (round(x - 2), round(y - 2)), 2)


def draw_particles(surface, particles):
    for particle in particles:
        radius = max(1, round(3 * particle["life"] / 0.35))
        pygame.draw.circle(surface, particle["color"],
                           (round(particle["x"]), round(particle["y"])), radius)


def update_animations(state, selected_button, dt, demo_resetting=False):
    global demo_visibility
    # Небольшая интерполяция вместо резкого включения подсветки.
    step = min(1.0, max(0.0, dt) / 0.12)
    for index, (action, rect) in enumerate(buttons_for_state(state).items()):
        active = rect.collidepoint(pygame.mouse.get_pos())
        active = active or (state == "menu" and selected_button == index)
        key = tuple(rect)
        previous = button_progress.get(key, 0.0)
        button_progress[key] = previous + (float(active) - previous) * step
    target = 0.0 if demo_resetting else 1.0
    demo_visibility += (target - demo_visibility) * min(1.0, dt / 0.2)


def draw_menu_item(surface, action, rect, index, selected):
    amount = button_progress.get(tuple(rect), 0.0)
    fill = tuple(round(BG[c] + (PANEL[c] - BG[c]) * amount) for c in range(3))
    pygame.draw.rect(surface, fill, rect)
    pygame.draw.line(surface, LINE, (rect.x, rect.bottom), (rect.right, rect.bottom))
    if amount > 0.02:
        pygame.draw.rect(surface, MINT, (rect.x, rect.y + 10, 2, 24))
    labels = {"start": "Start Game", "controls": "Controls", "boss_test": "Boss Test", "exit": "Exit"}
    text(surface, f"0{index + 1}", (rect.x + 13, rect.y + 14), "tiny", MINT if selected else MUTED)
    text(surface, labels[action], (rect.x + 47 + round(amount * 4), rect.y + 9),
         "button", TEXT if selected else MUTED)
    tag = "B / LAB" if action == "boss_test" else "ENTER" if selected else ""
    text(surface, tag, (rect.right - 62, rect.y + 15), "tiny", MUTED)
    if selected:
        pygame.draw.polygon(surface, MINT, [(rect.right - 13, rect.y + 17),
                                          (rect.right - 8, rect.y + 22),
                                          (rect.right - 13, rect.y + 27)])


def draw_menu(surface, selected_button, demo):
    # Панель аркадного автомата: крупная типографика и настоящее живое поле.
    surface.fill(BG)
    for row in range(3):
        pygame.draw.rect(surface, MINT, (52 + row * 3, 31 + row * 7, 20, 4))
    text(surface, "BRICKFALL / ARCADE", (91, 33), "small", TEXT)
    text(surface, "CAMPAIGN  01—04", (720, 35), "tiny", MUTED)
    pygame.draw.line(surface, LINE, (52, 72), (848, 72))
    text(surface, "KEEP THE BALL IN PLAY", (54, 96), "tiny", MINT)
    text(surface, "BRICK", (48, 112), "title")
    text(surface, "FALL", (48, 184), "title")
    text(surface, "Precision under pressure.", (54, 277), "small", MUTED)
    for index, (action, rect) in enumerate(MENU_BUTTONS.items()):
        draw_menu_item(surface, action, rect, index, selected_button == index)
    frame = pygame.Rect(456, 91, 392, 445)
    pygame.draw.rect(surface, PANEL, frame, border_radius=4)
    pygame.draw.rect(surface, LINE, frame, 1, border_radius=4)
    pygame.draw.circle(surface, MINT, (478, 111), 3)
    text(surface, "LIVE / ATTRACT MODE", (491, 103), "tiny", MUTED)
    text(surface, f"{demo.hits:02d} BREAKS", (763, 103), "tiny", MINT)
    scene = pygame.Surface((360, 362))
    scene.fill(PANEL)
    pygame.draw.line(scene, LINE, (12, 12), (348, 12))
    pygame.draw.line(scene, LINE, (12, 12), (12, 352))
    pygame.draw.line(scene, LINE, (348, 12), (348, 352))
    for brick in demo.bricks:
        draw_brick(scene, pygame_rect(brick), BRICK_COLORS[brick.color_index])
    draw_paddle(scene, pygame_rect(demo.paddle))
    # Координаты приходят из симуляции; искусственного следа нет.
    draw_ball(scene, demo.ball_x, demo.ball_y, 8, [])
    scene.set_alpha(round(255 * demo_visibility))
    surface.blit(scene, (472, 130))
    text(surface, "BALL / WALL / BRICK / REPEAT", (475, 509), "tiny", MUTED)
    pygame.draw.line(surface, LINE, (52, 547), (848, 547))
    text(surface, "3 stages + a final adversary", (52, 560), "small", MUTED)
    text(surface, "UP / DOWN  select   ·   ENTER  play", (570, 560), "small", MUTED)


def draw_game_background(surface):
    draw_base(surface)
    pygame.draw.rect(surface, PANEL, (24, 18, 852, 60), border_radius=12)
    pygame.draw.rect(surface, LINE, (24, 18, 852, 60), 1, border_radius=12)
    # Нижняя сторона открыта: за ней игрок теряет жизнь.
    pygame.draw.line(surface, LINE, (24, 96), (876, 96))
    pygame.draw.line(surface, LINE, (24, 96), (24, 556))
    pygame.draw.line(surface, LINE, (876, 96), (876, 556))


def draw_top_bar(surface, game):
    # Значения в одну строку: меньше тяжёлых заголовков и разделителей.
    for row in range(3):
        pygame.draw.rect(surface, MINT, (43 + row * 2, 34 + row * 6, 16, 3))
    text(surface, "Brickfall", (77, 36), "logo")
    text(surface, "Score", (239, 37), "small", MUTED)
    text(surface, f"{game.score:04d}", (290, 35), "number")
    text(surface, "Stage", (425, 37), "small", MUTED)
    value = f"0{game.level} / 04" if game.level <= 3 else "04 / Boss"
    text(surface, value, (475, 36), "logo", CORAL if game.level == 4 else TEXT)
    text(surface, "Lives", (651, 37), "small", MUTED)
    for index in range(3):
        pygame.draw.rect(surface, MINT if index < game.lives else LINE,
                         (698 + index * 18, 40, 9, 9), border_radius=2)
    rect = PLAY_BUTTONS["pause"]
    amount = button_progress.get(tuple(rect), 0.0)
    pygame.draw.rect(surface, LINE if amount > 0.3 else PANEL, rect, border_radius=4)
    text(surface, "P  Pause", (rect.x + 10, rect.y + 5), "small", MUTED)


def draw_boss(surface, game):
    pose = "idle"
    if game.state == "boss_defeated" or game.boss_health == 0:
        pose = "defeat"
    elif game.boss_hit_timer > 0.38:
        pose = "hit"
    elif game.warning_timer > 0:
        pose = "attack"
    progress = (1.8 - game.defeat_timer) / 1.8 if pose == "defeat" else 0.0
    robot.draw(surface, pygame_rect(game.boss), pose, game.boss_phase, game.boss_time, progress)


def draw_boss_health(surface, game, max_health):
    text(surface, "WARDEN / R-04", (44, 108), "tiny", CORAL)
    text(surface, f"PHASE {game.boss_phase}", (206, 108), "tiny", MUTED)
    bar = pygame.Rect(319, 114, 463, 5)
    pygame.draw.rect(surface, LINE, bar)
    fill = bar.copy()
    fill.width = round(bar.width * max(0, game.boss_health) / max_health)
    if fill.width > 0:
        pygame.draw.rect(surface, CORAL, fill)
    text(surface, f"{game.boss_health:02d} / {max_health}", (803, 107), "tiny", MUTED)


def draw_debuff_icon(surface, kind, center, size=20):
    x, y = center
    color = DEBUFF_STYLES[kind][1]
    radius = size // 2
    if kind == "slow":
        pygame.draw.circle(surface, color, center, radius, 2)
        pygame.draw.line(surface, color, center, (x, y - radius + 4), 2)
        pygame.draw.line(surface, color, center, (x + radius - 4, y), 2)
    elif kind == "narrow":
        pygame.draw.rect(surface, color, (x - radius, y - radius, size, size), 2)
        pygame.draw.lines(surface, color, False, [(x - 5, y - 4), (x - 2, y), (x - 5, y + 4)], 2)
        pygame.draw.lines(surface, color, False, [(x + 5, y - 4), (x + 2, y), (x + 5, y + 4)], 2)
    else:
        pygame.draw.polygon(surface, color, [(x, y - radius), (x + radius, y),
                                            (x, y + radius), (x - radius, y)], 2)
        pygame.draw.line(surface, color, (x - 5, y - 2), (x + 4, y - 2), 2)
        pygame.draw.line(surface, color, (x - 4, y + 2), (x + 5, y + 2), 2)
        pygame.draw.line(surface, color, (x - 5, y - 2), (x - 2, y - 5), 2)
        pygame.draw.line(surface, color, (x + 5, y + 2), (x + 2, y + 5), 2)


def draw_boss_attacks(surface, game):
    for drop in game.drops:
        draw_debuff_icon(surface, drop.kind, (round(drop.centerx), round(drop.centery)))
    if game.warning_timer <= 0:
        return
    color = DEBUFF_STYLES[game.attack_kind][1]
    x = round(game.attack_target_x)
    # Метка показывает место будущего попадания до запуска снаряда.
    pygame.draw.lines(surface, color, False,
                      [(x - 24, 513), (x - 24, 518), (x + 24, 518), (x + 24, 513)], 2)
    label = DEBUFF_STYLES[game.attack_kind][0] + " / incoming"
    text(surface, label, (max(135, min(765, x)), 499), "small", color, center=True)
    draw_debuff_icon(surface, game.attack_kind,
                     (round(game.boss.centerx), round(game.boss.y - 12)), 16)


def draw_footer(surface, game):
    effects = []
    for kind, timer in game.debuff_timers.items():
        if timer > 0:
            label, color = DEBUFF_STYLES[kind]
            effects.append((label, timer, color))
    if game.shrink_timer > 0 and game.debuff_timers["narrow"] <= 0:
        effects.append(("Narrow paddle", game.shrink_timer, GOLD))
    if game.slow_timer > 0:
        effects.append(("Slow ball", game.slow_timer, MINT))
    for index, (label, timer, color) in enumerate(effects):
        rect = pygame.Rect(24 + index * 198, 550, 190, 22)
        pygame.draw.rect(surface, PANEL, rect, border_radius=3)
        text(surface, f"{label}  {timer:.1f}s", (rect.x + 8, rect.y + 2), "small", color)
    if not effects:
        text(surface, "Space to launch" if game.ball_attached else "Aim with the paddle. Keep the ball in play.",
             (24, 552), "small", MUTED)
    text(surface, "Move  ← → / A D", (24, 580), "small", MUTED)
    text(surface, "Shift  slow used" if game.slow_used else "Shift  slow ready",
         (293, 580), "small", MUTED if game.slow_used else MINT)
    text(surface, "P  pause", (599, 580), "small", MUTED)
    text(surface, "Esc  menu", (789, 580), "small", MUTED)


def draw_ready_hint(surface, level):
    text(surface, "FINAL STAGE / THE GUARDIAN" if level == 4 else f"STAGE 0{level} / READY",
         (450, 434), "tiny", CORAL if level == 4 else MUTED, center=True)
    pill = pygame.Rect(333, 455, 234, 36)
    pygame.draw.rect(surface, PANEL, pill, border_radius=18)
    pygame.draw.rect(surface, LINE, pill, 1, border_radius=18)
    text(surface, "SPACE  to launch", pill.center, "small", MINT, center=True)


def draw_modal(surface, state, score, boss_test=False):
    overlay = pygame.Surface((900, 600), pygame.SRCALPHA)
    overlay.fill((5, 10, 14, 205))
    surface.blit(overlay, (0, 0))
    card = pygame.Rect(250, 171, 400, 285)
    pygame.draw.rect(surface, PANEL, card, border_radius=18)
    pygame.draw.rect(surface, LINE, card, 1, border_radius=18)
    if state == "paused":
        title, subtitle, color = "PAUSED", "Take a breath. Your run is waiting.", MINT
        label, shortcut = "Continue", "P"
    elif state == "game_over":
        title, subtitle, color = "GAME OVER", f"Final score / {score:04d}", CORAL
        label, shortcut = "Retry boss" if boss_test else "Try again", "ENTER"
    else:
        title, subtitle, color = "VICTORY", f"Guardian defeated. Score / {score:04d}", MINT
        label, shortcut = "Retry boss" if boss_test else "Play again", "ENTER"
    text(surface, "BOSS LAB / R-04" if boss_test else "BRICKFALL / YOUR RUN", (450, 206), "tiny", MUTED, center=True)
    text(surface, title, (450, 246), "heading", color, center=True)
    text(surface, subtitle, (450, 289), "small", MUTED, center=True)
    buttons = buttons_for_state(state)
    primary_action = "resume" if state == "paused" else "retry"
    draw_button(surface, buttons[primary_action], label, shortcut, primary=True)
    draw_button(surface, buttons["menu"], "Main menu", "ESC")


def draw_controls(surface):
    draw_base(surface)
    card = pygame.Rect(182, 50, 536, 510)
    pygame.draw.rect(surface, PANEL, card, border_radius=8)
    pygame.draw.rect(surface, LINE, card, 1, border_radius=8)
    text(surface, "CONTROLS / CAMPAIGN + BOSS LAB", (450, 83), "tiny", MINT, center=True)
    text(surface, "Move. Aim. Dodge.", (450, 122), "heading", center=True)
    rows = [
        ("ARROWS / A D", "Move the paddle"),
        ("SPACE", "Launch from the paddle"),
        ("SHIFT", "Slow ball: 3s, once per stage"),
        ("P", "Pause / continue"),
        ("ESC", "Return to menu"),
    ]
    for index, (key, description) in enumerate(rows):
        y = 167 + index * 32
        text(surface, key, (213, y), "small", MINT)
        text(surface, description, (379, y), "small")
    pygame.draw.line(surface, LINE, (213, 336), (687, 336))
    text(surface, "BOSS DROPS / DODGE THE MARKED TARGET", (213, 350), "tiny", MUTED)
    for index, kind in enumerate(("slow", "narrow", "reverse")):
        x = 224 + index * 160
        draw_debuff_icon(surface, kind, (x, 390), 16)
        text(surface, ("Slow paddle", "Narrow paddle", "Reverse keys")[index],
             (x + 15, 381), "small", DEBUFF_STYLES[kind][1])
    text(surface, "Every 5 bricks: narrower paddle for 3 seconds.", (450, 428), "small", MUTED, center=True)
    text(surface, "Boss core: double damage. Drops: 4s / 4s / 3s.", (450, 450), "small", MUTED, center=True)
    text(surface, "Boss Test starts stage 04 with 3 lives.", (450, 472), "small", MUTED, center=True)
    draw_button(surface, CONTROLS_BUTTONS["menu"], "Back to menu", "ESC")
