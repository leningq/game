import os
from pathlib import Path

import pygame


BG = (13, 20, 26)
PANEL = (20, 29, 36)
LINE = (43, 58, 65)
TEXT = (245, 247, 250)
MUTED = (191, 200, 208)
MINT = (156, 218, 195)
CORAL = (229, 151, 134)
GOLD = (222, 192, 131)
BRICK_COLORS = [MINT, (139, 184, 203), (166, 158, 198), GOLD, CORAL, (131, 184, 163)]
fonts = {}
button_progress = {}
demo_visibility = 1.0
def initialize_fonts():
    font_dir = Path(os.environ.get("WINDIR", "C:/Windows")) / "Fonts"
    for name, size, bold in (
        ("title", 72, True), ("heading", 36, True), ("number", 26, True),
        ("body", 22, False), ("button", 20, True), ("small", 18, False),
        ("tiny", 16, True), ("logo", 18, True),
    ):
        font_file = font_dir / ("segoeuib.ttf" if bold else "segoeui.ttf")
        fallback = pygame.font.match_font("arial,dejavusans", bold=bold)
        fonts[name] = pygame.font.Font(str(font_file) if font_file.is_file() else fallback, size)
        if bold and not font_file.is_file() and fallback is None:
            fonts[name].set_bold(True)


def text(surface, value, pos, size="small", color=TEXT, center=False):
    image = fonts[size].render(str(value), True, color)
    rect = image.get_rect(center=pos) if center else image.get_rect(topleft=pos)
    surface.blit(image, rect)


def pygame_rect(rect):
    return pygame.Rect(round(rect.x), round(rect.y), round(rect.width), round(rect.height))


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


def update_animations(state, selected_button, dt, demo_resetting=False, mouse_pos=None):
    global demo_visibility
    step = min(1.0, max(0.0, dt) / 0.12)
    mouse_pos = pygame.mouse.get_pos() if mouse_pos is None else mouse_pos
    for index, (action, rect) in enumerate(buttons_for_state(state).items()):
        active = rect.collidepoint(mouse_pos)
        active = active or (state == "menu" and selected_button == index)
        key = tuple(rect)
        previous = button_progress.get(key, 0.0)
        button_progress[key] = previous + (float(active) - previous) * step
    target = 0.0 if demo_resetting else 1.0
    demo_visibility += (target - demo_visibility) * min(1.0, dt / 0.2)


def draw_game_background(surface):
    draw_base(surface)
    pygame.draw.rect(surface, PANEL, (24, 18, 852, 68), border_radius=12)
    pygame.draw.rect(surface, LINE, (24, 18, 852, 68), 1, border_radius=12)
    pygame.draw.line(surface, LINE, (24, 96), (876, 96))
    pygame.draw.line(surface, LINE, (24, 96), (24, 556))
    pygame.draw.line(surface, LINE, (876, 96), (876, 556))


MENU_BUTTONS = {action: pygame.Rect(52, 280 + index * 40, 336, 36)
                for index, action in enumerate(("continue", "start", "load", "controls", "account", "exit"))}
PAUSE_BUTTONS = {action: pygame.Rect(286, 270 + index * 50, 328, 40)
                 for index, action in enumerate(("resume", "save", "load", "menu"))}
END_BUTTONS = {
    "retry": pygame.Rect(286, 290, 328, 40),
    "send_score": pygame.Rect(286, 340, 328, 40),
    "menu": pygame.Rect(286, 400, 328, 40),
}
CONTROLS_BUTTONS = {"menu": pygame.Rect(286, 485, 328, 40)}
PLAY_BUTTONS = {"pause": pygame.Rect(748, 30, 108, 40)}
AUTH_FIELDS = [pygame.Rect(280, 222, 340, 42), pygame.Rect(280, 306, 340, 42)]


def buttons_for_state(state):
    if state == "menu":
        return MENU_BUTTONS
    if state == "paused":
        return PAUSE_BUTTONS
    if state in ("game_over", "win"):
        return END_BUTTONS
    if state == "controls":
        return CONTROLS_BUTTONS
    if state == "playing":
        return PLAY_BUTTONS
    if state in ("login", "register"):
        return {
            "auth": pygame.Rect(280, 374, 340, 42),
            "register" if state == "login" else "login": pygame.Rect(280, 427, 340, 38),
            "menu": pygame.Rect(280, 477, 340, 38),
        }
    return {}


def draw_menu(surface, selected_button, demo, username=None, has_run=False):
    surface.fill(BG)
    text(surface, "BRICKFALL / ARCADE", (52, 33), "small", MINT)
    account_label = username or "SIGN IN TO PLAY"
    text(surface, account_label, (848 - fonts["small"].size(account_label)[0], 33), "small", MUTED)
    pygame.draw.line(surface, LINE, (52, 76), (848, 76))
    text(surface, "BRICK", (48, 105), "title")
    text(surface, "FALL", (48, 175), "title")
    text(surface, "Three stages. Keep the ball in play.", (54, 255), "small", MUTED)
    labels = {
        "continue": "Continue run" if has_run else "Continue (no active run)",
        "start": "New game", "load": "Load saved game", "controls": "Controls",
        "account": "Sign out" if username else "Sign in / Register", "exit": "Exit",
    }
    for index, (action, rect) in enumerate(MENU_BUTTONS.items()):
        draw_button(surface, rect, labels[action], selected=index == selected_button)
    frame = pygame.Rect(456, 100, 392, 434)
    pygame.draw.rect(surface, PANEL, frame, border_radius=6)
    pygame.draw.rect(surface, LINE, frame, 1, border_radius=6)
    text(surface, "BRICKFALL / LIVE PREVIEW", (476, 117), "tiny", MUTED)
    scene = pygame.Surface((360, 362))
    scene.fill(PANEL)
    for brick in demo.bricks:
        draw_brick(scene, pygame_rect(brick), BRICK_COLORS[brick.color_index])
    draw_paddle(scene, pygame_rect(demo.paddle))
    draw_ball(scene, demo.ball_x, demo.ball_y, 8, [])
    scene.set_alpha(round(255 * demo_visibility))
    surface.blit(scene, (472, 149))
    text(surface, "UP / DOWN to select   /   ENTER to choose", (52, 545), "small", MUTED)


def draw_top_bar(surface, game):
    text(surface, "SCORE", (44, 22), "tiny", MUTED)
    text(surface, f"{game.score:04d}", (44, 44), "number")
    text(surface, "LEVEL", (300, 22), "tiny", MUTED)
    text(surface, f"{game.level} / 3", (300, 44), "number")
    text(surface, "LIVES", (557, 22), "tiny", MUTED)
    text(surface, str(game.lives), (557, 44), "number")
    draw_button(surface, PLAY_BUTTONS["pause"], "Pause")


def draw_footer(surface, game):
    effects = []
    if game.shrink_timer > 0:
        effects.append(f"Narrow paddle: {game.shrink_timer:.1f}s")
    if game.slow_timer > 0:
        effects.append(f"Slow ball: {game.slow_timer:.1f}s")
    if not effects:
        effects.append("SHIFT: slow used" if game.slow_used else "SHIFT: slow ready")
    text(surface, "   /   ".join(effects), (24, 548), "small", GOLD if game.shrink_timer else MINT)
    text(surface, "Move: arrows / A D     Space: launch     Shift: slow     P / Esc: pause     F5: save", (24, 576), "tiny", MUTED)


def draw_ready_hint(surface, level):
    text(surface, f"LEVEL {level} / READY", (450, 434), "tiny", MUTED, center=True)
    text(surface, "SPACE to launch", (450, 464), "body", MINT, center=True)


def draw_modal(surface, state, score, score_state=""):
    overlay = pygame.Surface((900, 600), pygame.SRCALPHA)
    overlay.fill((5, 10, 14, 220))
    surface.blit(overlay, (0, 0))
    card = pygame.Rect(250, 145, 400, 325)
    pygame.draw.rect(surface, PANEL, card, border_radius=12)
    pygame.draw.rect(surface, LINE, card, 1, border_radius=12)
    title = {"paused": "PAUSED", "win": "VICTORY", "game_over": "GAME OVER"}[state]
    text(surface, title, (450, 190), "heading", center=True)
    subtitle = "Your run is waiting." if state == "paused" else f"Final score: {score}"
    text(surface, subtitle, (450, 230), "body", center=True)
    if state == "paused":
        labels = {"resume": "Continue", "save": "Save game  /  F5", "load": "Load game  /  F9", "menu": "Main menu"}
    else:
        labels = {"retry": "Play again  /  ENTER", "send_score": {
            "saved": "Result saved", "pending": "Sending result...",
            "error": "Retry sending result", "": "Preparing result...",
        }.get(score_state, ""), "menu": "Main menu"}
    for index, (action, rect) in enumerate(buttons_for_state(state).items()):
        draw_button(surface, rect, labels[action], primary=index == 0)


def draw_controls(surface):
    draw_base(surface)
    text(surface, "CONTROLS", (450, 83), "heading", center=True)
    rows = [
        ("ARROWS / A D", "Move the paddle"),
        ("SPACE", "Launch the ball"),
        ("SHIFT", "Slow the ball for 3s, once per level"),
        ("P / ESC", "Pause; P continues, Esc opens menu"),
        ("F5", "Pause and save your current game"),
        ("F9", "Load from menu or pause screen"),
    ]
    for index, (key, description) in enumerate(rows):
        y = 155 + index * 40
        text(surface, key, (140, y), "small", MINT)
        text(surface, description, (315, y), "small")
    text(surface, "Every 5 bricks: a narrower paddle for 3 seconds.", (450, 422), "body", GOLD, center=True)
    text(surface, "10 points per brick. Three lives. Complete all 3 levels to win.", (450, 455), "small", MUTED, center=True)
    draw_button(surface, CONTROLS_BUTTONS["menu"], "Main menu", "ESC")


def draw_auth(surface, state, username, password, active_field, busy):
    draw_base(surface)
    text(surface, "BRICKFALL", (450, 90), "heading", center=True)
    text(surface, "Create account" if state == "register" else "Sign in", (450, 147), "body", center=True)
    for index, (label, value, rect) in enumerate(zip(
            ("Username", "Password"), (username, "*" * len(password)), AUTH_FIELDS)):
        text(surface, label, (rect.x, rect.y - 26), "small", MUTED)
        pygame.draw.rect(surface, PANEL, rect, border_radius=6)
        pygame.draw.rect(surface, MINT if index == active_field else LINE, rect, 1, border_radius=6)
        value += "|" if index == active_field and not busy else ""
        image = fonts["body"].render(value, True, TEXT)
        inner = rect.inflate(-24, -4)
        clip = surface.get_clip()
        surface.set_clip(inner)
        x = min(inner.x, inner.right - image.get_width())
        surface.blit(image, (x, rect.centery - image.get_height() // 2))
        surface.set_clip(clip)
    buttons = buttons_for_state(state)
    draw_button(surface, buttons["auth"], "Connecting..." if busy else "Register" if state == "register" else "Sign in", primary=True)
    switch = "register" if state == "login" else "login"
    draw_button(surface, buttons[switch], "Create an account" if switch == "register" else "Already registered? Sign in")
    draw_button(surface, buttons["menu"], "Main menu", "ESC")


def draw_status(surface, message, error=False):
    if not message:
        return
    width, height = surface.get_size()
    font = fonts["small"]
    lines, line = [], ""
    for word in message.split():
        candidate = (line + " " + word).strip()
        if font.size(candidate)[0] > width - 48 and line:
            lines.append(line)
            line = word
        else:
            line = candidate
    lines.append(line)
    if len(lines) > 2:
        lines[1] = " ".join(lines[1:])
    lines = lines[:2]
    for index, value in enumerate(lines):
        if font.size(value)[0] > width - 48:
            while value and font.size(value + "...")[0] > width - 48:
                value = value[:-1]
            lines[index] = value.rstrip() + "..."
    line_height = font.get_linesize() + 4
    box_height = 12 + len(lines) * line_height
    pygame.draw.rect(surface, BG, (0, height - box_height, width, box_height))
    for index, value in enumerate(lines):
        text(surface, value, (24, height - box_height + 6 + index * line_height),
             "small", CORAL if error else TEXT)
