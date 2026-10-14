import random
import sys
from pathlib import Path

import pygame

# При запуске файла напрямую Python должен видеть соседнюю папку game/.
if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client import ui
from game.logic import Game, WIDTH, HEIGHT, BALL_RADIUS, BOSS_MAX_HEALTH
from game.demo import MenuDemo

# Клиент хранит только окно, выбор пункта меню и визуальные эффекты.
game = Game()
demo = MenuDemo()
MENU_ACTIONS = ("start", "controls", "boss_test", "exit")
screen = None
clock = None
running = True
selected_button = 0
ball_trail = []
particles = []
transition_surface = None
transition_timer = 0.0
last_drawn_state = None


def clear_effects():
    ball_trail.clear()
    particles.clear()


def perform_action(action):
    global running, selected_button
    if action in ("start", "boss_test", "retry"):
        boss_test = game.boss_test if action == "retry" else action == "boss_test"
        game.start(boss_test=boss_test)
        clear_effects()
    elif action == "controls":
        game.state = "controls"
    elif action == "exit":
        running = False
    elif action in ("resume", "pause"):
        game.toggle_pause()
    elif action == "menu":
        game.state = "menu"
        selected_button = 0
        clear_effects()


def handle_event(event):
    global running, selected_button
    if event.type == pygame.QUIT:
        running = False
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        for action, rect in ui.buttons_for_state(game.state).items():
            if rect.collidepoint(event.pos):
                perform_action(action)
                break
    elif event.type == pygame.MOUSEMOTION and game.state == "menu":
        for index, rect in enumerate(ui.MENU_BUTTONS.values()):
            if rect.collidepoint(event.pos):
                selected_button = index
                break
    elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            perform_action("exit" if game.state == "menu" else "menu")
        elif game.state == "menu":
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                change = -1 if event.key == pygame.K_UP else 1
                selected_button = (selected_button + change) % len(MENU_ACTIONS)
            elif event.key == pygame.K_RETURN:
                perform_action(MENU_ACTIONS[selected_button])
            elif event.key == pygame.K_b:
                perform_action("boss_test")
        elif game.state == "controls":
            if event.key == pygame.K_RETURN:
                perform_action("menu")
        elif event.key == pygame.K_RETURN and game.state in ("game_over", "win"):
            perform_action("retry")
        elif event.key == pygame.K_p:
            game.toggle_pause()
        elif event.key == pygame.K_SPACE:
            game.launch_ball()
        elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            game.activate_slow()


def add_particles(x, y, color_index):
    # Частицы относятся только к отображению и не влияют на столкновения.
    color = ui.BRICK_COLORS[color_index % len(ui.BRICK_COLORS)]
    for _ in range(8):
        particles.append({
            "x": float(x), "y": float(y),
            "vx": random.uniform(-100, 100),
            "vy": random.uniform(-110, 70),
            "life": 0.35, "color": color,
        })


def update_effects(dt):
    # Пауза останавливает и физику, и визуальные анимации.
    if game.state not in ("playing", "boss_defeated"):
        return
    for particle in particles[:]:
        particle["life"] -= dt
        particle["x"] += particle["vx"] * dt
        particle["y"] += particle["vy"] * dt
        particle["vy"] += 200 * dt
        if particle["life"] <= 0:
            particles.remove(particle)
    for x, y, color_index in game.hit_events:
        add_particles(x, y, color_index)
    if game.ball_attached:
        ball_trail.clear()
    else:
        ball_trail.append((game.ball_x, game.ball_y))
        if len(ball_trail) > 8:
            ball_trail.pop(0)


def update(dt):
    global transition_timer
    dt = max(0.0, min(dt, 1 / 30))
    transition_timer = max(0.0, transition_timer - dt)
    if game.state == "menu":
        demo.update(dt)
    ui.update_animations(game.state, selected_button, dt, demo.reset_timer > 0)
    keys = pygame.key.get_pressed()
    direction = int(keys[pygame.K_RIGHT] or keys[pygame.K_d])
    direction -= int(keys[pygame.K_LEFT] or keys[pygame.K_a])
    game.update(dt, direction)
    update_effects(max(0.0, min(dt, 1 / 30)))


def draw_scene():
    if game.state == "menu":
        ui.draw_menu(screen, selected_button, demo)
        return
    if game.state == "controls":
        ui.draw_controls(screen)
        return
    ui.draw_game_background(screen)
    ui.draw_top_bar(screen, game)
    if game.level == 4:
        ui.draw_boss_health(screen, game, BOSS_MAX_HEALTH)
        ui.draw_boss(screen, game)
        ui.draw_boss_attacks(screen, game)
    for brick in game.bricks:
        ui.draw_brick(screen, ui.pygame_rect(brick),
                      ui.BRICK_COLORS[brick.color_index % len(ui.BRICK_COLORS)])
    ui.draw_particles(screen, particles)
    ui.draw_paddle(screen, ui.pygame_rect(game.paddle), game.shrink_timer > 0)
    ui.draw_ball(screen, game.ball_x, game.ball_y, BALL_RADIUS,
                 ball_trail, game.slow_timer > 0)
    ui.draw_footer(screen, game)
    if game.ball_attached:
        ui.draw_ready_hint(screen, game.level)
    if game.state in ("paused", "game_over", "win"):
        ui.draw_modal(screen, game.state, game.score, game.boss_test)


def draw():
    global last_drawn_state, transition_surface, transition_timer
    # При смене экрана предыдущий кадр мягко исчезает за 0,18 секунды.
    if last_drawn_state is not None and last_drawn_state != game.state:
        transition_surface = screen.copy()
        transition_timer = 0.18
    draw_scene()
    if transition_timer > 0 and transition_surface is not None:
        transition_surface.set_alpha(round(255 * transition_timer / 0.18))
        screen.blit(transition_surface, (0, 0))
    last_drawn_state = game.state


def initialize():
    global screen, clock, running, selected_button, demo
    global transition_surface, transition_timer, last_drawn_state
    # Звука в игре нет, поэтому аудиоустройство инициализировать не нужно.
    pygame.display.init()
    pygame.font.init()
    screen = pygame.display.set_mode((WIDTH, HEIGHT))
    pygame.display.set_caption("Brickfall")
    clock = pygame.time.Clock()
    ui.initialize_fonts()
    game.start()
    game.state = "menu"
    running = True
    selected_button = 0
    demo = MenuDemo()
    transition_surface = None
    transition_timer = 0.0
    last_drawn_state = None
    ui.button_progress.clear()
    ui.demo_visibility = 1.0
    clear_effects()


def main():
    initialize()
    try:
        while running:
            dt = clock.tick(60) / 1000.0
            for event in pygame.event.get():
                handle_event(event)
            if not running:
                break
            update(dt)
            draw()
            pygame.display.flip()
    finally:
        pygame.quit()


# При импорте игровой цикл не запускается.
if __name__ == "__main__":
    main()
