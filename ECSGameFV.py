import pygame
import random
import time
import os
from pytmx import load_pygame

# Initialize Pygame
pygame.init()

# Constants
SCREEN_WIDTH, SCREEN_HEIGHT = 1200, 800
TILE_SIZE = 16
FPS = 60
BEST_TIME_FILE = "best_time.txt"
TEXT_COLOR = (190, 0, 0)  # Red color

# Set up the display
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Catch Pokeballs!")

# Load the TMX map
tmx_data = load_pygame("assets/mapPokemon1.tmx")

# Calculate zoom level to fit the map to the screen size
map_width = tmx_data.width * TILE_SIZE
map_height = tmx_data.height * TILE_SIZE
zoom_level_x = SCREEN_WIDTH / map_width
zoom_level_y = SCREEN_HEIGHT / map_height
zoom_level = min(zoom_level_x, zoom_level_y)

# Load the best time from file
def load_best_time():
    if os.path.exists(BEST_TIME_FILE):
        with open(BEST_TIME_FILE, "r") as file:
            return float(file.read().strip())
    return float("inf")

# Save the best time to file
def save_best_time(best_time):
    with open(BEST_TIME_FILE, "w") as file:
        file.write(str(best_time))

best_time = load_best_time()

# ECS Components
class PositionComponent:
    def __init__(self, x, y):
        self.x = x
        self.y = y

class VelocityComponent:
    def __init__(self, speed):
        self.speed = speed
        self.vx = 0
        self.vy = 0
        self.direction = "down"  # Default direction

class SpriteComponent:
    def __init__(self, sprite_sheet_path, frame_width, frame_height, scale):
        self.sprite_sheet = pygame.image.load(sprite_sheet_path).convert_alpha()
        self.frame_width = frame_width
        self.frame_height = frame_height
        self.scale = scale
        self.frames = {
            'down': [],
            'left': [],
            'right': [],
            'up': []
        }
        self.current_frame = 0
        self.load_frames()
        self.image = self.frames['down'][0]  # Default frame
        self.rect = self.image.get_rect()

    def load_frames(self):
        sheet_width, sheet_height = self.sprite_sheet.get_size()
        directions = ['down', 'left', 'right', 'up']

        for row, direction in enumerate(directions):
            for col in range(sheet_width // self.frame_width):
                if col * self.frame_width < sheet_width and row * self.frame_height < sheet_height:
                    frame = self.sprite_sheet.subsurface(
                        pygame.Rect(col * self.frame_width, row * self.frame_height, self.frame_width, self.frame_height)
                    )
                    scaled_frame = pygame.transform.scale(
                        frame, (int(self.frame_width * self.scale), int(self.frame_height * self.scale))
                    )
                    self.frames[direction].append(scaled_frame)

    def next_frame(self, direction):
        self.current_frame = (self.current_frame + 1) % len(self.frames[direction])
        self.image = self.frames[direction][self.current_frame]
        self.rect = self.image.get_rect()

class CameraComponent:
    def __init__(self):
        self.x = 0
        self.y = 0

class CollidableComponent:
    def __init__(self, rect):
        self.rect = rect

class CollectibleComponent:
    def __init__(self, rect):
        self.rect = rect

# ECS Systems
class MovementSystem:
    def update(self, entities):
        for entity in entities:
            if 'velocity' in entity and 'position' in entity:
                new_x = entity['position'].x + entity['velocity'].vx
                new_y = entity['position'].y + entity['velocity'].vy

                new_x = max(0, min(new_x, map_width - entity['sprite'].rect.width))
                new_y = max(0, min(new_y, map_height - entity['sprite'].rect.height))

                entity['position'].x = new_x
                entity['position'].y = new_y

class CameraSystem:
    def update(self, entities, target):
        for entity in entities:
            if 'camera' in entity:
                camera = entity['camera']
                camera_speed = 0.1
                camera.x += (target['position'].x - SCREEN_WIDTH // 2 - camera.x) * camera_speed
                camera.y += (target['position'].y - SCREEN_HEIGHT // 2 - camera.y) * camera_speed

                camera.x = max(0, min(camera.x, map_width - SCREEN_WIDTH))
                camera.y = max(0, min(camera.y, map_height - SCREEN_HEIGHT))

class RenderSystem:
    def __init__(self, screen, tmx_data, zoom_level):
        self.screen = screen
        self.tmx_data = tmx_data
        self.zoom_level = zoom_level
        self.frame_counter = 0
        self.font = pygame.font.Font(None, 36)  # Initialize font

    def draw_map(self, camera):
        for layer in self.tmx_data.visible_layers:
            if hasattr(layer, "tiles"):
                for x, y, image in layer.tiles():
                    scaled_image = pygame.transform.scale(image, (int(TILE_SIZE * self.zoom_level), int(TILE_SIZE * self.zoom_level)))
                    self.screen.blit(scaled_image, (x * TILE_SIZE * self.zoom_level - camera.x, y * TILE_SIZE * self.zoom_level - camera.y))

    def draw_entities(self, entities, camera):
        for entity in entities:
            if 'sprite' in entity and 'position' in entity:
                scaled_image = pygame.transform.scale(entity['sprite'].image, (int(entity['sprite'].rect.width * self.zoom_level), int(entity['sprite'].rect.height * self.zoom_level)))
                self.screen.blit(scaled_image, (entity['position'].x * self.zoom_level - camera.x, entity['position'].y * self.zoom_level - camera.y))

    def draw_score(self, score):
        score_text = self.font.render(f"Score: {score}", True, TEXT_COLOR)
        self.screen.blit(score_text, (10, 10))

    def draw_timer(self, elapsed_time, best_time):
        timer_text = self.font.render(f"Time: {elapsed_time:.2f}s", True, TEXT_COLOR)
        best_time_text = self.font.render(f"Best Time: {best_time:.2f}s", True, TEXT_COLOR)
        self.screen.blit(timer_text, (10, 50))
        self.screen.blit(best_time_text, (10, 90))

    def update(self, entities, camera, score, elapsed_time, best_time):
        self.screen.fill((0, 0, 0))
        self.draw_map(camera)
        self.draw_entities(entities, camera)
        self.draw_score(score)
        self.draw_timer(elapsed_time, best_time)
        pygame.display.flip()

class CollisionSystem:
    def update(self, entities, collidables):
        for entity in entities:
            if 'position' in entity and 'sprite' in entity:
                original_position = (entity['position'].x, entity['position'].y)
                entity_rect = entity['sprite'].rect.copy()
                entity_rect.topleft = (entity['position'].x, entity['position'].y)

                entity['position'].x += entity['velocity'].vx
                entity_rect.topleft = (entity['position'].x, entity['position'].y)
                for collidable in collidables:
                    collidable_rect = collidable['collidable'].rect
                    if entity_rect.colliderect(collidable_rect):
                        if entity['velocity'].vx > 0:
                            entity['position'].x = collidable_rect.left - entity_rect.width
                        elif entity['velocity'].vx < 0:
                            entity['position'].x = collidable_rect.right
                        entity['velocity'].vx = 0
                        break

                entity['position'].y += entity['velocity'].vy
                entity_rect.topleft = (entity['position'].x, entity['position'].y)
                for collidable in collidables:
                    collidable_rect = collidable['collidable'].rect
                    if entity_rect.colliderect(collidable_rect):
                        if entity['velocity'].vy > 0:
                            entity['position'].y = collidable_rect.top - entity_rect.height
                        elif entity['velocity'].vy < 0:
                            entity['position'].y = collidable_rect.bottom
                        entity['velocity'].vy = 0
                        break

class CollectibleSystem:
    def update(self, player, collectibles):
        player_rect = player['sprite'].rect.copy()
        player_rect.topleft = (player['position'].x, player['position'].y)
        collected = []
        for collectible in collectibles:
            if player_rect.colliderect(collectible['collectible'].rect):
                collected.append(collectible)
        return collected

# ECS Entity
class Entity:
    def __init__(self):
        self.components = {}

    def add_component(self, component_name, component):
        self.components[component_name] = component

    def __getitem__(self, item):
        return self.components[item]

    def __contains__(self, item):
        return item in self.components

# Create player entity
player = Entity()
player.add_component('position', PositionComponent(map_width // 2, map_height - 100))
player.add_component('velocity', VelocityComponent(1))
player.add_component('sprite', SpriteComponent("assets/sacha.png", 64, 64, 0.4))  # Adjust frame size and scale

# Create camera entity
camera = Entity()
camera.add_component('camera', CameraComponent())

camera['camera'].x = player['position'].x - SCREEN_WIDTH // 2
camera['camera'].y = player['position'].y - SCREEN_HEIGHT // 2

# Load collidable objects
collidables = []
for obj in tmx_data.get_layer_by_name("Object Layer 1"):
    if obj.type == "collidable":
        collidables.append(Entity())
        collidables[-1].add_component('collidable', CollidableComponent(pygame.Rect(obj.x, obj.y, obj.width, obj.height)))

# Load collectible objects (pokeballs)
collectibles = []
while len(collectibles) < 5:
    x = random.randint(0, map_width - 32)
    y = random.randint(0, map_height - 32)
    pokeball_rect = pygame.Rect(x, y, 32, 32)
    if not any(pokeball_rect.colliderect(collidable['collidable'].rect) for collidable in collidables):
        collectible = Entity()
        collectible.add_component('position', PositionComponent(x, y))
        collectible.add_component('sprite', SpriteComponent("assets/pokeball.png", 32, 32, 1))  # No scaling needed for pokeball
        collectible.add_component('collectible', CollectibleComponent(pokeball_rect))
        collectibles.append(collectible)

# Create systems
movement_system = MovementSystem()
camera_system = CameraSystem()
render_system = RenderSystem(screen, tmx_data, zoom_level)
collision_system = CollisionSystem()
collectible_system = CollectibleSystem()

# Main game loop
clock = pygame.time.Clock()
running = True
score = 0
start_time = time.time()
timer_running = True

while running:
    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            running = False

    keys = pygame.key.get_pressed()
    if keys[pygame.K_LEFT]:
        player['velocity'].vx = -player['velocity'].speed
        player['velocity'].direction = 'left'
    elif keys[pygame.K_RIGHT]:
        player['velocity'].vx = player['velocity'].speed
        player['velocity'].direction = 'right'
    else:
        player['velocity'].vx = 0

    if keys[pygame.K_UP]:
        player['velocity'].vy = -player['velocity'].speed
        player['velocity'].direction = 'up'
    elif keys[pygame.K_DOWN]:
        player['velocity'].vy = player['velocity'].speed
        player['velocity'].direction = 'down'
    else:
        player['velocity'].vy = 0

    if player['velocity'].vx != 0 or player['velocity'].vy != 0:
        player['sprite'].next_frame(player['velocity'].direction)

    # Update systems
    movement_system.update([player])
    collision_system.update([player], collidables)
    camera_system.update([camera], player)
    collected = collectible_system.update(player, collectibles)
    for collectible in collected:
        collectibles.remove(collectible)
        score += 1

    # Calculate elapsed time
    if timer_running:
        elapsed_time = time.time() - start_time

    # Check if all pokeballs are collected
    if score == 5 and timer_running:
        timer_running = False
        if elapsed_time < best_time:
            best_time = elapsed_time
            save_best_time(best_time)

    render_system.update([player] + collectibles, camera['camera'], score, elapsed_time, best_time)

    clock.tick(FPS)

pygame.quit()