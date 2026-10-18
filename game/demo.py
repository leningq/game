import math

from .logic import BALL_RADIUS, Rectangle


class MenuDemo:
    WIDTH, HEIGHT = 360, 362

    def __init__(self):
        self.round_number = 0
        self.reset()

    def reset(self):
        self.round_number += 1
        self.bricks = [
            Rectangle(24 + col * 64, 42 + row * 28, 56, 20, row)
            for row in range(4) for col in range(5)
        ]
        self.paddle = Rectangle(137, 330, 86, 10)
        self.ball_x, self.ball_y = 180.0, 296.0
        self.ball_speed_x = 95.0 if self.round_number % 2 else -95.0
        self.ball_speed_y = -165.0
        self.reset_timer = 0.0
        self.hits = 0

    def bounce(self, brick, old_x, old_y):
        if old_y + BALL_RADIUS <= brick.top:
            self.ball_y = brick.top - BALL_RADIUS - 0.01
            self.ball_speed_y = -abs(self.ball_speed_y)
        elif old_y - BALL_RADIUS >= brick.bottom:
            self.ball_y = brick.bottom + BALL_RADIUS + 0.01
            self.ball_speed_y = abs(self.ball_speed_y)
        elif old_x < brick.centerx:
            self.ball_x = brick.left - BALL_RADIUS - 0.01
            self.ball_speed_x = -abs(self.ball_speed_x)
        else:
            self.ball_x = brick.right + BALL_RADIUS + 0.01
            self.ball_speed_x = abs(self.ball_speed_x)

    def update(self, dt):
        dt = max(0.0, min(dt, 1 / 30))
        if self.reset_timer > 0:
            self.reset_timer -= dt
            if self.reset_timer <= 0:
                self.reset()
            return
        aim_offset = 18 if self.hits % 2 == 0 else -18
        target = self.ball_x + aim_offset
        distance = target - self.paddle.centerx
        self.paddle.x += max(-220 * dt, min(220 * dt, distance))
        self.paddle.x = max(12, min(self.WIDTH - 12 - self.paddle.width, self.paddle.x))

        speed = math.hypot(self.ball_speed_x, self.ball_speed_y)
        steps = max(1, math.ceil(speed * dt / 4))
        for _ in range(steps):
            old_x, old_y = self.ball_x, self.ball_y
            self.ball_x += self.ball_speed_x * dt / steps
            self.ball_y += self.ball_speed_y * dt / steps
            if self.ball_x - BALL_RADIUS < 12:
                self.ball_x = 12 + BALL_RADIUS
                self.ball_speed_x = abs(self.ball_speed_x)
            elif self.ball_x + BALL_RADIUS > self.WIDTH - 12:
                self.ball_x = self.WIDTH - 12 - BALL_RADIUS
                self.ball_speed_x = -abs(self.ball_speed_x)
            if self.ball_y - BALL_RADIUS < 12:
                self.ball_y = 12 + BALL_RADIUS
                self.ball_speed_y = abs(self.ball_speed_y)
            if self.paddle.touches_ball(self.ball_x, self.ball_y) and self.ball_speed_y > 0:
                self.ball_y = self.paddle.top - BALL_RADIUS - 0.01
                angle = (self.ball_x - self.paddle.centerx) / (self.paddle.width / 2) * 0.95
                if abs(angle) < 0.2:
                    angle = 0.2 if self.hits % 2 else -0.2
                self.ball_speed_x = speed * math.sin(angle)
                self.ball_speed_y = -speed * math.cos(angle)
            else:
                for brick in self.bricks[:]:
                    if brick.touches_ball(self.ball_x, self.ball_y):
                        self.bounce(brick, old_x, old_y)
                        self.bricks.remove(brick)
                        self.hits += 1
                        break
            if not self.bricks or self.ball_y - BALL_RADIUS > self.HEIGHT:
                self.reset_timer = 1.25
                return
