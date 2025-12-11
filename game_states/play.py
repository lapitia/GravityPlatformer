import pygame
from pygame.math import Vector2
import random
from entities.speedlines import Speedline
from typing import List
from game_states.base import GameState
from game_states.paused import GameStatePaused
from level import Level, LevelLoader
from collision_system import CollisionSystem
from constants import COLORS, PLAYER_SPEED, SPRINT_ACCELERATION, SPRINT_SPEED, CONFIG, BG_IMAGE_PATH
from language_manager import LANG

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game_states.state_manager import StateManager

class GameStatePlay(GameState):
    def __init__(self, state_manager: 'StateManager', level_num: int = 1):
        self.state_manager = state_manager
        self.level_num = level_num
        self.level = LevelLoader.load(level_num)
        self.camera = (0, 0)
        self.background = pygame.image.load(BG_IMAGE_PATH).convert()
        self.original_bg = self.background.copy()

        self.speed_lines = pygame.sprite.Group()
        self.zoom = self.state_manager.zoom_level  # <-- use saved zoom
        self.min_zoom = 0.5
        self.max_zoom = 2.0

        self.cached_zoom = None
        self.cached_scaled_bg = None

    def handle_events(self, events: List[pygame.event.Event]) -> None:
        for event in events:
            if event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                self.level.player.flip_gravity()
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_l:
                    self.level.player.flip_gravity()
                if event.key == pygame.K_SPACE:
                    self.level.player.jump()
                if event.key == pygame.K_r:
                    self.level.player.reset_position()
                if event.key == pygame.K_ESCAPE:
                    self.state_manager.push_state(GameStatePaused(self.state_manager))
                # Zoom controls
                if event.key == pygame.K_z:
                    self.zoom = max(self.min_zoom, self.zoom - 0.1)
                    self.state_manager.zoom_level = self.zoom

                if event.key == pygame.K_c:
                    self.zoom = min(self.max_zoom, self.zoom + 0.1)
                    self.state_manager.zoom_level = self.zoom

    def update(self) -> None:
        keys = pygame.key.get_pressed()
        self.level.player.is_sprinting = keys[pygame.K_LSHIFT] or keys[pygame.K_RSHIFT]

        if self.level.player.is_sprinting:
            self.level.player.current_speed = min(SPRINT_SPEED, self.level.player.current_speed + SPRINT_ACCELERATION)
        else:
            self.level.player.current_speed = max(PLAYER_SPEED, self.level.player.current_speed - SPRINT_ACCELERATION*1.2)

        x_velocity = 0
        if keys[pygame.K_a]:
            x_velocity -= self.level.player.current_speed
        if keys[pygame.K_d]:
            x_velocity += self.level.player.current_speed

        self.level.player.update(x_velocity)

        self._handle_horizontal_collision()
        self.level.player.apply_physics(self.level.platforms)
        CollisionSystem.handle_collisions(self.level.player, self.level, self.state_manager)
        self.level.orbs.update()
        if self.level.player.just_flipped:
            self._create_speedlines()
            self.level.player.reset_flip_flag()

        self.speed_lines.update()
        for boss in self.level.bosses:
            boss.update(self.level.player.rect)
        
    def _create_speedlines(self) -> None:
        self.zoomed_width = CONFIG.WIDTH / self.zoom
        self.zoomed_height = CONFIG.HEIGHT / self.zoom
        camera_left = int(self.camera[0])
        camera_right = int(self.camera[0] + self.zoomed_width)
        direction = Vector2(0, self.level.player.gravity_direction)
        camera_left = int(self.camera[0])
        camera_right = int(self.camera[0] + self.zoomed_width)
        player_y = self.level.player.rect.centery

        #create lines across the entire visible width
        for _ in range(random.randint(30, 40)):
            x = random.randint(camera_left, camera_right)
            y = player_y + random.randint(-200, 200) #vertical spread
            #random horizontal offset
            offset = Vector2(
                random.randint(-50, 50),
                random.randint(-100, 100)
            )
            pos = Vector2(x, y) + offset
            
            self.speed_lines.add(Speedline(pos, direction))

    def _handle_horizontal_collision(self) -> None:
        for platform in self.level.platforms:
            if self.level.player.rect.colliderect(platform.rect):
                if self.level.player.rect.centerx < platform.rect.centerx:
                    self.level.player.rect.right = platform.rect.left
                else:
                    self.level.player.rect.left = platform.rect.right

    def draw(self, screen: pygame.Surface) -> None:
        #calculate camera position with zoom
        self.zoomed_width = CONFIG.WIDTH / self.zoom
        self.zoomed_height = CONFIG.HEIGHT / self.zoom
        self.camera = (
            self.level.player.rect.centerx - self.zoomed_width // 2,
            self.level.player.rect.centery - self.zoomed_height // 2
        )
        
        #create a surface to render the zoomed view
        zoom_surface = pygame.Surface((self.zoomed_width, self.zoomed_height))
        
        if self.zoom != self.cached_zoom or not self.cached_scaled_bg:
            #only scale background when zoom changes
            bg_width = max(1, int(self.original_bg.get_width() * self.zoom))
            bg_height = max(1, int(self.original_bg.get_height() * self.zoom))
            self.cached_scaled_bg = pygame.transform.scale(self.original_bg, (bg_width, bg_height))
            self.cached_zoom = self.zoom

        tile = self.cached_scaled_bg
        tile_width = tile.get_width()
        tile_height = tile.get_height()
        parallax_offset = -self.camera[0] * 0.5

        #drawing background logic
        x_start = parallax_offset % tile_width - tile_width
        y_start = 0
        x = x_start
        while x < self.zoomed_width:
            y = y_start
            while y < self.zoomed_height:
                zoom_surface.blit(tile, (x, y))
                y += tile_height
            x += tile_width        
            
        #draw all sprites on the zoom surface
        for sprite in self.level.all_sprites:
            screen_x = sprite.rect.x - self.camera[0]
            screen_y = sprite.rect.y - self.camera[1]
            if -sprite.rect.width < screen_x < self.zoomed_width and -sprite.rect.height < screen_y < self.zoomed_height:
                zoom_surface.blit(sprite.image, (screen_x, screen_y))
        
        #draw speedlines
        for line in self.speed_lines:
            line.offset.update(self.camera)
            screen_x = line.rect.x - self.camera[0]
            screen_y = line.rect.y - self.camera[1]
            zoom_surface.blit(line.image, (screen_x, screen_y))
        
        #scale the zoom surface to the screen size
        scaled_zoom = pygame.transform.scale(zoom_surface, (CONFIG.WIDTH, CONFIG.HEIGHT))
        screen.blit(scaled_zoom, (0, 0))
        
        self._draw_ui(screen)
        pygame.display.flip()

    def _draw_ui(self, screen: pygame.Surface) -> None:
        player = self.level.player
        current_level = self.level_num
        
        #defining instructions and game info
        instructions = [
            LANG.strings["hud"]["level"].format(current_level),
            LANG.strings["hud"]["move"],
            LANG.strings["hud"]["jump"],
            LANG.strings["hud"]["sprint"],
            LANG.strings["hud"]["flip_gravity"],
            LANG.strings["hud"]["reset"],
            LANG.strings["hud"]["pause"],
            LANG.strings["hud"]["zoom"].format(f"{self.zoom:.1f}")
        ]

        font_small = pygame.freetype.Font('fonts/Silver.ttf',30)
        line_height = 30
        start_x = 10
        start_y = 40

        gravity_text = LANG.strings["hud"]["down"] if player.gravity_direction == 1 else LANG.strings["hud"]["up"]
        text_surf, _ = font_small.render(gravity_text, COLORS["WHITE"])
        screen.blit(text_surf, (10, 10))

        for i, text in enumerate(instructions):
            text_surf, _ = font_small.render(text, COLORS["WHITE"])
            screen.blit(text_surf, (start_x, start_y + i * line_height))
            
        if self.level.active_sign:
            sign = self.level.active_sign
            scaled_font_size = max(36, int(32 * self.zoom))
            font = pygame.freetype.Font('fonts/Silver.ttf', scaled_font_size)
            
            sign_screen_x = (sign.rect.x - self.camera[0]) * self.zoom
            sign_screen_y = (sign.rect.y - self.camera[1] - 40) * self.zoom
            
            text_surf, text_rect = font.render(sign.message, COLORS["WHITE"])
            bg_rect = text_rect.inflate(int(20 * self.zoom), int(10 * self.zoom))
            bg_rect.center = (sign_screen_x, sign_screen_y)
            
            pygame.draw.rect(screen, COLORS["BLACK"], bg_rect)
            pygame.draw.rect(screen, COLORS["WHITE"], bg_rect, max(1, int(2 * self.zoom)))
            screen.blit(text_surf, (bg_rect.x + int(10 * self.zoom), bg_rect.y + int(5 * self.zoom)))
