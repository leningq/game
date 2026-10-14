import math
import random

# Здесь нет Pygame: логика использует только числа и стандартный Python.
WIDTH, HEIGHT = 900, 600
FIELD_LEFT, FIELD_RIGHT = 24, 876
FIELD_TOP, FIELD_BOTTOM = 96, 556
BALL_RADIUS = 8
PADDLE_WIDTH, PADDLE_SMALL_WIDTH = 110, 70
PADDLE_SPEED = 510
BOSS_MAX_HEALTH = 36
DEBUFF_DURATIONS = {"slow": 4.0, "narrow": 4.0, "reverse": 3.0}


class Rectangle:
    # Простой прямоугольник для платформы, кирпичей и корпуса босса.
    def __init__(self, x, y, width, height, color_index=0):
        self.x = float(x)
        self.y = float(y)
        self.width = width
        self.height = height
        self.color_index = color_index

    # Свойства вычисляют границы из координат и размера.
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
        # Ближайшая к центру мяча точка прямоугольника.
        nearest_x = max(self.left, min(self.right, x))
        nearest_y = max(self.top, min(self.bottom, y))
        return (x - nearest_x) ** 2 + (y - nearest_y) ** 2 < BALL_RADIUS ** 2

    def overlaps(self, other, gap=0):
        return (self.left < other.right + gap and self.right > other.left - gap
                and self.top < other.bottom + gap and self.bottom > other.top - gap)


class DebuffDrop(Rectangle):
    # Падающий снаряд хранит тип эффекта и летит в заранее показанную точку.
    def __init__(self, x, y, kind, target_x, speed):
        super().__init__(x - 10, y, 20, 20)
        self.kind = kind
        self.speed_y = speed
        flight_time = max(0.5, (528 - y) / speed)
        self.speed_x = (target_x - x) / flight_time


class Game:
    def __init__(self, seed=None):
        self.random = random.Random(seed)
        self.paddle = Rectangle(395, 528, PADDLE_WIDTH, 12)
        self.boss = Rectangle(362, 144, 176, 152)
        self.hit_events = []
        self.start()
        self.state = "menu"

    def start(self, boss_test=False):
        # Новая попытка полностью сбрасывает счёт и уровни.
        self.score = 0
        self.lives = 3
        self.boss_test = boss_test
        self.level = 4 if boss_test else 1
        self.paused_state = "playing"
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
        # Сохраняем центр при сужении; после расширения проверяем края.
        center = self.paddle.centerx
        self.paddle.width = width
        self.paddle.x = max(FIELD_LEFT, min(FIELD_RIGHT - width, center - width / 2))

    def attach_ball(self):
        self.ball_x = self.paddle.centerx
        self.ball_y = self.paddle.top - BALL_RADIUS - 2

    def reset_ball(self):
        # После потери жизни мяч ждёт Space; эффекты платформы снимаются.
        self.debuff_timers = {kind: 0.0 for kind in DEBUFF_DURATIONS}
        self.debuff_guard_timer = 1.0
        self.drops.clear()
        self.warning_timer = 0.0
        self.boss_attack_timer = self.boss_attack_interval
        self.paddle.width = PADDLE_WIDTH
        self.paddle.x = (WIDTH - PADDLE_WIDTH) / 2
        self.shrink_timer = 0.0
        self.slow_timer = 0.0
        self.ball_attached = True
        self.ball_speed_x = 0.0
        self.ball_speed_y = 0.0
        self.attach_ball()
        # slow_used не сбрасывается: заряд остаётся один на весь уровень.

    def prepare_level(self):
        self.bricks = self.create_bricks() if self.level <= 3 else []
        self.destroyed_bricks = 0
        self.slow_used = False
        self.boss.x = (WIDTH - self.boss.width) / 2
        self.boss_direction = 1
        self.boss_health = BOSS_MAX_HEALTH
        self.boss_hit_timer = 0.0
        self.boss_direction_timer = 4.5
        self.boss_time = 0.0
        self.attack_number = 0
        self.attack_kind = "slow"
        self.attack_target_x = WIDTH / 2
        self.drops = []
        self.defeat_timer = 0.0
        self.reset_ball()

    def next_level(self):
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
        # Shift расходуется только при полёте, один раз за уровень.
        if self.state == "playing" and not self.ball_attached and not self.slow_used:
            self.slow_used = True
            self.slow_timer = 3.0

    def toggle_pause(self):
        if self.state in ("playing", "boss_defeated"):
            self.paused_state = self.state
            self.state = "paused"
        elif self.state == "paused":
            self.state = self.paused_state

    @property
    def boss_phase(self):
        return 1 if self.boss_health > BOSS_MAX_HEALTH / 2 else 2

    @property
    def boss_attack_interval(self):
        return 6.5 if self.boss_phase == 1 else 4.6

    def boss_parts(self):
        # Несколько прямоугольников повторяют силуэт: между руками и ногами пусто.
        x, y = self.boss.x, self.boss.y
        return [
            Rectangle(x + 44, y, 88, 44),       # голова
            Rectangle(x + 36, y + 48, 104, 76), # броня корпуса
            Rectangle(x, y + 48, 32, 80),       # левая рука
            Rectangle(x + 144, y + 48, 32, 80), # правая рука
            Rectangle(x + 44, y + 128, 28, 24), # левая нога
            Rectangle(x + 100, y + 128, 28, 24),# правая нога
        ]

    def boss_weak_point(self):
        # Ядро выступает из нижней части корпуса: его можно атаковать снизу.
        return Rectangle(self.boss.x + 76, self.boss.y + 112, 24, 32)

    def sync_paddle_width(self):
        # Два разных источника сужения не уменьшают ширину дважды.
        narrow = self.shrink_timer > 0 or self.debuff_timers["narrow"] > 0
        width = PADDLE_SMALL_WIDTH if narrow else PADDLE_WIDTH
        if self.paddle.width != width:
            self.resize_paddle(width)

    def apply_debuff(self, kind):
        # Повторное попадание не продлевает тот же эффект.
        if self.debuff_timers[kind] > 0 or self.debuff_guard_timer > 0:
            return False
        self.debuff_timers[kind] = DEBUFF_DURATIONS[kind]
        self.debuff_guard_timer = 0.9
        self.sync_paddle_width()
        return True

    def update_drops(self, dt):
        for drop in self.drops[:]:
            drop.x += drop.speed_x * dt
            drop.y += drop.speed_y * dt
            if drop.overlaps(self.paddle):
                self.apply_debuff(drop.kind)
                self.drops.remove(drop)
            elif drop.top > FIELD_BOTTOM:
                self.drops.remove(drop)

    def update_boss(self, dt):
        self.boss_time += dt
        speed = 125 if self.boss_phase == 1 else 175
        self.boss.x += self.boss_direction * speed * dt
        if self.boss.left <= FIELD_LEFT + 18:
            self.boss.x = FIELD_LEFT + 18
            self.boss_direction = 1
        elif self.boss.right >= FIELD_RIGHT - 18:
            self.boss.x = FIELD_RIGHT - 18 - self.boss.width
            self.boss_direction = -1
        self.boss_direction_timer -= dt
        if self.boss_direction_timer <= 0:
            self.boss_direction *= -1
            self.boss_direction_timer = self.random.uniform(3.5, 5.5)
        self.boss_hit_timer = max(0.0, self.boss_hit_timer - dt)

        if self.warning_timer > 0:
            self.warning_timer = max(0.0, self.warning_timer - dt)
            if self.warning_timer < 0.000001:
                self.warning_timer = 0.0
                speed = 150 if self.boss_phase == 1 else 170
                self.drops.append(DebuffDrop(
                    self.boss.centerx, self.boss.bottom + 4,
                    self.attack_kind, self.attack_target_x, speed,
                ))
                self.boss_attack_timer = self.boss_attack_interval
        else:
            self.boss_attack_timer = min(self.boss_attack_timer, self.boss_attack_interval) - dt
            if self.boss_attack_timer <= 0:
                # Типы чередуются, а цель фиксируется до выстрела: можно увернуться.
                self.attack_kind = ("slow", "narrow", "reverse")[self.attack_number % 3]
                self.attack_number += 1
                self.attack_target_x = self.paddle.centerx
                self.warning_timer = 1.0 if self.boss_phase == 1 else 0.85

    def bounce_off_rect(self, rect, old_x, old_y):
        # Выбираем сторону удара по прошлому положению мяча.
        if old_y + BALL_RADIUS <= rect.top:
            side = 0
        elif old_y - BALL_RADIUS >= rect.bottom:
            side = 1
        elif old_x + BALL_RADIUS <= rect.left:
            side = 2
        elif old_x - BALL_RADIUS >= rect.right:
            side = 3
        else:
            # Босс может сам коснуться мяча: выбираем ближайшую границу.
            distances = (
                abs(self.ball_y + BALL_RADIUS - rect.top),
                abs(rect.bottom - self.ball_y + BALL_RADIUS),
                abs(self.ball_x + BALL_RADIUS - rect.left),
                abs(rect.right - self.ball_x + BALL_RADIUS),
            )
            side = distances.index(min(distances))
        # Маленький зазор предотвращает повторный контакт с той же гранью.
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

    def damage_boss(self, weak_hit=False):
        if self.boss_hit_timer > 0:
            return
        damage = 2 if weak_hit else 1
        self.boss_health = max(0, self.boss_health - damage)
        self.boss_hit_timer = 0.55
        self.score += 50 * damage
        self.hit_events.append((self.ball_x, self.ball_y, 3 if weak_hit else 4))
        if self.boss_health <= 0:
            self.score += 500
            self.state = "boss_defeated"
            self.defeat_timer = 1.8
            self.drops.clear()
            self.warning_timer = 0.0
            self.debuff_timers = {kind: 0.0 for kind in DEBUFF_DURATIONS}
            self.shrink_timer = 0.0
            self.sync_paddle_width()

    def hit_boss(self, old_x, old_y):
        # Проверяем ядро первым, иначе броня могла бы закрыть слабое место.
        weak_point = self.boss_weak_point()
        if weak_point.touches_ball(self.ball_x, self.ball_y):
            self.bounce_off_rect(weak_point, old_x, old_y)
            self.damage_boss(weak_hit=True)
            return True
        for part in self.boss_parts():
            if part.touches_ball(self.ball_x, self.ball_y):
                self.bounce_off_rect(part, old_x, old_y)
                self.damage_boss()
                return True
        return False

    def break_brick(self, brick):
        self.bricks.remove(brick)
        self.score += 10
        self.destroyed_bricks += 1
        # Клиент получит координаты удара и самостоятельно нарисует частицы.
        self.hit_events.append((brick.centerx, brick.centery, brick.color_index))
        if self.destroyed_bricks % 5 == 0:
            self.resize_paddle(PADDLE_SMALL_WIDTH)
            self.shrink_timer = 3.0

    def move_ball(self, dt):
        speed = math.hypot(self.ball_speed_x, self.ball_speed_y)
        multiplier = 0.55 if self.slow_timer > 0 else 1.0
        # Маленькие шаги не дают быстрому мячу пролететь сквозь кирпич.
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
                # Точка удара задаёт угол: общая скорость сохраняется
                hit_position = (self.ball_x - self.paddle.centerx) / (self.paddle.width / 2)
                angle = max(-1.0, min(1.0, hit_position)) * math.radians(62)
                self.ball_speed_x = speed * math.sin(angle)
                self.ball_speed_y = -speed * math.cos(angle)
            elif self.level == 4 and self.hit_boss(old_x, old_y):
                if self.state == "boss_defeated":
                    return
            else:
                for brick in self.bricks[:]:
                    if brick.touches_ball(self.ball_x, self.ball_y):
                        self.bounce_off_rect(brick, old_x, old_y)
                        self.break_brick(brick)
                        break

            if self.ball_y - BALL_RADIUS > FIELD_BOTTOM:
                self.lives -= 1
                if self.lives <= 0:
                    self.state = "game_over"
                else:
                    self.reset_ball()
                return
            if self.level <= 3 and not self.bricks:
                self.next_level()
                return

    def update(self, dt, direction=0):
        self.hit_events.clear()
        # Финал имеет собственный короткий таймер; пауза останавливает и его.
        dt = max(0.0, min(dt, 1 / 30))
        if self.state == "boss_defeated":
            self.defeat_timer = max(0.0, self.defeat_timer - dt)
            if self.defeat_timer < 0.000001:
                self.defeat_timer = 0.0
                self.state = "win"
            return
        if self.state != "playing":
            return
        # Клиент передаёт секунды и направление: -1, 0 или 1.
        # При подвисании не пытаемся проиграть целую секунду за один кадр.
        dt = max(0.0, min(dt, 1 / 30))
        if dt == 0:
            return
        for kind in self.debuff_timers:
            self.debuff_timers[kind] = max(0.0, self.debuff_timers[kind] - dt)
        self.debuff_guard_timer = max(0.0, self.debuff_guard_timer - dt)
        if self.debuff_timers["reverse"] > 0:
            direction *= -1
        paddle_speed = PADDLE_SPEED * (0.55 if self.debuff_timers["slow"] > 0 else 1.0)
        self.paddle.x += max(-1, min(1, direction)) * paddle_speed * dt
        self.paddle.x = max(FIELD_LEFT, min(FIELD_RIGHT - self.paddle.width, self.paddle.x))
        if self.shrink_timer > 0:
            self.shrink_timer = max(0.0, self.shrink_timer - dt)
            if self.shrink_timer < 0.000001:
                self.shrink_timer = 0.0
                self.sync_paddle_width()
        self.slow_timer = max(0.0, self.slow_timer - dt)
        if self.slow_timer < 0.000001:
            self.slow_timer = 0.0
        self.sync_paddle_width()
        if self.ball_attached:
            self.attach_ball()
            return
        if self.level == 4:
            self.update_boss(dt)
            self.update_drops(dt)
        self.move_ball(dt)
