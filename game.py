import pygame
import sys
import os
import math
import random

pygame.init()

SCREEN_WIDTH, SCREEN_HEIGHT = 800, 600
TILE_SIZE = 32
PLAYER_SPEED = 5
JUMP_FORCE = -13
GRAVITY = 0.5
FPS = 60
KNOCKBACK_FORCE = 10  # Force of knockback
KNOCKBACK_DURATION = 300  # ms
STUN_DURATION = 1000  # ms

SKY_BLUE = (135, 206, 235)
BLACK = (0, 0, 0)
GREEN = (34, 139, 34)
BROWN = (139, 69, 19)
RED = (255, 0, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)
PURPLE = (128, 0, 128)
CYAN = (0, 255, 255)
MAGENTA = (255, 0, 255)
ORANGE = (255, 165, 0)
WHITE = (255, 255, 255)

BACKGROUND_SCROLL_SPEED = 0.5
MIDGROUND_SCROLL_SPEED = 1.0
FOREGROUND_SCROLL_SPEED = 1.5


class Player(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.animations = self.load_animations()
        self.current_state = "idle"
        self.current_frame = 0
        self.animation_speed = 100
        self.animation_timer = 0
        self.image = self.animations[self.current_state][self.current_frame]
        self.prev_state = "idle"

        self.rect = self.image.get_rect(topleft=(x, y))

        self.hitbox = pygame.Rect(0, 0, 20, 40)
        self.hitbox.midbottom = self.rect.midbottom
        self.hitbox.bottom -= 4

        self.velocity_y = 0
        self.direction = pygame.math.Vector2(0, 0)
        self.on_ground = False
        self.facing_right = True
        self.hit_timer = 0
        self.hit_cooldown = 1000
        self.show_hitbox = False
        self.was_running = False
        self.actually_moved_x = False

        # Attack system variables
        self.is_attacking = False
        self.attack_timer = 0
        self.attack_cooldown = 500
        self.attack_frame = 0
        self.attack_hitbox = None
        self.attack_direction = 1

        self.attack_overlays = {}
        self.load_attack_overlays()
        self.current_overlay = None
        self.overlay_positions = {
            2: (26, 98),
            3: (19, 108)
        }

        self.health = 100
        self.max_health = 100
        self.invincible = False
        self.invincibility_timer = 0
        self.invincibility_duration = 500  # ms

        self.knockback_velocity = pygame.math.Vector2(0, 0)
        self.knockback_timer = 0
        self.stunned = False
        self.stun_timer = 0

        self.is_alive = True
        self.death_time = 0
        self.respawn_time = 3000

        self.total_enemies_killed = 0
        self.initial_health = self.health
        self.level_complete = False

    def load_animations(self):
        animations = {
            "idle": self.load_spritesheet("img/idle_anim.png", 30, 256),
            "jump": self.load_spritesheet("img/jump_anim.png", 36, 257),
            "hit": self.load_spritesheet("img/hit_anim.png", 28, 256),
            "attack": self.load_spritesheet("img/attack_anim.png", 50, 256)
        }

        run_frames = self.load_spritesheet("img/run_anim.png", 35, 257)

        animations["start_run"] = run_frames[0:2]
        animations["run"] = run_frames[2:-2]
        animations["end_run"] = run_frames[-3:]

        return animations

    def load_spritesheet(self, filename, frame_width, frame_height):
        sheet = pygame.image.load(filename).convert_alpha()

        frame_count = sheet.get_height() // frame_height
        frames = []
        for i in range(frame_count):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), (0, i * frame_height, frame_width, frame_height))
            frames.append(frame)

        return frames

    def load_attack_overlays(self):
        overlay1 = pygame.image.load("img/attack_frame2.png").convert_alpha()
        overlay1 = pygame.transform.scale(overlay1, (98, 60))
        self.attack_overlays[2] = overlay1
        print("Loaded attack_frame2.png")

        overlay2 = pygame.image.load("img/attack_frame3.png").convert_alpha()
        overlay2 = pygame.transform.scale(overlay2, (100, 40))
        self.attack_overlays[3] = overlay2
        print("Loaded attack_frame3.png")

    def update(self, tiles, dt):
        if not self.is_alive:
            current_time = pygame.time.get_ticks()
            if current_time - self.death_time > self.respawn_time:
                self.respawn(100, 300)
            return
        self.actually_moved_x = False

        self.update_knockback_stun(dt)

        if self.is_attacking:
            self.attack_timer -= dt
            if self.attack_timer <= 0:
                self.is_attacking = False
                self.attack_hitbox = None
                self.current_overlay = None

        if self.hit_timer > 0:
            self.hit_timer -= dt

        if self.invincible:
            self.invincibility_timer -= dt
            if self.invincibility_timer <= 0:
                self.invincible = False

        prev_x = self.rect.x
        self.rect.x += self.direction.x * PLAYER_SPEED
        self.hitbox.centerx = self.rect.centerx
        self.hitbox.bottom = self.rect.bottom - 4

        self.collide_horizontal(tiles)

        if abs(self.rect.x - prev_x) > 0.1:
            self.actually_moved_x = True

        self.apply_gravity(tiles)

        self.update_animation_state()

        self.animation_timer += dt
        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0

            if self.is_attacking:
                self.attack_frame += 1
                frames = self.animations["attack"]
                self.attack_timer -= dt
                self.update_attack_hitbox()
                if self.attack_frame >= len(frames):
                    self.is_attacking = False
                    self.attack_frame = 0
                    self.attack_hitbox = None
                    self.current_overlay = None
                else:
                    if self.attack_frame == 2:
                        self.current_overlay = 2
                    elif self.attack_frame == 3:
                        self.current_overlay = 3
                    else:
                        self.current_overlay = None
            else:
                frames = self.animations[self.current_state]
                self.current_frame = (self.current_frame + 1) % len(frames)
                self.current_overlay = None

        try:
            if self.is_attacking:
                self.image = self.animations["attack"][self.attack_frame]
            else:
                self.image = self.animations[self.current_state][self.current_frame]
        except IndexError:
            pass
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)

        if self.stunned:
            self.apply_gravity(tiles)
            return

        if self.direction.x > 0:
            self.facing_right = True
            self.attack_direction = 1
        elif self.direction.x < 0:
            self.facing_right = False
            self.attack_direction = -1

        self.was_running = self.current_state in ["run", "start_run"]
        self.prev_state = self.current_state

    def apply_gravity(self, tiles):
        self.velocity_y += GRAVITY
        self.rect.y += self.velocity_y
        self.hitbox.bottom = self.rect.bottom - 4

        self.collide_vertical(tiles)

    def update_knockback_stun(self, dt):
        if self.knockback_timer > 0:
            self.rect.x += self.knockback_velocity.x
            self.rect.y += self.knockback_velocity.y
            self.hitbox.centerx = self.rect.centerx
            self.hitbox.bottom = self.rect.bottom - 4

            self.knockback_velocity *= 0.9
            self.knockback_timer -= dt

            if self.knockback_timer <= 0:
                self.stunned = True
                self.stun_timer = STUN_DURATION
                self.knockback_velocity = pygame.math.Vector2(0, 0)

        if self.stunned:
            self.stun_timer -= dt
            if self.stun_timer <= 0:
                self.stunned = False

        if self.stunned:
            self.current_state = "hit"
            self.current_frame = min(self.current_frame, len(self.animations["hit"]) - 1)

    def apply_knockback(self, source_x, source_y, force=KNOCKBACK_FORCE):
        direction = pygame.math.Vector2(self.rect.centerx - source_x,
                                        self.rect.centery - source_y)
        if direction.length() > 0:
            direction = direction.normalize()
        else:
            direction = pygame.math.Vector2(-1 if self.facing_right else 1, -0.3)

        self.knockback_velocity = direction * force
        self.knockback_timer = KNOCKBACK_DURATION
        self.velocity_y = 0

        self.take_hit()

    def update_animation_state(self):
        if self.is_attacking:
            self.current_state = "attack"
            return

        if self.hit_timer > 0:
            self.current_state = "hit"
            return

        if not self.on_ground:
            self.current_state = "jump"
            return

        moving = self.direction.x != 0

        if moving and self.prev_state in ["idle", "end_run"]:
            self.current_state = "start_run"
            self.current_frame = 0
            return

        if self.current_state == "start_run":
            frames = self.animations["start_run"]
            if self.current_frame >= len(frames) - 1:
                self.current_state = "run"
                self.current_frame = 0
            return

        if not moving and self.was_running:
            self.current_state = "end_run"
            self.current_frame = 0
            return

        if self.current_state == "end_run":
            frames = self.animations["end_run"]
            if self.current_frame >= len(frames) - 1:
                self.current_state = "idle"
                self.current_frame = 0
            return

        if moving:
            self.current_state = "run"
        else:
            self.current_state = "idle"

    def collide_horizontal(self, tiles):
        for tile in tiles:
            if self.hitbox.colliderect(tile.rect):
                if self.direction.x > 0:
                    self.hitbox.right = tile.rect.left
                elif self.direction.x < 0:
                    self.hitbox.left = tile.rect.right
                self.rect.centerx = self.hitbox.centerx

    def collide_vertical(self, tiles):
        self.on_ground = False
        for tile in tiles:
            if self.hitbox.colliderect(tile.rect):
                if self.velocity_y > 0:
                    self.hitbox.bottom = tile.rect.top
                    self.rect.bottom = self.hitbox.bottom + 4
                    self.on_ground = True
                    self.velocity_y = 0
                elif self.velocity_y < 0:
                    self.hitbox.top = tile.rect.bottom + 3
                    self.rect.top = self.hitbox.top - (self.rect.height - self.hitbox.height) + 3
                    self.velocity_y = 0

    def attack(self):
        if not self.is_attacking and not self.stunned:
            self.is_attacking = True
            self.attack_timer = self.attack_cooldown
            self.attack_frame = 0
            self.current_overlay = None

            self.update_attack_hitbox()

    def update_attack_hitbox(self):
        if not self.is_attacking:
            return

        attack_width = 110
        attack_height = 65
        attack_x_offset = 45

        if self.facing_right:
            self.attack_hitbox = pygame.Rect(
                self.hitbox.right - attack_x_offset,
                self.hitbox.centery - attack_height // 2 - 10,
                attack_width,
                attack_height
            )
        else:
            self.attack_hitbox = pygame.Rect(
                self.hitbox.left - (attack_width - attack_x_offset) + 15,
                self.hitbox.centery - attack_height // 2 - 10,
                attack_width,
                attack_height
            )

    def jump(self):
        if self.on_ground and not self.stunned:
            self.velocity_y = JUMP_FORCE

    def take_hit(self):
        if self.hit_timer <= 0:
            self.hit_timer = self.hit_cooldown

    def take_damage(self, amount, source_x, source_y):
        if not self.invincible and self.is_alive:
            self.health -= amount
            self.invincible = True
            self.invincibility_timer = self.invincibility_duration
            self.take_hit()
            self.apply_knockback(source_x, source_y)
            if self.health <= 0:
                self.health = 0
                self.is_alive = False
                self.death_time = pygame.time.get_ticks()
                self.current_state = "hit"
                self.current_frame = 0

    def respawn(self, x, y):
        self.is_alive = True
        self.health = self.max_health
        self.rect.topleft = (x, y)
        self.hitbox.midbottom = self.rect.midbottom
        self.hitbox.bottom -= 4
        self.velocity_y = 0
        self.direction = pygame.math.Vector2(0, 0)
        self.invincible = True
        self.invincibility_timer = 2000
        self.stunned = False
        self.knockback_velocity = pygame.math.Vector2(0, 0)
        self.current_state = "idle"
        self.current_frame = 0

    def get_overlay_position(self):
        if self.current_overlay is None:
            return None

        offset_x, offset_y = self.overlay_positions[self.current_overlay]

        if not self.facing_right:
            offset_x = -offset_x + 20

        return (self.rect.centerx + offset_x, self.rect.centery + offset_y)

    def get_overlay_sprite(self, frame):
        if frame not in self.attack_overlays:
            return None

        sprite = self.attack_overlays[frame]

        if not self.facing_right:
            sprite = pygame.transform.flip(sprite, True, False)

        return sprite


class Tile(pygame.sprite.Sprite):
    def __init__(self, x, y, color):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE))
        self.image = pygame.image.load('img/tile.jpg').convert_alpha()
        self.rect = self.image.get_rect(topleft=(x, y))


class Projectile(pygame.sprite.Sprite):
    def __init__(self, x, y, direction, speed, damage, color, size=(10, 10)):
        super().__init__()
        self.image = pygame.Surface(size)
        self.image.fill(color)
        self.rect = self.image.get_rect(center=(x, y))
        self.direction = direction.normalize() if direction.length() > 0 else pygame.math.Vector2(1, 0)
        self.speed = speed
        self.damage = damage
        self.lifetime = 3000  # milliseconds
        self.spawn_time = pygame.time.get_ticks()

    def update(self, dt):
        self.rect.x += self.direction.x * self.speed * dt / 16
        self.rect.y += self.direction.y * self.speed * dt / 16

        if pygame.time.get_ticks() - self.spawn_time > self.lifetime:
            self.kill()


class BaseEnemy(pygame.sprite.Sprite):
    def __init__(self, x, y, color, width=24, height=32):
        super().__init__()
        self.animations = self.load_animations()
        self.current_state = "idle"
        self.current_frame = 0
        self.animation_speed = 150
        self.animation_timer = 0
        self.image = self.animations[self.current_state][self.current_frame]
        self.prev_state = "idle"

        self.rect = self.image.get_rect(topleft=(x, y))

        hitbox_width = width * 0.8
        hitbox_height = height * 0.9
        self.hitbox = pygame.Rect(0, 0, hitbox_width, hitbox_height)
        self.hitbox.midbottom = self.rect.midbottom

        self.health = 3
        self.max_health = 3
        self.hit_cooldown = 1000
        self.last_hit_time = 0
        self.direction = pygame.math.Vector2(0, 0)
        self.speed = 1.5
        self.velocity_y = 0
        self.on_ground = False
        self.facing_right = True
        self.hit_timer = 0
        self.invincible = False
        self.invincibility_timer = 0
        self.invincibility_duration = 500

        self.knockback_velocity = pygame.math.Vector2(0, 0)
        self.knockback_timer = 0
        self.stunned = False
        self.stun_timer = 0

    def load_animations(self):
        animations = {
            "idle": self.create_placeholder_animation(4, (255, 0, 0)),
            "move": self.create_placeholder_animation(4, (200, 0, 0)),
            "attack": self.create_placeholder_animation(4, (255, 100, 100)),
            "hit": self.create_placeholder_animation(2, (255, 255, 255))
        }
        return animations

    def load_spritesheet(self, filename, frame_width, frame_height, scale_factor=1.0):
        try:
            sheet = pygame.image.load(filename).convert_alpha()
        except FileNotFoundError:
            print(f"Spritesheet '{filename}' not found. Using placeholder.")
            return self.create_placeholder_animation(4, (255, 0, 0))

        frame_count = sheet.get_height() // frame_height
        frames = []

        scaled_width = int(frame_width * scale_factor)
        scaled_height = int(frame_height * scale_factor)

        for i in range(frame_count):
            frame = pygame.Surface((frame_width, frame_height), pygame.SRCALPHA)
            frame.blit(sheet, (0, 0), (0, i * frame_height, frame_width, frame_height))

            if scale_factor != 1.0:
                frame = pygame.transform.scale(frame, (scaled_width, scaled_height))

            frames.append(frame)

        return frames

    def create_placeholder_animation(self, frame_count, color):
        frames = []
        for i in range(frame_count):
            surf = pygame.Surface((24, 32), pygame.SRCALPHA)
            frame_color = (
                min(255, color[0] + i * 10),
                min(255, color[1] + i * 10),
                min(255, color[2] + i * 10)
            )
            pygame.draw.rect(surf, frame_color, (0, 0, 24, 32))
            pygame.draw.rect(surf, (50, 50, 50), (0, 0, 24, 32), 2)
            frames.append(surf)
        return frames

    def update(self, player, tiles, dt, current_time=None):
        if current_time is None:
            current_time = pygame.time.get_ticks()

        self.update_knockback_stun(dt)

        self.animation_timer += dt

        if self.invincible:
            self.invincibility_timer -= dt
            if self.invincibility_timer <= 0:
                self.invincible = False

        if self.hit_timer > 0:
            self.hit_timer -= dt

        self.apply_gravity(tiles)

        if self.direction.x > 0:
            self.facing_right = True
        elif self.direction.x < 0:
            self.facing_right = False

        self.update_animation_state()

        if self.animation_timer >= self.animation_speed:
            self.animation_timer = 0
            frames = self.animations[self.current_state]
            self.current_frame = (self.current_frame + 1) % len(frames)

        if self.stunned:
            self.apply_gravity(tiles)
            return

        try:
            self.image = self.animations[self.current_state][self.current_frame]
        except Exception:
            pass
        if not self.facing_right:
            self.image = pygame.transform.flip(self.image, True, False)

        self.prev_state = self.current_state

    def apply_gravity(self, tiles):
        self.velocity_y += GRAVITY
        self.rect.y += self.velocity_y
        self.hitbox.bottom = self.rect.bottom

        self.collide_vertical(tiles)

    def update_knockback_stun(self, dt):
        if self.knockback_timer > 0:
            self.rect.x += self.knockback_velocity.x
            self.rect.y += self.knockback_velocity.y
            self.hitbox.centerx = self.rect.centerx
            self.hitbox.bottom = self.rect.bottom

            self.knockback_velocity *= 0.9
            self.knockback_timer -= dt

            if self.knockback_timer <= 0:
                self.stunned = True
                self.stun_timer = STUN_DURATION
                self.knockback_velocity = pygame.math.Vector2(0, 0)

        if self.stunned:
            self.stun_timer -= dt
            if self.stun_timer <= 0:
                self.stunned = False

        if self.stunned:
            self.current_state = "hit"
            self.current_frame = min(self.current_frame, len(self.animations["hit"]) - 1)

    def apply_knockback(self, source_x, source_y, force=KNOCKBACK_FORCE):
        direction = pygame.math.Vector2(self.rect.centerx - source_x,
                                        self.rect.centery - source_y)
        if direction.length() > 0:
            direction = direction.normalize()
        else:
            direction = pygame.math.Vector2(-1 if self.facing_right else 1, -0.3)

        # Apply force
        self.knockback_velocity = direction * force
        self.knockback_timer = KNOCKBACK_DURATION
        self.velocity_y = 0
        self.hit_timer = 300

    def update_animation_state(self):
        if self.hit_timer > 0:
            self.current_state = "hit"
            return

        if self.direction.x != 0:
            self.current_state = "move"
        else:
            self.current_state = "idle"

    def collide_vertical(self, tiles):
        self.on_ground = False
        for tile in tiles:
            if self.hitbox.colliderect(tile.rect):
                if self.velocity_y > 0:
                    self.hitbox.bottom = tile.rect.top
                    self.rect.bottom = self.hitbox.bottom
                    self.on_ground = True
                    self.velocity_y = 0
                elif self.velocity_y < 0:
                    self.hitbox.top = tile.rect.bottom
                    self.rect.top = self.hitbox.top
                    self.velocity_y = 0

    def take_damage(self, amount, source_x, source_y):
        if not self.invincible:
            self.health -= amount
            self.invincible = True
            self.invincibility_timer = self.invincibility_duration
            self.hit_timer = 300  # Show hit animation for 300ms
            self.apply_knockback(source_x, source_y)
            if self.health <= 0:
                self.kill()


class ChargerEnemy(BaseEnemy):
    def __init__(self, x, y):
        super().__init__(x, y, (200, 50, 50), 36, 76)  # Red enemy (slightly larger)

        self.animations = self.load_animations()
        try:
            self.image = self.animations[self.current_state][self.current_frame]
        except Exception:
            pass
        self.rect = self.image.get_rect(topleft=(x, y))

        self.state = "patrol"  # patrol, charge, cooldown
        self.patrol_range = 2 * TILE_SIZE
        self.patrol_direction = 1  # 1 for right, -1 for left
        self.start_x = x
        self.charge_speed = 6
        self.charge_direction = pygame.math.Vector2(0, 0)
        self.charge_cooldown = 2000  # ms
        self.last_charge_time = 0
        self.agro_distance = 200
        self.charge_damage = 30
        self.attack_cooldown = 1000
        self.last_attack_time = 0
        self.patrol_speed = 1.5

    def load_animations(self):
        try:
            animations = {
                "idle": self.load_spritesheet("img/goon_idle.png", 49, 256, 0.7),
                "move": self.load_spritesheet("img/goon_walk.png", 62, 256, 0.7),
                "charge": self.load_spritesheet("img/goon_atack.png", 136, 256, 0.7),
                "hit": self.load_spritesheet("img/goon_hit.png", 112, 256, 0.7)
            }
        except:
            animations = {
                "idle": self.create_placeholder_animation(4, (200, 50, 50)),
                "move": self.create_placeholder_animation(4, (180, 40, 40)),
                "charge": self.create_placeholder_animation(4, (220, 60, 60)),
                "hit": self.create_placeholder_animation(2, (255, 150, 150))
            }
        return animations

    def update(self, player, tiles, dt, current_time=None):
        if current_time is None:
            current_time = pygame.time.get_ticks()

        if self.stunned:
            super().update(player, tiles, dt, current_time)
            return

        prev_state = self.state

        dist_to_player = math.sqrt((self.rect.centerx - player.rect.centerx) ** 2 +
                                   (self.rect.centery - player.rect.centery) ** 2)

        if self.state == "patrol":
            if dist_to_player < self.agro_distance:
                self.state = "charge"
                self.charge_direction = pygame.math.Vector2(player.rect.centerx - self.rect.centerx,
                                                            player.rect.centery - self.rect.centery)
                if self.charge_direction.length() > 0:
                    self.charge_direction = self.charge_direction.normalize()
                self.last_charge_time = current_time
        elif self.state == "charge":
            if current_time - self.last_charge_time > 1000:  # Charge for 1 second
                self.state = "cooldown"
                self.last_charge_time = current_time
        elif self.state == "cooldown":
            if current_time - self.last_charge_time > self.charge_cooldown:
                self.state = "patrol"
                if player.rect.centerx > self.rect.centerx:
                    self.patrol_direction = -1
                else:
                    self.patrol_direction = 1

        if self.state == "patrol":
            if abs(self.rect.x - self.start_x) >= self.patrol_range:
                self.patrol_direction *= -1

            self.direction.x = self.patrol_direction
            self.rect.x += self.direction.x * self.patrol_speed
            self.hitbox.centerx = self.rect.centerx

            self.collide_horizontal(tiles)

        elif self.state == "charge":
            self.rect.x += self.charge_direction.x * self.charge_speed
            self.rect.y += self.charge_direction.y * self.charge_speed
            self.hitbox.centerx = self.rect.centerx
            self.hitbox.centery = self.rect.centery

            if self.hitbox.colliderect(player.hitbox) and current_time - self.last_attack_time > self.attack_cooldown:
                player.take_damage(self.charge_damage, self.rect.centerx, self.rect.centery)
                self.last_attack_time = current_time

        super().update(player, tiles, dt, current_time)

        self.update_animation_state()

    def update_animation_state(self):
        if self.hit_timer > 0:
            self.current_state = "hit"
        elif self.state == "charge":
            self.current_state = "charge"
        elif self.direction.x != 0:
            self.current_state = "move"
        else:
            self.current_state = "idle"

    def collide_horizontal(self, tiles):
        for tile in tiles:
            if self.hitbox.colliderect(tile.rect):
                if self.state == "charge":
                    self.state = "cooldown"
                    self.last_charge_time = pygame.time.get_ticks()

                if self.direction.x > 0:
                    self.hitbox.right = tile.rect.left
                    self.patrol_direction *= -1
                elif self.direction.x < 0:
                    self.hitbox.left = tile.rect.right
                    self.patrol_direction *= -1
                self.rect.centerx = self.hitbox.centerx


class ShooterEnemy(BaseEnemy):
    def __init__(self, x, y):
        super().__init__(x, y, (50, 50, 200), 24, 64)  # Blue enemy

        self.animations = self.load_animations()
        try:
            self.image = self.animations[self.current_state][self.current_frame]
        except Exception:
            pass
        self.rect = self.image.get_rect(topleft=(x, y))

        self.shoot_cooldown = 2000  # ms
        self.last_shot_time = 0
        self.projectile_speed = 4
        self.projectile_damage = 20
        self.shoot_range = 400
        self.projectiles = pygame.sprite.Group()
        self.attack_animation_duration = 300  # ms
        self.attack_start_time = 0

    def load_animations(self):
        try:
            animations = {
                "idle": self.load_spritesheet("img/shooter_idle.png", 38, 256, 0.7),
                "shoot": self.load_spritesheet("img/shooter_shot.png", 48, 256, 0.7),
                "hit": self.load_spritesheet("img/shooter_hit.png", 58, 256, 0.7)
            }
        except:
            animations = {
                "idle": self.create_placeholder_animation(4, (50, 50, 200)),
                "shoot": self.create_placeholder_animation(4, (100, 100, 255)),
                "hit": self.create_placeholder_animation(2, (150, 150, 255))
            }
        return animations

    def update(self, player, tiles, dt, current_time=None):
        if current_time is None:
            current_time = pygame.time.get_ticks()

        self.direction.x = 0

        super().update(player, tiles, dt, current_time)

        dist_to_player = math.sqrt((self.rect.centerx - player.rect.centerx) ** 2 +
                                   (self.rect.centery - player.rect.centery) ** 2)

        if (dist_to_player < self.shoot_range and
                current_time - self.last_shot_time > self.shoot_cooldown and
                self.current_state != "shoot"):
            self.current_state = "shoot"
            self.current_frame = 0
            self.animation_timer = 0
            self.last_shot_time = current_time
            self.attack_start_time = current_time
            self.shoot(player)

        if (self.current_state == "shoot" and
                current_time - self.attack_start_time > self.attack_animation_duration):
            self.current_state = "idle"
            self.current_frame = 0
            self.animation_timer = 0

        self.projectiles.update(dt)

        if self.stunned:
            super().update(player, tiles, dt, current_time)
            return

    def update_animation_state(self):
        if self.hit_timer > 0:
            self.current_state = "hit"

    def shoot(self, player):
        direction = pygame.math.Vector2(player.rect.centerx - self.rect.centerx,
                                        player.rect.centery - self.rect.centery + 100)
        if direction.length() > 0:
            direction = direction.normalize()

        projectile = Projectile(
            self.rect.centerx,
            self.rect.centery,
            direction,
            self.projectile_speed,
            self.projectile_damage,
            BLUE
        )
        self.projectiles.add(projectile)


class HybridEnemy(BaseEnemy):
    def __init__(self, x, y):
        super().__init__(x, y, (150, 50, 150), 28, 36)  # Purple enemy (slightly larger)

        # Load custom animations
        self.animations = self.load_animations()
        try:
            self.image = self.animations[self.current_state][self.current_frame]
        except Exception:
            pass
        self.rect = self.image.get_rect(topleft=(x, y))

        # Hybrid-specific properties
        self.state = "idle"  # idle, melee, shoot
        self.melee_range = 60
        self.shoot_range = 250
        self.melee_damage = 8
        self.projectile_damage = 15
        self.projectile_speed = 3
        self.attack_cooldown = 1500  # ms
        self.last_attack_time = 0
        self.projectiles = pygame.sprite.Group()
        self.charge_speed = 4
        self.charge_direction = pygame.math.Vector2(0, 0)
        self.charge_duration = 400  # ms
        self.charge_start_time = 0
        self.attack_animation_duration = 500  # ms

    def load_animations(self):
        try:
            animations = {
                "idle": self.load_spritesheet("hybrid_idle.png", 28, 36),
                "move": self.load_spritesheet("hybrid_move.png", 28, 36),
                "melee": self.load_spritesheet("hybrid_melee.png", 36, 36),
                "shoot": self.load_spritesheet("hybrid_shoot.png", 32, 36),
                "hit": self.load_spritesheet("hybrid_hit.png", 28, 36)
            }
        except:
            animations = {
                "idle": self.create_placeholder_animation(4, (150, 50, 150)),
                "move": self.create_placeholder_animation(4, (130, 40, 130)),
                "melee": self.create_placeholder_animation(4, (180, 60, 180)),
                "shoot": self.create_placeholder_animation(4, (170, 70, 170)),
                "hit": self.create_placeholder_animation(2, (200, 100, 200))
            }
        return animations

    def update(self, player, tiles, dt, current_time=None):
        if current_time is None:
            current_time = pygame.time.get_ticks()

        if self.stunned:
            super().update(player, tiles, dt, current_time)
            return

        prev_state = self.state

        super().update(player, tiles, dt, current_time)

        self.projectiles.update(dt)

        dist_to_player = math.sqrt((self.rect.centerx - player.rect.centerx) ** 2 +
                                   (self.rect.centery - player.rect.centery) ** 2)

        if self.state == "idle":
            if dist_to_player < self.melee_range:
                self.state = "melee"
                self.charge_direction = pygame.math.Vector2(player.rect.centerx - self.rect.centerx,
                                                            player.rect.centery - self.rect.centery)
                if self.charge_direction.length() > 0:
                    self.charge_direction = self.charge_direction.normalize()
                self.charge_start_time = current_time
                self.last_attack_time = current_time
            elif dist_to_player < self.shoot_range:
                self.state = "shoot"
                self.last_attack_time = current_time
                self.attack_start_time = current_time
        elif self.state == "melee":
            if current_time - self.charge_start_time > self.charge_duration:
                self.state = "idle"
        elif self.state == "shoot":
            if current_time - self.attack_start_time > self.attack_animation_duration:
                self.state = "idle"

        if self.state == "melee":
            self.rect.x += self.charge_direction.x * self.charge_speed
            self.rect.y += self.charge_direction.y * self.charge_speed
            self.hitbox.centerx = self.rect.centerx
            self.hitbox.centery = self.rect.centery

            if self.hitbox.colliderect(player.hitbox):
                player.take_damage(self.melee_damage, self.rect.centerx, self.rect.centery)
                self.state = "idle"
        elif self.state == "shoot" and current_time - self.attack_start_time > 100:
            if prev_state != "shoot":
                direction = pygame.math.Vector2(player.rect.centerx - self.rect.centerx,
                                                player.rect.centery - self.rect.centery + 100)
                if direction.length() > 0:
                    direction = direction.normalize()

                # Create projectile
                projectile = Projectile(
                    self.rect.centerx,
                    self.rect.centery,
                    direction,
                    self.projectile_speed,
                    self.projectile_damage,
                    PURPLE,
                    (8, 8)
                )
                self.projectiles.add(projectile)

        self.update_animation_state()

    def update_animation_state(self):
        if self.hit_timer > 0:
            self.current_state = "hit"
        elif self.state == "melee":
            self.current_state = "melee"
        elif self.state == "shoot":
            self.current_state = "shoot"
        elif self.direction.x != 0:
            self.current_state = "move"
        else:
            self.current_state = "idle"


class Camera:
    def __init__(self, width, height):
        self.camera = pygame.Rect(0, 0, width, height)
        self.width = width
        self.height = height
        self.vertical_deadzone = 100
        self.smoothness = 0.1

    def apply(self, entity):
        return entity.rect.move(self.camera.topleft)

    def apply_point(self, point):
        return (point[0] + self.camera.x, point[1] + self.camera.y)

    def apply_rect(self, rect):
        return rect.move(self.camera.topleft)

    def update(self, target):
        x = -target.rect.centerx + SCREEN_WIDTH // 2

        target_center_y = target.rect.centery
        screen_center_y = SCREEN_HEIGHT // 2
        dist_y = target_center_y - (screen_center_y - self.camera.y)

        if abs(dist_y) > self.vertical_deadzone:
            target_y = -target.rect.centery + screen_center_y
            if dist_y > 0:
                target_y += self.vertical_deadzone
            else:
                target_y -= self.vertical_deadzone
            y = self.camera.y + (target_y - self.camera.y) * self.smoothness
        else:
            y = self.camera.y

        x = min(0, x)
        y = min(0, y)
        x = max(-(self.width - SCREEN_WIDTH), x)
        y = max(-(self.height - SCREEN_HEIGHT), y)

        self.camera = pygame.Rect(x, y, self.width, self.height)


class Background:
    def __init__(self, image_path, scroll_speed):
        self.image = pygame.image.load(image_path).convert_alpha()
        img_width = int(self.image.get_width() * (SCREEN_HEIGHT / self.image.get_height()))
        self.image = pygame.transform.scale(self.image, (img_width, SCREEN_HEIGHT))

        self.width = self.image.get_width()
        self.scroll_speed = scroll_speed
        self.x = 0
        self.x2 = self.width

    def update(self, player):
        if player.actually_moved_x:
            if player.direction.x > 0:
                self.x -= self.scroll_speed
                self.x2 -= self.scroll_speed
            elif player.direction.x < 0:
                self.x += self.scroll_speed
                self.x2 += self.scroll_speed

        if self.x <= -self.width:
            self.x = self.width
        if self.x2 <= -self.width:
            self.x2 = self.width
        if self.x >= self.width:
            self.x = -self.width
        if self.x2 >= self.width:
            self.x2 = -self.width

    def draw(self, screen, camera):
        screen.blit(self.image, (self.x + camera.camera.x * self.scroll_speed * 0.1, 0))
        screen.blit(self.image, (self.x2 + camera.camera.x * self.scroll_speed * 0.1, 0))


def generate_level():
    tiles = pygame.sprite.Group()

    for x in range(0, 60 * TILE_SIZE, TILE_SIZE):
        tiles.add(Tile(x, 20 * TILE_SIZE, BROWN))

    for y in range(0, 64 * TILE_SIZE, TILE_SIZE):
        tiles.add(Tile(-TILE_SIZE, y, BROWN))
        for y in range(0, 64 * TILE_SIZE, TILE_SIZE):
            tiles.add(Tile(60 * TILE_SIZE, y, RED))

    platforms = [
        (5 * TILE_SIZE, 16 * TILE_SIZE, 4),
        (8 * TILE_SIZE, 13 * TILE_SIZE, 3),
        (12 * TILE_SIZE, 10 * TILE_SIZE, 2),

        (18 * TILE_SIZE, 8 * TILE_SIZE, 5),
        (25 * TILE_SIZE, 11 * TILE_SIZE, 3),
        (31 * TILE_SIZE, 14 * TILE_SIZE, 3),
        (30 * TILE_SIZE, 7 * TILE_SIZE, 2),

        (35 * TILE_SIZE, 12 * TILE_SIZE, 4),
        (40 * TILE_SIZE, 9 * TILE_SIZE, 3),
        (47 * TILE_SIZE, 15 * TILE_SIZE, 6),
        (42 * TILE_SIZE, 17 * TILE_SIZE, 2),
        (52 * TILE_SIZE, 12 * TILE_SIZE, 4),
    ]

    for x, y, length in platforms:
        for i in range(length):
            tiles.add(Tile(x + i * TILE_SIZE, y, GREEN))

    floating_platforms = [
        (15 * TILE_SIZE, 15 * TILE_SIZE),
        (22 * TILE_SIZE, 13 * TILE_SIZE),
        (28 * TILE_SIZE, 16 * TILE_SIZE),
        (38 * TILE_SIZE, 14 * TILE_SIZE),
        (50 * TILE_SIZE, 10 * TILE_SIZE)
    ]

    for x, y in floating_platforms:
        tiles.add(Tile(x, y, GREEN))

    for x in range(25 * TILE_SIZE, 28 * TILE_SIZE, TILE_SIZE):
        tiles.add(Tile(x, 17 * TILE_SIZE, GREEN))

    return tiles


def draw_health_bar(screen, camera, entity, x_offset=0, y_offset=-15):
    health_width = 30
    health_height = 5
    health_x = entity.rect.centerx - health_width // 2 + x_offset
    health_y = entity.rect.top + y_offset + 200

    health_rect = pygame.Rect(
        health_x + camera.camera.x,
        health_y + camera.camera.y,
        health_width,
        health_height
    )

    pygame.draw.rect(screen, (255, 0, 0), health_rect)

    health_fill_width = health_width * entity.health / entity.max_health
    health_fill_rect = pygame.Rect(
        health_rect.x,
        health_rect.y,
        health_fill_width,
        health_height
    )
    pygame.draw.rect(screen, (0, 255, 0), health_fill_rect)

    # Border
    pygame.draw.rect(screen, (50, 50, 50), health_rect, 1)


class Goal(pygame.sprite.Sprite):
    def __init__(self, x, y):
        super().__init__()
        self.image = pygame.Surface((TILE_SIZE, TILE_SIZE * 2))
        self.image.fill(YELLOW)
        self.rect = self.image.get_rect(topleft=(x, y))


def calculate_rating(player, total_enemies):
    health_lost = player.initial_health - player.health
    enemies_killed = player.total_enemies_killed

    # Calculate health score (0-100, higher is better)
    health_score = max(0, 100 - (health_lost * 2))

    # Calculate kill score (0-100, higher is better)
    kill_score = (enemies_killed / total_enemies) * 100 if total_enemies > 0 else 100

    # Weighted average (60% health, 40% kills)
    total_score = (health_score * 0.4) + (kill_score * 0.6)

    # Determine rating
    if total_score >= 90:
        return "S", total_score
    elif total_score >= 75:
        return "A", total_score
    elif total_score >= 60:
        return "B", total_score
    elif total_score >= 45:
        return "C", total_score
    else:
        return "D", total_score


def show_win_screen(screen, player, total_enemies):
    """Display the win screen with performance rating"""
    screen.fill(BLACK)
    font_large = pygame.font.SysFont(None, 72)
    font_medium = pygame.font.SysFont(None, 48)
    font_small = pygame.font.SysFont(None, 36)

    # Calculate rating
    rating, score = calculate_rating(player, total_enemies)

    # Render text
    win_text = font_large.render("LEVEL COMPLETE!", True, WHITE)
    rating_text = font_medium.render(f"Rating: {rating}", True, WHITE)
    score_text = font_medium.render(f"Score: {score:.1f}/100", True, WHITE)
    stats_text = font_small.render(
        f"Health Lost: {player.initial_health - player.health} | Enemies Killed: {player.total_enemies_killed}/{total_enemies}",
        True, (255, 255, 255)
    )
    continue_text = font_small.render("Press any key to continue...", True, WHITE)

    # Position text
    screen.blit(win_text, (SCREEN_WIDTH // 2 - win_text.get_width() // 2, 150))
    screen.blit(rating_text, (SCREEN_WIDTH // 2 - rating_text.get_width() // 2, 250))
    screen.blit(score_text, (SCREEN_WIDTH // 2 - score_text.get_width() // 2, 300))
    screen.blit(stats_text, (SCREEN_WIDTH // 2 - stats_text.get_width() // 2, 350))
    screen.blit(continue_text, (SCREEN_WIDTH // 2 - continue_text.get_width() // 2, 450))

    pygame.display.flip()

    # Wait for key press
    waiting = True
    while waiting:
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                pygame.quit()
                sys.exit()
            if event.type == pygame.KEYDOWN:
                waiting = False
                return True  # Return True to indicate game should restart


def main():
    pygame.mixer.init()

    try:
        pygame.mixer.music.load(
            "music/Hotline_Miami_2_Wrong_Number_OST_-_Technoir_76701774.mp3")  # Replace with your file
        pygame.mixer.music.set_volume(0.3)  # 30% volume for background music
        pygame.mixer.music.play(-1)  # -1 means loop indefinitely
    except Exception as e:
        print(f"Could not load background music: {e}")

    screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
    pygame.display.set_caption("Neco Adventures")
    clock = pygame.time.Clock()

    # Font for instructions
    font = pygame.font.SysFont(None, 24)

    # Load sound files
    try:
        win_sound = pygame.mixer.Sound("music/videoplayback.mp3")
        win_sound.set_volume(0.5)  # 50% volume
    except Exception as e:
        print(f"Could not load sound file: {e}")
        win_sound = None

    # Level setup
    all_tiles = generate_level()
    player = Player(100, 300)
    player_group = pygame.sprite.Group(player)

    # Create goal at the end of the level
    goal = Goal(58 * TILE_SIZE, 18 * TILE_SIZE)
    goal_group = pygame.sprite.Group(goal)

    # Camera setup
    level_width = 60 * TILE_SIZE  # Map width in pixels
    level_height = 30 * TILE_SIZE  # Map height
    camera = Camera(level_width, level_height)

    # Create enemies
    enemies = pygame.sprite.Group()

    chargers_spaw = [
        ChargerEnemy(19 * TILE_SIZE, 15 * TILE_SIZE),
        ChargerEnemy(34 * TILE_SIZE, 13 * TILE_SIZE),
        ChargerEnemy(20 * TILE_SIZE, 4 * TILE_SIZE),
        ChargerEnemy(36.5 * TILE_SIZE, 9 * TILE_SIZE),
        ChargerEnemy(49 * TILE_SIZE, 11 * TILE_SIZE),
        ChargerEnemy(50 * TILE_SIZE, 15 * TILE_SIZE),
    ]
    enemies.add(*chargers_spaw)
    shooters_spawn = [
        ShooterEnemy(15 * TILE_SIZE, 11 * TILE_SIZE),
        ShooterEnemy(22 * TILE_SIZE, 9 * TILE_SIZE),
        ShooterEnemy(28 * TILE_SIZE, 12 * TILE_SIZE),
        ShooterEnemy(31 * TILE_SIZE, 3 * TILE_SIZE),
        ShooterEnemy(50 * TILE_SIZE, 5 * TILE_SIZE),
    ]
    enemies.add(*shooters_spawn)

    total_enemies = len(enemies)

    background = Background("img/background_level1.png", BACKGROUND_SCROLL_SPEED)

    running = True
    while running:
        current_time = pygame.time.get_ticks()
        dt = clock.tick(FPS)

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                running = False
            # Only process input if player is alive and game not complete
            if player.is_alive and not player.level_complete and event.type == pygame.KEYDOWN:
                if event.key == pygame.K_SPACE:
                    player.jump()
                if event.key == pygame.K_h:
                    player.take_hit()
                if event.key == pygame.K_b:
                    player.show_hitbox = not player.show_hitbox
                if event.key == pygame.K_z:
                    player.attack()
                if event.key == pygame.K_m:
                    player.facing_right = not player.facing_right

        # Check if player reached the goal
        if not player.level_complete and player.hitbox.colliderect(goal.rect):
            player.level_complete = True
            if win_sound:
                try:
                    pygame.mixer.music.stop()
                    win_sound.play()
                except Exception as e:
                    print(f"Could not play sound: {e}")
            if show_win_screen(screen, player, total_enemies):
                return main()
        if player.level_complete:
            continue

        # Only update movement if player is alive
        if player.is_alive:
            keys = pygame.key.get_pressed()
            player.direction.x = keys[pygame.K_RIGHT] - keys[pygame.K_LEFT]
        else:
            player.direction.x = 0

        # Check for attack collisions with enemies
        if player.is_attacking and player.attack_hitbox:
            for enemy in enemies:
                if player.attack_hitbox.colliderect(enemy.hitbox):
                    # Pass player position as source for knockback
                    enemy.take_damage(1, player.rect.centerx, player.rect.centery)
                    if enemy.health <= 0:
                        player.total_enemies_killed += 1

        # Update enemies
        for enemy in enemies:
            enemy.update(player, all_tiles, dt, current_time)

            # Check for collisions with player
            if player.hitbox.colliderect(enemy.hitbox) and current_time - enemy.last_hit_time > enemy.hit_cooldown:
                # Pass enemy position as source for knockback
                player.take_damage(15, enemy.rect.centerx, enemy.rect.centery)
                enemy.last_hit_time = current_time

        # Check for projectile collisions with player
        for enemy in enemies:
            if hasattr(enemy, 'projectiles'):
                for projectile in enemy.projectiles:
                    if projectile.rect.colliderect(player.hitbox):
                        # Pass projectile position and direction for knockback
                        player.take_damage(projectile.damage, projectile.rect.centerx, projectile.rect.centery)
                        projectile.kill()

        # Update
        player.update(all_tiles, dt)
        camera.update(player)

        # Draw
        background.update(player)
        background.draw(screen, camera)

        # Draw tiles with camera offset
        for tile in all_tiles:
            screen.blit(tile.image, camera.apply(tile))

        # Draw goal
        screen.blit(goal.image, camera.apply(goal))

        # Draw enemy projectiles
        for enemy in enemies:
            if hasattr(enemy, 'projectiles'):
                for projectile in enemy.projectiles:
                    screen.blit(projectile.image, camera.apply(projectile))

        # Draw enemies with camera offset
        for enemy in enemies:
            screen.blit(enemy.image, camera.apply(enemy))
            draw_health_bar(screen, camera, enemy)

        # Draw player with camera offset
        screen.blit(player.image, camera.apply(player))
        draw_health_bar(screen, camera, player, 0, -20)

        # Draw attack overlay if active
        if player.current_overlay:
            overlay_sprite = player.get_overlay_sprite(player.current_overlay)
            if overlay_sprite:
                overlay_pos = player.get_overlay_position()
                if overlay_pos:
                    overlay_screen_pos = camera.apply_point(overlay_pos)
                    overlay_rect = overlay_sprite.get_rect(center=overlay_screen_pos)
                    screen.blit(overlay_sprite, overlay_rect)

        # Draw hitbox if enabled
        if player.show_hitbox:
            pygame.draw.rect(screen, BLUE, camera.apply_rect(player.hitbox), 2)
            for enemy in enemies:
                pygame.draw.rect(screen, RED, camera.apply_rect(enemy.hitbox), 2)

            # Draw attack hitbox if attacking
            if player.is_attacking and player.attack_hitbox:
                pygame.draw.rect(screen, YELLOW, camera.apply_rect(player.attack_hitbox), 2)

        # Draw instructions and debug info
        # debug_info = [
        #     "Arrow Keys: Move",
        #     "Space: Jump",
        #     "Z: Attack",
        #     "H: Trigger Hit Animation",
        #     "B: Toggle Hitbox Visibility",
        #     "M: Toggle Player Direction",
        #     f"Health: {player.health}/{player.max_health}",
        #     f"State: {player.current_state}",
        #     f"Enemies: {len(enemies)}",
        #     f"Projectiles: {sum(len(enemy.projectiles) for enemy in enemies if hasattr(enemy, 'projectiles'))}",
        #     f"Facing: {'Right' if player.facing_right else 'Left'}",
        #     f"Stunned: {'Yes' if player.stunned else 'No'}",
        #     f"Kills: {player.total_enemies_killed}/{total_enemies}"
        # ]

        # for i, text in enumerate(debug_info):
        #     text_surf = font.render(text, True, (50, 50, 50))
        #     screen.blit(text_surf, (10, 10 + i * 25))
        #
        # # Draw enemy info
        # enemy_info = [
        #     "ENEMY TYPES:",
        #     "RED: Charger - Charges when close",
        #     "BLUE: Shooter - Shoots projectiles",
        #     "PURPLE: Hybrid - Both melee and ranged"
        # ]
        #
        # for i, text in enumerate(enemy_info):
        #     text_surf = font.render(text, True, (200, 50, 50) if i == 0 else (50, 50, 50))
        #     screen.blit(text_surf, (SCREEN_WIDTH - 300, 10 + i * 25))

        if player.is_alive:
            screen.blit(player.image, camera.apply(player))
            draw_health_bar(screen, camera, player, 0, -20)

            # Draw attack overlay if active
            if player.current_overlay:
                overlay_sprite = player.get_overlay_sprite(player.current_overlay)
                if overlay_sprite:
                    overlay_pos = player.get_overlay_position()
                    if overlay_pos:
                        overlay_screen_pos = camera.apply_point(overlay_pos)
                        overlay_rect = overlay_sprite.get_rect(center=overlay_screen_pos)
                        screen.blit(overlay_sprite, overlay_rect)
        else:
            # Draw death message
            death_font = pygame.font.SysFont(None, 72)
            death_text = death_font.render("YOU DIED", True, (255, 0, 0))
            respawn_text = font.render(
                f"Respawning in {((player.respawn_time - (current_time - player.death_time)) // 1000 + 1)}...", True,
                (255, 255, 255))
            screen.blit(death_text, (SCREEN_WIDTH // 2 - death_text.get_width() // 2, SCREEN_HEIGHT // 2 - 50))
            screen.blit(respawn_text, (SCREEN_WIDTH // 2 - respawn_text.get_width() // 2, SCREEN_HEIGHT // 2 + 20))

        pygame.display.flip()

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
