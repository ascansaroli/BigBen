"""Frogger - a classic arcade clone built with pygame."""
import random
import sys

import pygame

CELL = 40
COLS = 14
ROWS = 14
PLAY_W = COLS * CELL
PLAY_H = ROWS * CELL
UI_H = 70
WIDTH = PLAY_W
HEIGHT = PLAY_H + UI_H
FPS = 60

ROW_HOME = 0
ROW_SAFE_TOP = 1
RIVER_ROWS = (2, 3, 4, 5, 6)
ROW_MEDIAN = 7
ROAD_ROWS = (8, 9, 10, 11, 12)
ROW_START = 13

HOME_COLS = (1, 4, 7, 10, 13)
HOME_TOLERANCE = CELL * 0.4

START_LIVES = 4
LIFE_TIME = 35.0

BLACK = (0, 0, 0)
WHITE = (255, 255, 255)
GRASS_DARK = (10, 90, 30)
GRASS_LIGHT = (20, 130, 45)
WATER = (30, 90, 200)
WATER_DARK = (20, 70, 170)
ROAD = (40, 40, 40)
ROAD_LINE = (200, 200, 60)
SAND = (210, 190, 140)
SLOT_OPEN = (15, 60, 25)
SLOT_FILLED = (60, 200, 90)
FROG_GREEN = (60, 200, 90)
FROG_DARK = (30, 130, 55)
RED = (210, 50, 40)
YELLOW = (230, 190, 30)
BLUE = (50, 110, 220)
PURPLE = (150, 60, 180)
ORANGE = (230, 130, 30)
LOG_BROWN = (120, 80, 40)
LOG_BROWN_DARK = (90, 58, 26)
TURTLE_GREEN = (40, 150, 90)
TURTLE_DARK = (25, 100, 60)


def clamp(value, low, high):
    return max(low, min(high, value))


class Lane:
    """A horizontal strip of evenly spaced, wrapping entities (cars/logs/turtles)."""

    def __init__(self, row, speed, direction, width_cells, gap_cells, color, dark_color, kind):
        self.row = row
        self.base_speed = speed
        self.direction = direction
        self.width_cells = width_cells
        self.gap_cells = gap_cells
        self.color = color
        self.dark_color = dark_color
        self.kind = kind
        self.phase = random.uniform(0, 1) * self._spacing()

    def _spacing(self):
        return (self.width_cells + self.gap_cells) * CELL

    def speed_px(self, level):
        return self.base_speed * (1 + 0.12 * (level - 1))

    def velocity_px(self, level):
        return self.direction * self.speed_px(level)

    def update(self, dt, level):
        sp = self._spacing()
        self.phase = (self.phase + self.direction * self.speed_px(level) * dt) % (PLAY_W + sp)

    def entity_rects(self):
        sp = self._spacing()
        count = int(PLAY_W // sp) + 3
        w = self.width_cells * CELL
        y = self.row * CELL
        rects = []
        for i in range(count):
            x = (self.phase + i * sp) % (PLAY_W + sp) - sp
            rects.append(pygame.Rect(int(x), y, w, CELL))
        return rects

    def draw(self, surface):
        for rect in self.entity_rects():
            if self.kind == "car":
                pygame.draw.rect(surface, self.color, rect, border_radius=6)
                pygame.draw.rect(surface, self.dark_color, rect, width=2, border_radius=6)
                wheel_y = rect.bottom - 4
                pygame.draw.circle(surface, BLACK, (rect.left + 8, wheel_y), 4)
                pygame.draw.circle(surface, BLACK, (rect.right - 8, wheel_y), 4)
            elif self.kind == "log":
                pygame.draw.rect(surface, self.color, rect, border_radius=10)
                for gx in range(rect.left + 10, rect.right, 16):
                    pygame.draw.line(surface, self.dark_color, (gx, rect.top + 4), (gx, rect.bottom - 4), 2)
            else:  # turtle
                segment_w = rect.width // self.width_cells
                for i in range(self.width_cells):
                    cx = rect.left + segment_w * i + segment_w // 2
                    cy = rect.centery
                    pygame.draw.ellipse(surface, self.color, (cx - 17, cy - 14, 34, 28))
                    pygame.draw.ellipse(surface, self.dark_color, (cx - 17, cy - 14, 34, 28), width=2)


def build_lanes():
    road = [
        Lane(8, 90, -1, 1, 2.0, RED, (120, 20, 15), "car"),
        Lane(9, 130, 1, 1, 1.5, YELLOW, (140, 110, 10), "car"),
        Lane(10, 70, -1, 2, 2.0, BLUE, (20, 60, 140), "car"),
        Lane(11, 150, 1, 1, 3.0, PURPLE, (90, 25, 120), "car"),
        Lane(12, 100, -1, 1, 1.2, ORANGE, (150, 80, 10), "car"),
    ]
    river = [
        Lane(2, 60, 1, 3, 2.0, LOG_BROWN, LOG_BROWN_DARK, "log"),
        Lane(3, 90, -1, 2, 1.5, TURTLE_GREEN, TURTLE_DARK, "turtle"),
        Lane(4, 50, 1, 4, 2.5, LOG_BROWN, LOG_BROWN_DARK, "log"),
        Lane(5, 110, -1, 2, 1.5, TURTLE_GREEN, TURTLE_DARK, "turtle"),
        Lane(6, 70, 1, 3, 2.0, LOG_BROWN, LOG_BROWN_DARK, "log"),
    ]
    return road, river


class Frog:
    def __init__(self):
        self.reset()

    def reset(self):
        self.col = COLS // 2
        self.row = ROW_START
        self.x = float(self.col * CELL)
        self.y = float(self.row * CELL)
        self.furthest_row = ROW_START

    def rect(self):
        return pygame.Rect(int(self.x), int(self.y), CELL, CELL)

    def jump(self, dcol, drow):
        cur_col = round(self.x / CELL)
        new_col = clamp(cur_col + dcol, 0, COLS - 1)
        new_row = clamp(self.row + drow, 0, ROWS - 1)
        self.col = new_col
        self.row = new_row
        self.x = float(new_col * CELL)
        self.y = float(new_row * CELL)

    def carry(self, dx, dt):
        self.x += dx * dt

    def draw(self, surface):
        rect = self.rect()
        pygame.draw.ellipse(surface, FROG_GREEN, rect.inflate(-4, -4))
        pygame.draw.ellipse(surface, FROG_DARK, rect.inflate(-4, -4), width=2)
        eye_y = rect.top + 9
        pygame.draw.circle(surface, WHITE, (rect.left + 11, eye_y), 5)
        pygame.draw.circle(surface, WHITE, (rect.right - 11, eye_y), 5)
        pygame.draw.circle(surface, BLACK, (rect.left + 11, eye_y), 2)
        pygame.draw.circle(surface, BLACK, (rect.right - 11, eye_y), 2)


class Game:
    def __init__(self):
        pygame.init()
        pygame.display.set_caption("Frogger")
        self.screen = pygame.display.set_mode((WIDTH, HEIGHT))
        self.clock = pygame.time.Clock()
        self.font_big = pygame.font.SysFont("arial", 48, bold=True)
        self.font_med = pygame.font.SysFont("arial", 26, bold=True)
        self.font_small = pygame.font.SysFont("arial", 18)
        self.state = "TITLE"
        self.new_game()

    def new_game(self):
        self.level = 1
        self.score = 0
        self.lives = START_LIVES
        self.road_lanes, self.river_lanes = build_lanes()
        self.home_filled = [False] * len(HOME_COLS)
        self.frog = Frog()
        self.life_timer = LIFE_TIME
        self.transition_timer = 0.0
        self.state = "TITLE"

    def start_level(self):
        self.road_lanes, self.river_lanes = build_lanes()
        self.home_filled = [False] * len(HOME_COLS)
        self.frog.reset()
        self.life_timer = LIFE_TIME
        self.state = "PLAYING"

    def respawn(self, lose_life=True):
        if lose_life:
            self.lives -= 1
        if self.lives < 0:
            self.state = "GAME_OVER"
            return
        self.frog.reset()
        self.life_timer = LIFE_TIME

    def handle_input(self, event):
        if self.state == "TITLE":
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self.start_level()
            return
        if self.state == "GAME_OVER":
            if event.key == pygame.K_r:
                self.new_game()
            return
        if self.state != "PLAYING":
            return
        if event.key == pygame.K_UP:
            self.try_advance_row(0, -1)
        elif event.key == pygame.K_DOWN:
            self.frog.jump(0, 1)
        elif event.key == pygame.K_LEFT:
            self.frog.jump(-1, 0)
        elif event.key == pygame.K_RIGHT:
            self.frog.jump(1, 0)
        elif event.key == pygame.K_ESCAPE:
            pygame.quit()
            sys.exit()

    def try_advance_row(self, dcol, drow):
        frog = self.frog
        frog.jump(dcol, drow)
        if frog.row < frog.furthest_row:
            self.score += 10 * (frog.furthest_row - frog.row)
            frog.furthest_row = frog.row

    def update_playing(self, dt):
        for lane in self.road_lanes:
            lane.update(dt, self.level)
        for lane in self.river_lanes:
            lane.update(dt, self.level)

        self.life_timer -= dt
        if self.life_timer <= 0:
            self.respawn()
            return

        frog = self.frog
        row = frog.row

        if row in ROAD_ROWS:
            for lane in self.road_lanes:
                if lane.row != row:
                    continue
                for rect in lane.entity_rects():
                    if rect.colliderect(frog.rect()):
                        self.respawn()
                        return

        elif row in RIVER_ROWS:
            on_support = False
            for lane in self.river_lanes:
                if lane.row != row:
                    continue
                for rect in lane.entity_rects():
                    if rect.colliderect(frog.rect()):
                        on_support = True
                        frog.carry(lane.velocity_px(self.level), dt)
                        break
                if on_support:
                    break
            if not on_support:
                self.respawn()
                return
            if frog.x < -CELL or frog.x > PLAY_W:
                self.respawn()
                return

        elif row == ROW_HOME:
            landed = False
            for i, col in enumerate(HOME_COLS):
                slot_center = col * CELL + CELL / 2
                if abs((frog.x + CELL / 2) - slot_center) < HOME_TOLERANCE:
                    if self.home_filled[i]:
                        self.respawn()
                        return
                    self.home_filled[i] = True
                    self.score += 50 + int(self.life_timer * 10)
                    landed = True
                    break
            if not landed:
                self.respawn()
                return
            if all(self.home_filled):
                self.score += 1000
                self.level += 1
                self.state = "LEVEL_COMPLETE"
                self.transition_timer = 2.0
            else:
                frog.reset()
                self.life_timer = LIFE_TIME

    def update(self, dt):
        if self.state == "PLAYING":
            self.update_playing(dt)
        elif self.state == "LEVEL_COMPLETE":
            self.transition_timer -= dt
            if self.transition_timer <= 0:
                self.start_level()

    def draw_board(self):
        screen = self.screen
        for row in range(ROWS):
            y = row * CELL
            if row == ROW_HOME:
                color = SAND
            elif row in (ROW_SAFE_TOP, ROW_MEDIAN, ROW_START):
                color = GRASS_LIGHT if row % 2 == 0 else GRASS_DARK
            elif row in RIVER_ROWS:
                color = WATER if row % 2 == 0 else WATER_DARK
            else:
                color = ROAD
            pygame.draw.rect(screen, color, (0, y, PLAY_W, CELL))

        for row in ROAD_ROWS:
            y = row * CELL + CELL - 2
            for x in range(0, PLAY_W, 24):
                pygame.draw.rect(screen, ROAD_LINE, (x, y, 14, 3))

        for i, col in enumerate(HOME_COLS):
            rect = pygame.Rect(col * CELL + 2, ROW_HOME * CELL + 2, CELL - 4, CELL - 4)
            color = SLOT_FILLED if self.home_filled[i] else SLOT_OPEN
            pygame.draw.rect(screen, color, rect, border_radius=8)
            if self.home_filled[i]:
                center = rect.center
                pygame.draw.circle(screen, FROG_DARK, center, 12)
                pygame.draw.circle(screen, FROG_GREEN, center, 9)

    def draw_ui(self):
        screen = self.screen
        ui_rect = pygame.Rect(0, PLAY_H, WIDTH, UI_H)
        pygame.draw.rect(screen, (15, 15, 20), ui_rect)

        score_surf = self.font_med.render(f"Score: {self.score}", True, WHITE)
        screen.blit(score_surf, (16, PLAY_H + 12))

        level_surf = self.font_med.render(f"Level: {self.level}", True, WHITE)
        screen.blit(level_surf, (16, PLAY_H + 40))

        for i in range(max(self.lives, 0)):
            cx = WIDTH - 24 - i * 28
            cy = PLAY_H + 22
            pygame.draw.ellipse(screen, FROG_GREEN, (cx - 10, cy - 8, 20, 16))

        if self.state == "PLAYING":
            bar_w = 160
            ratio = clamp(self.life_timer / LIFE_TIME, 0, 1)
            bar_rect = pygame.Rect(WIDTH - bar_w - 16, PLAY_H + 42, bar_w, 14)
            pygame.draw.rect(screen, (60, 60, 60), bar_rect, border_radius=4)
            fill_color = (60, 200, 90) if ratio > 0.3 else (210, 60, 40)
            pygame.draw.rect(
                screen, fill_color,
                (bar_rect.x, bar_rect.y, int(bar_w * ratio), bar_rect.height),
                border_radius=4,
            )

    def draw_overlay_text(self, lines, sub_lines=None):
        overlay = pygame.Surface((WIDTH, HEIGHT), pygame.SRCALPHA)
        overlay.fill((0, 0, 0, 170))
        self.screen.blit(overlay, (0, 0))
        y = HEIGHT // 2 - 60
        for line in lines:
            surf = self.font_big.render(line, True, WHITE)
            self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))
            y += 56
        if sub_lines:
            y += 10
            for line in sub_lines:
                surf = self.font_small.render(line, True, (220, 220, 220))
                self.screen.blit(surf, (WIDTH // 2 - surf.get_width() // 2, y))
                y += 26

    def draw(self):
        self.draw_board()
        for lane in self.road_lanes:
            lane.draw(self.screen)
        for lane in self.river_lanes:
            lane.draw(self.screen)
        if self.state in ("PLAYING", "LEVEL_COMPLETE"):
            self.frog.draw(self.screen)
        self.draw_ui()

        if self.state == "TITLE":
            self.draw_overlay_text(
                ["FROGGER"],
                ["Arrow keys to hop, reach the lily pads.",
                 "Ride the logs and turtles, dodge traffic.",
                 "Press ENTER to start, ESC to quit."],
            )
        elif self.state == "LEVEL_COMPLETE":
            self.draw_overlay_text([f"LEVEL {self.level - 1} CLEAR!"])
        elif self.state == "GAME_OVER":
            self.draw_overlay_text(
                ["GAME OVER"],
                [f"Final score: {self.score}", "Press R to restart, ESC to quit."],
            )

        pygame.display.flip()

    def run(self):
        while True:
            dt = self.clock.tick(FPS) / 1000.0
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    pygame.quit()
                    sys.exit()
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE and self.state in ("TITLE", "GAME_OVER"):
                        pygame.quit()
                        sys.exit()
                    self.handle_input(event)
            self.update(dt)
            self.draw()


def main():
    Game().run()


if __name__ == "__main__":
    main()
