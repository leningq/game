import math
import unittest

from game.logic import (
    Game, Rectangle, BALL_RADIUS, FIELD_LEFT, FIELD_RIGHT, FIELD_BOTTOM,
    PADDLE_WIDTH, PADDLE_SMALL_WIDTH, BOSS_MAX_HEALTH, DebuffDrop,
)


class BrickfallTests(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.start()

    def test_launch_life_loss_and_slow_charge(self):
        game = self.game
        game.update(1 / 60, direction=1)
        self.assertEqual(game.ball_x, game.paddle.centerx)
        self.assertTrue(game.ball_attached)
        game.activate_slow()
        self.assertFalse(game.slow_used)
        game.launch_ball()
        self.assertLess(game.ball_speed_y, 0)
        game.activate_slow()
        self.assertEqual(game.slow_timer, 3)
        game.update(1 / 60)
        remaining = game.slow_timer
        game.activate_slow()
        self.assertEqual(game.slow_timer, remaining)
        game.ball_y = FIELD_BOTTOM + BALL_RADIUS + 3
        game.ball_speed_y = 300
        game.update(1 / 60)
        self.assertEqual(game.lives, 2)
        self.assertTrue(game.ball_attached)
        self.assertEqual(game.ball_speed_y, 0)
        self.assertEqual(game.slow_timer, 0)
        self.assertTrue(game.slow_used)
        game.update(1 / 60, direction=-1)
        self.assertEqual(game.ball_x, game.paddle.centerx)

    def test_shrink_and_slow_last_three_seconds(self):
        game = self.game
        for brick in game.bricks[:5]:
            game.break_brick(brick)
        self.assertEqual(game.paddle.width, PADDLE_SMALL_WIDTH)
        self.assertEqual(game.shrink_timer, 3)
        game.paddle.x = FIELD_RIGHT - game.paddle.width
        for _ in range(180):
            game.update(1 / 60)
        self.assertEqual(game.paddle.width, PADDLE_WIDTH)
        self.assertEqual(game.shrink_timer, 0)
        self.assertLessEqual(game.paddle.right, FIELD_RIGHT)

        game.launch_ball()
        game.activate_slow()
        # Следим за таймером на безопасной горизонтальной траектории.
        game.ball_y = 400
        game.ball_speed_x, game.ball_speed_y = 150, 0
        for _ in range(90):
            game.update(1 / 30)
        self.assertAlmostEqual(game.slow_timer, 0, places=6)
        self.assertTrue(game.slow_used)

    def test_collisions_and_paddle_angle(self):
        game = self.game
        game.launch_ball()
        game.bricks = [Rectangle(400, 300, 72, 24), Rectangle(650, 200, 72, 24)]
        game.ball_x, game.ball_y = 430, 350
        game.ball_speed_x, game.ball_speed_y = 0, -1500
        game.update(1 / 30)
        self.assertGreater(game.ball_speed_y, 0)
        self.assertEqual(game.score, 10)
        game.ball_x = game.paddle.centerx + 35
        game.ball_y = game.paddle.top - BALL_RADIUS - 1
        game.ball_speed_x, game.ball_speed_y = 0, 400
        game.update(1 / 60)
        self.assertLess(game.ball_speed_y, 0)
        self.assertGreater(game.ball_speed_x, 0)
        self.assertAlmostEqual(math.hypot(game.ball_speed_x, game.ball_speed_y), 400)

    def test_three_levels_then_boss(self):
        game = self.game
        for expected_level in (2, 3, 4):
            game.bricks = [Rectangle(400, 300, 72, 24)]
            game.launch_ball()
            game.activate_slow()
            game.ball_x, game.ball_y = 430, 335
            game.ball_speed_x, game.ball_speed_y = 0, -400
            game.update(1 / 30)
            self.assertEqual(game.level, expected_level)
            self.assertTrue(game.ball_attached)
            self.assertFalse(game.slow_used)
        self.assertEqual(game.score, 30)
        self.assertEqual(game.boss_health, BOSS_MAX_HEALTH)
        game.launch_ball()
        game.update(1 / 60)
        self.assertEqual(game.state, "playing")

    def test_boss_phases_weak_point_pause_and_victory(self):
        game = self.game
        game.start(boss_test=True)
        waiting_x = game.boss.x
        game.update(1 / 30)
        self.assertEqual(game.boss.x, waiting_x)
        game.launch_ball()
        game.boss_attack_timer = 0
        game.update(1 / 60)
        self.assertGreater(game.warning_timer, 0)
        self.assertEqual(len(game.drops), 0)
        for _ in range(61):
            game.update(1 / 60)
        self.assertEqual(len(game.drops), 1)
        game.drops.clear()
        # Изолируем прицельный удар от случайного попадания во время предупреждения.
        game.boss_health = BOSS_MAX_HEALTH
        game.score = 0
        game.boss_hit_timer = 0

        def hit_core():
            weak = game.boss_weak_point()
            game.ball_x = weak.centerx
            game.ball_y = weak.bottom + BALL_RADIUS + 1
            game.ball_speed_x, game.ball_speed_y = 0, -400
            game.move_ball(1 / 60)

        hit_core()
        self.assertEqual(game.boss_health, BOSS_MAX_HEALTH - 2)
        self.assertEqual(game.score, 100)
        hit_core()
        self.assertEqual(game.boss_health, BOSS_MAX_HEALTH - 2)
        game.activate_slow()
        game.toggle_pause()
        before = (game.boss.x, game.boss_attack_timer, game.ball_y, game.slow_timer)
        game.update(1 / 30, direction=1)
        self.assertEqual(before, (game.boss.x, game.boss_attack_timer, game.ball_y, game.slow_timer))
        game.toggle_pause()
        game.reset_ball()
        self.assertEqual(game.boss_health, BOSS_MAX_HEALTH - 2)
        game.boss_health = BOSS_MAX_HEALTH // 2
        self.assertEqual(game.boss_phase, 2)
        self.assertLess(game.boss_attack_interval, 6.5)
        game.launch_ball()
        game.boss_health = 1
        game.boss_hit_timer = 0
        hit_core()
        self.assertEqual(game.state, "boss_defeated")
        self.assertEqual(game.boss_health, 0)
        self.assertEqual(game.score, 700)
        game.toggle_pause()
        timer = game.defeat_timer
        game.update(1 / 30)
        self.assertEqual(game.defeat_timer, timer)
        game.toggle_pause()
        for _ in range(108):
            game.update(1 / 60)
        self.assertEqual(game.state, "win")

    def test_all_three_drops_apply_and_do_not_extend(self):
        for kind in ("slow", "narrow", "reverse"):
            with self.subTest(kind=kind):
                game = Game(seed=2)
                game.start(boss_test=True)
                game.launch_ball()
                game.debuff_guard_timer = 0
                game.drops.append(DebuffDrop(
                    game.paddle.centerx, game.paddle.top - 21,
                    kind, game.paddle.centerx, 150,
                ))
                game.update_drops(1 / 30)
                self.assertGreater(game.debuff_timers[kind], 0)
                self.assertEqual(game.drops, [])
                before = game.paddle.x
                game.update(1 / 60, direction=1)
                movement = game.paddle.x - before
                if kind == "slow":
                    self.assertAlmostEqual(movement, 510 * 0.55 / 60)
                elif kind == "reverse":
                    self.assertLess(movement, 0)
                else:
                    self.assertEqual(game.paddle.width, PADDLE_SMALL_WIDTH)
                timer = game.debuff_timers[kind]
                game.debuff_guard_timer = 0
                self.assertFalse(game.apply_debuff(kind))
                self.assertEqual(timer, game.debuff_timers[kind])
                game.reset_ball()
                self.assertTrue(all(value == 0 for value in game.debuff_timers.values()))
                self.assertEqual(game.paddle.width, PADDLE_WIDTH)
                self.assertTrue(game.ball_attached)

    def test_narrow_sources_do_not_stack_or_expire_early(self):
        game = self.game
        for brick in game.bricks[:5]:
            game.break_brick(brick)
        game.debuff_guard_timer = 0
        game.apply_debuff("narrow")
        for _ in range(180):
            game.update(1 / 60)
        self.assertEqual(game.shrink_timer, 0)
        self.assertGreater(game.debuff_timers["narrow"], 0)
        self.assertEqual(game.paddle.width, PADDLE_SMALL_WIDTH)
        for _ in range(61):
            game.update(1 / 60)
        self.assertEqual(game.paddle.width, PADDLE_WIDTH)

    def test_warning_cycles_and_drops_can_be_dodged(self):
        game = Game(seed=3)
        game.start(boss_test=True)
        game.launch_ball()
        game.ball_y = 400
        game.ball_speed_x, game.ball_speed_y = 120, 0
        for kind in ("slow", "narrow", "reverse"):
            game.boss_attack_timer = 0
            game.update(1 / 60)
            target = game.attack_target_x
            self.assertEqual(game.attack_kind, kind)
            self.assertEqual(game.drops, [])
            # Уходим с отмеченной позиции ещё до выстрела.
            game.paddle.x = FIELD_LEFT if target > 400 else FIELD_RIGHT - game.paddle.width
            for _ in range(61):
                game.update(1 / 60)
            self.assertEqual(game.drops[0].kind, kind)
            self.assertEqual(game.attack_target_x, target)
            for _ in range(180):
                game.update(1 / 60)
            self.assertEqual(game.drops, [])
            self.assertTrue(all(value == 0 for value in game.debuff_timers.values()))

    def test_menu_demo_collisions_and_reset(self):
        from game.demo import MenuDemo
        demo = MenuDemo()
        count = len(demo.bricks)
        for _ in range(180):
            demo.update(1 / 60)
        self.assertLess(len(demo.bricks), count)
        self.assertGreater(demo.hits, 0)
        # Последний кирпич и последующее восстановление сцены.
        demo.bricks = [Rectangle(150, 150, 56, 20)]
        demo.ball_x, demo.ball_y = 176, 180
        demo.ball_speed_x, demo.ball_speed_y = 0, -165
        for _ in range(30):
            demo.update(1 / 60)
        self.assertGreater(demo.reset_timer, 0)
        for _ in range(90):
            demo.update(1 / 60)
        self.assertEqual(len(demo.bricks), 20)

    def test_game_over_and_restart(self):
        game = self.game
        for remaining in (2, 1, 0):
            game.launch_ball()
            game.ball_y = FIELD_BOTTOM + BALL_RADIUS + 3
            game.ball_speed_y = 300
            game.update(1 / 60)
            self.assertEqual(game.lives, remaining)
        self.assertEqual(game.state, "game_over")
        game.start()
        self.assertEqual((game.level, game.lives, game.score), (1, 3, 0))
        self.assertTrue(game.ball_attached)

    def test_paddle_motion_uses_seconds_and_stays_inside(self):
        def position(fps):
            game = Game()
            game.start()
            for _ in range(fps // 4):
                game.update(1 / fps, -1)
            return game.paddle.x
        self.assertAlmostEqual(position(40), position(60))
        for _ in range(300):
            self.game.update(1 / 60, -1)
        self.assertEqual(self.game.paddle.left, FIELD_LEFT)

    def test_client_screens_and_controls(self):
        import os
        # Виртуальное окно: проверка не мешает работе на школьном компьютере.
        os.environ["SDL_VIDEODRIVER"] = "dummy"
        import pygame
        from client import main as client

        client.initialize()
        try:
            for state in ("menu", "controls", "playing", "paused", "game_over", "boss_defeated", "win"):
                client.game.state = state
                client.draw()
                pygame.display.flip()
            client.perform_action("boss_test")
            self.assertTrue(client.game.boss_test)
            self.assertEqual(client.game.lives, 3)
            client.draw()
            self.assertEqual(client.screen.get_size(), (900, 600))
            client.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_SPACE))
            self.assertFalse(client.game.ball_attached)
            client.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_p))
            self.assertEqual(client.game.state, "paused")
            client.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_ESCAPE))
            click = pygame.event.Event(pygame.MOUSEBUTTONDOWN, button=1,
                                       pos=client.ui.MENU_BUTTONS["start"].center)
            client.handle_event(click)
            self.assertEqual(client.game.level, 1)
            self.assertEqual(client.game.state, "playing")
            client.game.state = "menu"
            client.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_b))
            self.assertTrue(client.game.boss_test)
            client.game.state = "game_over"
            client.handle_event(pygame.event.Event(pygame.KEYDOWN, key=pygame.K_RETURN))
            self.assertEqual((client.game.level, client.game.lives), (4, 3))
            self.assertTrue(client.game.ball_attached)
        finally:
            pygame.quit()


if __name__ == "__main__":
    unittest.main()
