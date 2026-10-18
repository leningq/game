import random
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

import pygame

if __package__ in (None, ""):
    sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from client import ui
from client.api_client import ApiClient, ApiError
from game.logic import Game, WIDTH, HEIGHT, BALL_RADIUS
from game.demo import MenuDemo

game = Game()
demo = MenuDemo()
api = ApiClient()
screen = None
clock = None
running = True
selected_button = 0
has_run = False
status = ""
status_error = False
username_input = ""
password_input = ""
active_field = 0
executor = None
pending = None
pending_action = None
pending_run_id = None
auth_cancelled = False
score_state = ""
ball_trail = []
particles = []


def show_status(message, error=False):
    global status, status_error
    status, status_error = message, error


def clear_effects():
    ball_trail.clear()
    particles.clear()


def begin_request(action, function, *args):
    global pending, pending_action, pending_run_id, auth_cancelled
    if pending is not None:
        show_status("Waiting for the server...")
        return False
    if action in ("login", "register"):
        auth_cancelled = False
    pending_action = action
    pending_run_id = game.run_id
    pending = executor.submit(function, *args)
    show_status("Connecting..." if action in ("login", "register") else "Waiting for the server...")
    return True


def poll_request():
    global pending, pending_action, password_input, game, has_run, score_state, selected_button
    if pending is None or not pending.done():
        return
    action, run_id = pending_action, pending_run_id
    future = pending
    pending = None
    pending_action = None
    if action in ("login", "register") and (auth_cancelled or game.state not in ("login", "register")):
        return
    try:
        result = future.result()
        if action in ("login", "register"):
            api.token = result["token"]
            api.username = result["username"]
            password_input = ""
            game.state = "menu"
            selected_button = 0 if has_run else 1
            pygame.key.stop_text_input()
            show_status("Signed in as " + api.username + ". Choose New game to play.")
        elif action == "save":
            show_status("Game saved. Continue here or load it from the menu.")
        elif action == "load":
            game = Game.from_dict(result)
            has_run = True
            score_state = ""
            clear_effects()
            show_status("Game loaded and paused. Press P to continue.")
        elif action == "score":
            if game.run_id == run_id:
                score_state = "saved"
            show_status("Result saved to the leaderboard.")
    except (ApiError, ValueError, KeyError, TypeError) as error:
        if action == "score" and game.run_id == run_id:
            score_state = "error"
        if action == "register" and isinstance(error, ApiError) and error.status_code == 409:
            game.state = "login"
            show_status("This username is already registered. Sign in with your password.", True)
        else:
            show_status(str(error) or "Unable to process the server response.", True)


def require_login():
    if api.token:
        return True
    game.state = "login"
    pygame.key.start_text_input()
    show_status("Sign in or create an account to play.")
    return False


def register_and_login(username, password):
    api.register(username, password)
    return api.login(username, password)


def submit_auth():
    if pending is not None:
        return
    username = username_input.strip()
    if not username or not password_input:
        show_status("Enter a username and password.", True)
        return
    if game.state == "register":
        if not (3 <= len(username) <= 20) or not all(c.isascii() and (c.isalnum() or c in "_-") for c in username):
            show_status("Username: 3-20 letters, numbers, _ or -.", True)
            return
        if not 8 <= len(password_input) <= 128:
            show_status("Password: 8-128 characters.", True)
            return
        begin_request("register", register_and_login, username, password_input)
    else:
        begin_request("login", api.login, username, password_input)


def perform_action(action):
    global running, selected_button, has_run, score_state, password_input, active_field, auth_cancelled
    if action == "exit":
        running = False
        return
    if action == "menu":
        if game.state == "playing":
            game.toggle_pause()
            return
        if game.state in ("login", "register"):
            auth_cancelled = True
        game.state = "menu"
        selected_button = 0 if has_run else 1
        password_input = ""
        pygame.key.stop_text_input()
        clear_effects()
        return
    if action == "controls":
        game.state = "controls"
        return
    if action in ("login", "register"):
        if pending is not None:
            return
        game.state = action
        pygame.key.start_text_input()
        show_status("Username: 3-20 letters, numbers, _ or -. Password: 8-128 characters.")
        return
    if action == "auth":
        submit_auth()
        return
    if action == "account":
        if pending is not None:
            return
        if api.token:
            api.token = api.username = None
            has_run = False
            game.state = "menu"
            show_status("Signed out.")
        else:
            perform_action("login")
        return
    if action in ("start", "retry", "load", "save", "resume", "continue") and pending is not None:
        show_status("Waiting for the server...")
        return
    if action in ("start", "retry"):
        if require_login():
            game.start()
            has_run = True
            score_state = ""
            clear_effects()
            show_status("")
    elif action in ("resume", "continue"):
        if has_run and game.state not in ("win", "game_over") and require_login():
            game.state = "playing"
            show_status("")
        elif not has_run:
            show_status("Start a new game or load a saved game.")
    elif action == "pause":
        game.toggle_pause()
    elif action == "save":
        if has_run and game.state in ("playing", "paused") and require_login():
            if game.state == "playing":
                game.toggle_pause()
            begin_request("save", api.save, game.to_dict())
    elif action == "load":
        if require_login():
            begin_request("load", api.load)
    elif action == "send_score":
        if score_state == "error" and api.token:
            if begin_request("score", api.send_score, game.score, game.run_id):
                score_state = "pending"


def viewport():
    width, height = pygame.display.get_surface().get_size()
    scale = min(width / WIDTH, height / HEIGHT)
    area = pygame.Rect(0, 0, max(1, round(WIDTH * scale)), max(1, round(HEIGHT * scale)))
    area.center = (width // 2, height // 2)
    return area


def game_position(position):
    area = viewport()
    return ((position[0] - area.x) * WIDTH / area.width,
            (position[1] - area.y) * HEIGHT / area.height)


def present():
    window = pygame.display.get_surface()
    area = viewport()
    window.fill(ui.BG)
    image = screen if area.size == screen.get_size() else pygame.transform.smoothscale(screen, area.size)
    window.blit(image, area)
    pygame.display.flip()


def handle_event(event):
    global running, selected_button, active_field, username_input, password_input
    position = game_position(event.pos) if hasattr(event, "pos") else None
    if event.type == pygame.QUIT:
        running = False
    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
        if game.state in ("login", "register"):
            for index, rect in enumerate(ui.AUTH_FIELDS):
                if rect.collidepoint(position):
                    active_field = index
        for action, rect in ui.buttons_for_state(game.state).items():
            if rect.collidepoint(position):
                perform_action(action)
                break
    elif event.type == pygame.MOUSEMOTION and game.state == "menu":
        for index, rect in enumerate(ui.MENU_BUTTONS.values()):
            if rect.collidepoint(position):
                selected_button = index
                break
    elif event.type == pygame.TEXTINPUT and game.state in ("login", "register") and pending is None:
        value = "".join(char for char in event.text if char.isprintable())
        if active_field == 0:
            username_input = (username_input + value)[:128]
        else:
            password_input = (password_input + value)[:256]
    elif event.type == pygame.KEYDOWN:
        if event.key == pygame.K_ESCAPE:
            perform_action("exit" if game.state == "menu" else "menu")
        elif game.state in ("login", "register"):
            if event.key == pygame.K_TAB:
                active_field = 1 - active_field
            elif event.key == pygame.K_BACKSPACE and pending is None:
                if active_field == 0:
                    username_input = username_input[:-1]
                else:
                    password_input = password_input[:-1]
            elif event.key == pygame.K_RETURN:
                submit_auth()
        elif game.state == "menu":
            if event.key in (pygame.K_UP, pygame.K_DOWN):
                change = -1 if event.key == pygame.K_UP else 1
                selected_button = (selected_button + change) % len(ui.MENU_BUTTONS)
            elif event.key == pygame.K_RETURN:
                perform_action(tuple(ui.MENU_BUTTONS)[selected_button])
            elif event.key == pygame.K_F9:
                perform_action("load")
        elif game.state == "controls":
            if event.key == pygame.K_RETURN:
                perform_action("menu")
        elif game.state in ("game_over", "win"):
            if event.key == pygame.K_RETURN:
                perform_action("retry")
        elif event.key == pygame.K_p:
            if game.state == "paused":
                perform_action("resume")
            elif game.state == "playing":
                perform_action("pause")
        elif event.key == pygame.K_F5:
            perform_action("save")
        elif event.key == pygame.K_F9 and game.state == "paused":
            perform_action("load")
        elif event.key == pygame.K_SPACE:
            game.launch_ball()
        elif event.key in (pygame.K_LSHIFT, pygame.K_RSHIFT):
            game.activate_slow()


def update_effects(dt):
    if game.state != "playing":
        return
    for particle in particles[:]:
        particle["life"] -= dt
        particle["x"] += particle["vx"] * dt
        particle["y"] += particle["vy"] * dt
        if particle["life"] <= 0:
            particles.remove(particle)
    for x, y, color_index in game.hit_events:
        for _ in range(4):
            particles.append({
                "x": x, "y": y, "vx": random.uniform(-65, 65),
                "vy": random.uniform(-65, 65), "life": 0.25,
                "color": ui.BRICK_COLORS[color_index % len(ui.BRICK_COLORS)],
            })
    if game.ball_attached:
        ball_trail.clear()
    else:
        ball_trail.append((game.ball_x, game.ball_y))
        del ball_trail[:-5]


def update(dt):
    global has_run, score_state
    poll_request()
    if game.state == "menu":
        demo.update(dt)
    ui.update_animations(game.state, selected_button, dt, demo.reset_timer > 0,
                         game_position(pygame.mouse.get_pos()))
    keys = pygame.key.get_pressed()
    direction = int(keys[pygame.K_RIGHT] or keys[pygame.K_d])
    direction -= int(keys[pygame.K_LEFT] or keys[pygame.K_a])
    game.update(dt, direction)
    update_effects(dt)
    if game.state in ("game_over", "win"):
        has_run = False
        if not score_state and api.token and pending is None:
            if begin_request("score", api.send_score, game.score, game.run_id):
                score_state = "pending"


def draw():
    if game.state == "menu":
        ui.draw_menu(screen, selected_button, demo, api.username, has_run)
    elif game.state == "controls":
        ui.draw_controls(screen)
    elif game.state in ("login", "register"):
        ui.draw_auth(screen, game.state, username_input, password_input, active_field, pending is not None)
    else:
        ui.draw_game_background(screen)
        ui.draw_top_bar(screen, game)
        for brick in game.bricks:
            ui.draw_brick(screen, ui.pygame_rect(brick), ui.BRICK_COLORS[brick.color_index % len(ui.BRICK_COLORS)])
        ui.draw_particles(screen, particles)
        ui.draw_paddle(screen, ui.pygame_rect(game.paddle), game.shrink_timer > 0)
        ui.draw_ball(screen, game.ball_x, game.ball_y, BALL_RADIUS, ball_trail, game.slow_timer > 0)
        ui.draw_footer(screen, game)
        if game.ball_attached:
            ui.draw_ready_hint(screen, game.level)
        if game.state in ("paused", "game_over", "win"):
            ui.draw_modal(screen, game.state, game.score, score_state)
    ui.draw_status(screen, status, status_error)


def initialize():
    global screen, clock, running, selected_button, demo, executor
    global pending, pending_action, pending_run_id, has_run, score_state, status, status_error
    global password_input, username_input, active_field, auth_cancelled
    pygame.display.init()
    pygame.font.init()
    pygame.display.set_mode((WIDTH, HEIGHT), pygame.RESIZABLE)
    screen = pygame.Surface((WIDTH, HEIGHT)).convert()
    pygame.display.set_caption("Brickfall")
    clock = pygame.time.Clock()
    ui.initialize_fonts()
    game.start()
    game.state = "menu"
    running = True
    selected_button = 1
    active_field = 0
    has_run = False
    score_state = status = username_input = password_input = ""
    status_error = False
    pending_run_id = None
    auth_cancelled = False
    pygame.key.stop_text_input()
    demo = MenuDemo()
    executor = ThreadPoolExecutor(max_workers=1)
    pending = pending_action = None
    ui.button_progress.clear()
    clear_effects()


def shutdown():
    if executor is not None:
        executor.shutdown(wait=False, cancel_futures=True)
    pygame.quit()


def main():
    initialize()
    try:
        while running:
            dt = min(clock.tick(60) / 1000.0, 1 / 30)
            for event in pygame.event.get():
                handle_event(event)
            if running:
                update(dt)
                draw()
                present()
    finally:
        shutdown()


if __name__ == "__main__":
    main()