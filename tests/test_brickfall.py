import copy
import json
import math
import unittest

from game.demo import MenuDemo
from game.logic import (
    BALL_RADIUS, FIELD_BOTTOM, FIELD_LEFT, FIELD_RIGHT, Game,
    LEVEL_BRICK_COUNTS, MAX_SCORE, PADDLE_SMALL_WIDTH, PADDLE_WIDTH, Rectangle,
)


class BrickfallTests(unittest.TestCase):
    def setUp(self):
        self.game = Game()
        self.game.start()

    def test_launch_lives_and_slow_charge(self):
        game = self.game
        game.update(1 / 60, 1)
        self.assertTrue(game.ball_attached)
        self.assertEqual(game.ball_x, game.paddle.centerx)
        game.activate_slow()
        self.assertFalse(game.slow_used)
        game.launch_ball()
        self.assertAlmostEqual(math.hypot(game.ball_speed_x, game.ball_speed_y), 360)
        game.activate_slow()
        self.assertEqual(game.slow_timer, 3)
        game.update(1 / 60)
        timer = game.slow_timer
        game.activate_slow()
        self.assertEqual(game.slow_timer, timer)
        for lives in (2, 1, 0):
            game.launch_ball()
            game.ball_y = FIELD_BOTTOM + BALL_RADIUS + 1
            game.ball_speed_y = 300
            game.update(1 / 60)
            self.assertEqual(game.lives, lives)
            self.assertTrue(game.slow_used)
        self.assertEqual(game.state, "game_over")
        old_id = game.run_id
        game.start()
        self.assertNotEqual(game.run_id, old_id)
        self.assertEqual((game.level, game.score, game.lives), (1, 0, 3))

    def test_three_original_layouts_and_final_victory(self):
        game = self.game
        for level, count in enumerate(LEVEL_BRICK_COUNTS, 1):
            self.assertEqual(game.level, level)
            self.assertEqual(len(game.bricks), count)
            self.assertEqual(len({(b.x, b.y) for b in game.bricks}), count)
            game.launch_ball()
            self.assertAlmostEqual(math.hypot(game.ball_speed_x, game.ball_speed_y), 360 + 40 * (level - 1))
            game.activate_slow()
            for brick in game.bricks[:]:
                game.break_brick(brick)
            game.update(1 / 60)
            if level < 3:
                self.assertTrue(game.ball_attached)
                self.assertFalse(game.slow_used)
                self.assertEqual(game.state, "playing")
        self.assertEqual(game.state, "win")
        self.assertEqual(game.level, 3)
        self.assertEqual(game.score, MAX_SCORE)
        self.assertEqual(game.destroyed_bricks, 142)

    def test_effect_timers_and_pause(self):
        game = self.game
        for brick in game.bricks[:5]:
            game.break_brick(brick)
        self.assertEqual(game.paddle.width, PADDLE_SMALL_WIDTH)
        game.launch_ball()
        game.activate_slow()
        game.toggle_pause()
        before = game.to_dict()
        game.update(1 / 30, 1)
        self.assertEqual(game.to_dict(), before)
        game.toggle_pause()
        game.ball_y = 400
        game.ball_speed_x, game.ball_speed_y = 150, 0
        game.paddle.x = FIELD_RIGHT - game.paddle.width
        for _ in range(180):
            game.update(1 / 60)
        self.assertEqual((game.slow_timer, game.shrink_timer), (0, 0))
        self.assertEqual(game.paddle.width, PADDLE_WIDTH)
        self.assertLessEqual(game.paddle.right, FIELD_RIGHT)
        self.assertTrue(game.slow_used)

    def test_shrink_counts_across_level_boundary(self):
        game = self.game
        for level in (1, 2):
            for brick in game.bricks[:]:
                game.break_brick(brick)
            game.launch_ball()
            game.update(1 / 60)
        self.assertEqual(game.destroyed_bricks, 88)
        game.break_brick(game.bricks[0])
        self.assertEqual(game.shrink_timer, 0)
        game.break_brick(game.bricks[0])
        self.assertEqual(game.shrink_timer, 3)

    def test_fast_ball_brick_and_paddle_collision(self):
        game = self.game
        game.launch_ball()
        game.bricks = [Rectangle(400, 300, 72, 24), Rectangle(650, 200, 72, 24)]
        hit = game.bricks[0]
        game.ball_x, game.ball_y = 430, 350
        game.ball_speed_x, game.ball_speed_y = 0, -1500
        game.update(1 / 30)
        self.assertGreater(game.ball_speed_y, 0)
        self.assertEqual((game.score, len(game.hit_events)), (10, 1))
        game.break_brick(hit)
        self.assertEqual(game.score, 10)
        game.ball_x = game.paddle.centerx + 35
        game.ball_y = game.paddle.top - BALL_RADIUS - 1
        game.ball_speed_x, game.ball_speed_y = 0, 400
        game.update(1 / 60)
        self.assertLess(game.ball_speed_y, 0)
        self.assertGreater(game.ball_speed_x, 0)
        self.assertAlmostEqual(math.hypot(game.ball_speed_x, game.ball_speed_y), 400)

    def test_wall_contact_leaves_ball_inside_field(self):
        game = self.game
        game.launch_ball()
        game.ball_x, game.ball_y = FIELD_LEFT + BALL_RADIUS + 1, 400
        game.ball_speed_x, game.ball_speed_y = -360, 0
        game.update(1 / 30)
        self.assertGreater(game.ball_speed_x, 0)
        self.assertGreaterEqual(game.ball_x - BALL_RADIUS, FIELD_LEFT)
        game.update(1 / 30)
        self.assertGreater(game.ball_x, FIELD_LEFT + BALL_RADIUS)

    def test_save_round_trip_preserves_motion_effects_and_identity(self):
        game = self.game
        for brick in game.bricks[:7]:
            game.break_brick(brick)
        game.launch_ball()
        game.activate_slow()
        game.update(1 / 60, 1)
        saved = json.loads(json.dumps(game.to_dict(), allow_nan=False))
        restored = Game.from_dict(saved)
        self.assertEqual(restored.state, "paused")
        expected = dict(saved, state="paused")
        self.assertEqual(restored.to_dict(), expected)
        restored.toggle_pause()
        restored.update(1 / 60, -1)
        game.update(1 / 60, -1)
        self.assertEqual(restored.to_dict(), game.to_dict())

    def test_save_round_trip_after_life_loss_keeps_spent_charge(self):
        game = self.game
        game.launch_ball()
        game.activate_slow()
        game.ball_y = FIELD_BOTTOM + BALL_RADIUS + 1
        game.ball_speed_y = 300
        game.update(1 / 60)
        restored = Game.from_dict(game.to_dict())
        self.assertTrue(restored.ball_attached)
        self.assertTrue(restored.slow_used)
        self.assertEqual((restored.lives, restored.slow_timer), (2, 0))
        restored.toggle_pause()
        restored.launch_ball()
        restored.activate_slow()
        self.assertEqual(restored.slow_timer, 0)

    def test_invalid_saves_are_rejected(self):
        original = self.game.to_dict()
        changes = [
            {"state": "win"}, {"run_id": "bad"}, {"level": 4},
            {"lives": True}, {"score": 10}, {"destroyed_bricks": 1},
            {"bricks": []}, {"bricks": [0, 0]}, {"bricks": [999]},
            {"slow_timer": float("nan")}, {"shrink_timer": 4},
            {"slow_timer": 1}, {"slow_used": 1}, {"extra": 1},
        ]
        for changeset in changes:
            with self.subTest(changeset=changeset):
                bad = copy.deepcopy(original)
                bad.update(changeset)
                with self.assertRaises(ValueError):
                    Game.from_dict(bad)
        for section, field, value in (("ball", "x", float("inf")),
                                      ("ball", "speed_y", -360),
                                      ("ball", "attached", "yes"),
                                      ("paddle", "x", -10),
                                      ("paddle", "width", 70)):
            with self.subTest(section=section, field=field):
                bad = copy.deepcopy(original)
                bad[section][field] = value
                with self.assertRaises(ValueError):
                    Game.from_dict(bad)
        self.game.state = "win"
        with self.assertRaises(ValueError):
            self.game.to_dict()

    def test_frame_rate_independent_paddle_and_bounds(self):
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

    def test_menu_demo_remains_playable(self):
        demo = MenuDemo()
        for _ in range(180):
            demo.update(1 / 60)
        self.assertGreater(demo.hits, 0)
        self.assertLess(len(demo.bricks), 20)
        demo.bricks = [Rectangle(150, 150, 56, 20)]
        demo.ball_x, demo.ball_y = 176, 180
        demo.ball_speed_x, demo.ball_speed_y = 0, -165
        for _ in range(30):
            demo.update(1 / 60)
        self.assertGreater(demo.reset_timer, 0)
        for _ in range(90):
            demo.update(1 / 60)
        self.assertEqual(len(demo.bricks), 20)


if __name__ == "__main__":
    unittest.main()
