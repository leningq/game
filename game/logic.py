import math
import re
import uuid

# Логика игры использует только стандартный Python, без Pygame.
WIDTH, HEIGHT = 900, 600
FIELD_LEFT, FIELD_RIGHT = 24, 876
FIELD_TOP, FIELD_BOTTOM = 96, 556
BALL_RADIUS = 8
PADDLE_WIDTH, PADDLE_SMALL_WIDTH = 110, 70
PADDLE_SPEED = 510
LEVEL_BRICK_COUNTS = (40, 48, 54)
MAX_SCORE = sum(LEVEL_BRICK_COUNTS) * 10


class Rectangle:
    def __init__(self, x, y, width, height, color_index=0):
        self.x, self.y = float(x), float(y)
        self.width, self.height = width, height
        self.color_index = color_index

    @property
    def left(self):
        return self.x

    @property
    def right(self):
        return self.x + self.width

    @property
    def top(self):
        return self.y

    @property
    def bottom(self):
        return self.y + self.height

    @property
    def centerx(self):
        return self.x + self.width / 2

    @property
    def centery(self):
        return self.y + self.height / 2

    def touches_ball(self, x, y):
        # Проверяем расстояние до ближайшей точки прямоугольника.
        nearest_x = max(self.left, min(self.right, x))
        nearest_y = max(self.top, min(self.bottom, y))
        return (x - nearest_x) ** 2 + (y - nearest_y) ** 2 < BALL_RADIUS ** 2

class Game:
    def __init__(self):
        self.paddle = Rectangle(395, 528, PADDLE_WIDTH, 12)
        self.hit_events = []
        self.start()
        self.state = "menu"

    def start(self):
        # Новая попытка получает отдельный идентификатор для результата.
        self.run_id = uuid.uuid4().hex
        self.score = 0
        self.lives = 3
        self.level = 1
        self.destroyed_bricks = 0
        self.state = "playing"
        self.hit_events.clear()
        self.prepare_level()

    def create_bricks(self):
        bricks = []
        for row in range(3 + self.level):
            for col in range(10):
                if self.level == 2 and row == 2 and col in (4, 5):
                    continue
                if self.level == 3 and row % 2 == 1 and col in (0, 9):
                    continue
                bricks.append(Rectangle(45 + col * 82, 132 + row * 34, 72, 24, row))
        return bricks

    def resize_paddle(self, width):
        center = self.paddle.centerx
        self.paddle.width = width
        self.paddle.x = max(FIELD_LEFT, min(FIELD_RIGHT - width, center - width / 2))

    def attach_ball(self):
        self.ball_x = self.paddle.centerx
        self.ball_y = self.paddle.top - BALL_RADIUS - 2

    def reset_ball(self):
        # Потеря жизни снимает эффекты, но не возвращает заряд Shift.
        self.paddle.width = PADDLE_WIDTH
        self.paddle.x = (WIDTH - PADDLE_WIDTH) / 2
        self.shrink_timer = 0.0
        self.slow_timer = 0.0
        self.ball_attached = True
        self.ball_speed_x = self.ball_speed_y = 0.0
        self.attach_ball()

    def prepare_level(self):
        self.bricks = self.create_bricks()
        self.slow_used = False
        self.reset_ball()

    def next_level(self):
        if self.level == 3:
            self.state = "win"
        else:
            self.level += 1
            self.prepare_level()

    def launch_ball(self):
        if self.state != "playing" or not self.ball_attached:
            return
        self.ball_attached = False
        speed = 360 + (self.level - 1) * 40
        self.ball_speed_x = speed * 0.42
        self.ball_speed_y = -math.sqrt(speed ** 2 - self.ball_speed_x ** 2)

    def activate_slow(self):
        if self.state == "playing" and not self.ball_attached and not self.slow_used:
            self.slow_used = True
            self.slow_timer = 3.0

    def toggle_pause(self):
        if self.state == "playing":
            self.state = "paused"
        elif self.state == "paused":
            self.state = "playing"

    def sync_paddle_width(self):
        width = PADDLE_SMALL_WIDTH if self.shrink_timer > 0 else PADDLE_WIDTH
        if self.paddle.width != width:
            self.resize_paddle(width)

    def bounce_off_rect(self, rect, old_x, old_y):
        # Предыдущее положение определяет грань удара.
        if old_y + BALL_RADIUS <= rect.top:
            side = 0
        elif old_y - BALL_RADIUS >= rect.bottom:
            side = 1
        elif old_x + BALL_RADIUS <= rect.left:
            side = 2
        elif old_x - BALL_RADIUS >= rect.right:
            side = 3
        else:
            distances = (abs(self.ball_y + BALL_RADIUS - rect.top),
                         abs(rect.bottom - self.ball_y + BALL_RADIUS),
                         abs(self.ball_x + BALL_RADIUS - rect.left),
                         abs(rect.right - self.ball_x + BALL_RADIUS))
            side = distances.index(min(distances))
        # Зазор не позволяет мячу застрять и повторно ударить ту же грань.
        if side == 0:
            self.ball_y = rect.top - BALL_RADIUS - 0.01
            self.ball_speed_y = -abs(self.ball_speed_y)
        elif side == 1:
            self.ball_y = rect.bottom + BALL_RADIUS + 0.01
            self.ball_speed_y = abs(self.ball_speed_y)
        elif side == 2:
            self.ball_x = rect.left - BALL_RADIUS - 0.01
            self.ball_speed_x = -abs(self.ball_speed_x)
        else:
            self.ball_x = rect.right + BALL_RADIUS + 0.01
            self.ball_speed_x = abs(self.ball_speed_x)

    def break_brick(self, brick):
        if brick not in self.bricks:
            return
        self.bricks.remove(brick)
        self.score += 10
        self.destroyed_bricks += 1
        self.hit_events.append((brick.centerx, brick.centery, brick.color_index))
        if self.destroyed_bricks % 5 == 0:
            self.shrink_timer = 3.0
            self.sync_paddle_width()

    def move_ball(self, dt):
        speed = math.hypot(self.ball_speed_x, self.ball_speed_y)
        multiplier = 0.55 if self.slow_timer > 0 else 1.0
        # Малые шаги предотвращают пролёт сквозь тонкие кирпичи.
        steps = max(1, math.ceil(speed * dt / (BALL_RADIUS * 0.75)))
        step_time = dt / steps
        for _ in range(steps):
            old_x, old_y = self.ball_x, self.ball_y
            self.ball_x += self.ball_speed_x * multiplier * step_time
            self.ball_y += self.ball_speed_y * multiplier * step_time
            if self.ball_x - BALL_RADIUS <= FIELD_LEFT:
                self.ball_x = FIELD_LEFT + BALL_RADIUS
                self.ball_speed_x = abs(self.ball_speed_x)
            elif self.ball_x + BALL_RADIUS >= FIELD_RIGHT:
                self.ball_x = FIELD_RIGHT - BALL_RADIUS
                self.ball_speed_x = -abs(self.ball_speed_x)
            if self.ball_y - BALL_RADIUS <= FIELD_TOP:
                self.ball_y = FIELD_TOP + BALL_RADIUS
                self.ball_speed_y = abs(self.ball_speed_y)
            if (self.paddle.touches_ball(self.ball_x, self.ball_y)
                    and self.ball_speed_y > 0 and old_y < self.paddle.top):
                self.ball_y = self.paddle.top - BALL_RADIUS - 0.01
                hit_position = (self.ball_x - self.paddle.centerx) / (self.paddle.width / 2)
                angle = max(-1.0, min(1.0, hit_position)) * math.radians(62)
                self.ball_speed_x = speed * math.sin(angle)
                self.ball_speed_y = -speed * math.cos(angle)
            else:
                # За один шаг отражаем мяч только от одного кирпича.
                for brick in self.bricks:
                    if brick.touches_ball(self.ball_x, self.ball_y):
                        self.bounce_off_rect(brick, old_x, old_y)
                        self.break_brick(brick)
                        break
            if self.ball_y - BALL_RADIUS > FIELD_BOTTOM:
                self.lives -= 1
                if self.lives == 0:
                    self.state = "game_over"
                else:
                    self.reset_ball()
                return
            if not self.bricks:
                self.next_level()
                return

    def update(self, dt, direction=0):
        self.hit_events.clear()
        if self.state != "playing":
            return
        # Ограничиваем кадр после подвисания окна.
        dt = max(0.0, min(dt, 1 / 30))
        if dt == 0:
            return
        self.paddle.x += max(-1, min(1, direction)) * PADDLE_SPEED * dt
        self.paddle.x = max(FIELD_LEFT, min(FIELD_RIGHT - self.paddle.width, self.paddle.x))
        self.shrink_timer = max(0.0, self.shrink_timer - dt)
        self.slow_timer = max(0.0, self.slow_timer - dt)
        if self.shrink_timer < 0.000001:
            self.shrink_timer = 0.0
        if self.slow_timer < 0.000001:
            self.slow_timer = 0.0
        self.sync_paddle_width()
        if self.ball_attached:
            self.attach_ball()
        else:
            self.move_ball(dt)

    def to_dict(self):
        # Храним индексы исходного уровня, а не произвольные прямоугольники.
        if self.state not in ("playing", "paused"):
            raise ValueError("Only unfinished games can be saved")
        layout = self.create_bricks()
        positions = {(brick.x, brick.y): index for index, brick in enumerate(layout)}
        return {
            "version": 1, "state": self.state, "run_id": self.run_id,
            "level": self.level, "score": self.score, "lives": self.lives,
            "destroyed_bricks": self.destroyed_bricks,
            "bricks": [positions[(brick.x, brick.y)] for brick in self.bricks],
            "paddle": {"x": self.paddle.x, "width": self.paddle.width},
            "ball": {"x": self.ball_x, "y": self.ball_y,
                     "speed_x": self.ball_speed_x, "speed_y": self.ball_speed_y,
                     "attached": self.ball_attached},
            "slow_used": self.slow_used, "slow_timer": self.slow_timer,
            "shrink_timer": self.shrink_timer,
        }

    @classmethod
    def from_dict(cls, data):
        # Сервер и клиент одинаково проверяют загруженную партию.
        def fields(value, expected):
            if not isinstance(value, dict) or set(value) != set(expected.split()):
                raise ValueError("Invalid save fields")

        def integer(value, low, high):
            if type(value) is not int or not low <= value <= high:
                raise ValueError("Invalid integer in save")
            return value

        def number(value, low, high):
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or not low <= value <= high):
                raise ValueError("Invalid number in save")
            return float(value)

        fields(data, "version state run_id level score lives destroyed_bricks bricks paddle ball slow_used slow_timer shrink_timer")
        integer(data["version"], 1, 1)
        if data["state"] not in ("playing", "paused"):
            raise ValueError("Only unfinished games can be loaded")
        if not isinstance(data["run_id"], str) or not re.fullmatch(r"[0-9a-f]{32}", data["run_id"]):
            raise ValueError("Invalid run identifier")
        game = cls()
        game.run_id = data["run_id"]
        game.level = integer(data["level"], 1, 3)
        game.lives = integer(data["lives"], 1, 3)
        game.score = integer(data["score"], 0, MAX_SCORE - 10)
        game.destroyed_bricks = integer(data["destroyed_bricks"], 0, MAX_SCORE // 10 - 1)
        layout = game.create_bricks()
        indices = data["bricks"]
        if not isinstance(indices, list) or not 1 <= len(indices) <= len(layout):
            raise ValueError("Invalid brick list")
        for index in indices:
            integer(index, 0, len(layout) - 1)
        if len(set(indices)) != len(indices):
            raise ValueError("Repeated brick index")
        destroyed = sum(LEVEL_BRICK_COUNTS[:game.level - 1]) + len(layout) - len(indices)
        if game.destroyed_bricks != destroyed or game.score != destroyed * 10:
            raise ValueError("Score and bricks do not agree")
        game.bricks = [layout[index] for index in indices]
        if type(data["slow_used"]) is not bool:
            raise ValueError("Invalid slow charge")
        game.slow_used = data["slow_used"]
        game.slow_timer = number(data["slow_timer"], 0, 3)
        game.shrink_timer = number(data["shrink_timer"], 0, 3)
        if game.slow_timer > 0 and not game.slow_used:
            raise ValueError("Slow effect requires a spent charge")
        if game.shrink_timer > 0 and game.destroyed_bricks < 5:
            raise ValueError("Shrink effect requires five destroyed bricks")
        fields(data["paddle"], "x width")
        width = PADDLE_SMALL_WIDTH if game.shrink_timer > 0 else PADDLE_WIDTH
        integer(data["paddle"]["width"], width, width)
        game.paddle.width = width
        game.paddle.x = number(data["paddle"]["x"], FIELD_LEFT, FIELD_RIGHT - width)
        fields(data["ball"], "x y speed_x speed_y attached")
        ball = data["ball"]
        if type(ball["attached"]) is not bool:
            raise ValueError("Invalid attached flag")
        game.ball_attached = ball["attached"]
        game.ball_x = number(ball["x"], FIELD_LEFT + BALL_RADIUS, FIELD_RIGHT - BALL_RADIUS)
        game.ball_y = number(ball["y"], FIELD_TOP + BALL_RADIUS, FIELD_BOTTOM + BALL_RADIUS)
        speed = 360 + (game.level - 1) * 40
        game.ball_speed_x = number(ball["speed_x"], -speed, speed)
        game.ball_speed_y = number(ball["speed_y"], -speed, speed)
        if game.ball_attached:
            if (game.ball_speed_x != 0 or game.ball_speed_y != 0 or game.slow_timer != 0
                    or not math.isclose(game.ball_x, game.paddle.centerx, abs_tol=0.000001)
                    or not math.isclose(game.ball_y, game.paddle.top - BALL_RADIUS - 2, abs_tol=0.000001)):
                raise ValueError("Invalid attached ball")
        elif not math.isclose(math.hypot(game.ball_speed_x, game.ball_speed_y), speed, abs_tol=0.000001):
            raise ValueError("Invalid ball speed")
        game.state = "paused"
        game.hit_events.clear()
        return game
