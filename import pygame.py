import pygame
import sys
import random
from enum import Enum

# Initialize pygame
pygame.init()
pygame.mixer.init()

# Game constants
SCREEN_WIDTH = 1200
SCREEN_HEIGHT = 700
FPS = 60
GRAVITY = 1
SCROLL_THRESH = 400

# Colors
WHITE = (255, 255, 255)
BLACK = (0, 0, 0)
RED = (255, 0, 0)
GREEN = (0, 255, 0)
BLUE = (0, 0, 255)
YELLOW = (255, 255, 0)


# Game state
class GameState(Enum):
    MENU = 0
    PLAYING = 1
    GAME_OVER = 2
    LEVEL_COMPLETE = 3
    VICTORY = 4


# Create game window
screen = pygame.display.set_mode((SCREEN_WIDTH, SCREEN_HEIGHT))
pygame.display.set_caption("Space Adventure")
clock = pygame.time.Clock()

# Load font
font = pygame.font.SysFont("Arial", 30)
big_font = pygame.font.SysFont("Arial", 70)


# Function to draw text
def draw_text(text, font, color, x, y):
    img = font.render(text, True, color)
    screen.blit(img, (x, y))


# Function to draw health bar
def draw_health_bar(x, y, health, max_health):
    ratio = health / max_health
    pygame.draw.rect(screen, RED, (x, y, 100, 10))
    pygame.draw.rect(screen, GREEN, (x, y, 100 * ratio, 10))


# Base class for all game objects
class GameObject:
    def __init__(self, x, y, width, height):
        self.rect = pygame.Rect(x, y, width, height)
        self.width = width
        self.height = height
        self.vel_y = 0

    def draw(self, surface, scroll):
        pygame.draw.rect(
            surface, RED, (self.rect.x - scroll, self.rect.y, self.width, self.height)
        )


# Player class
class Player(GameObject):
    def __init__(self, x, y):
        super().__init__(x, y, 50, 80)
        self.direction = 1  # 1 for right, -1 for left
        self.speed = 8
        self.jump_power = 20
        self.jumping = False
        self.health = 100
        self.max_health = 100
        self.lives = 3
        self.score = 0
        self.shooting_cooldown = 0
        self.shooting_cooldown_max = 15
        self.invincibility = 0
        self.invincibility_duration = 60
        self.color = BLUE

    def update(self, platforms, enemies, collectibles):
        # Get key presses
        key = pygame.key.get_pressed()

        dx = 0
        dy = 0

        # Movement
        if key[pygame.K_LEFT]:
            dx = -self.speed
            self.direction = -1
        if key[pygame.K_RIGHT]:
            dx = self.speed
            self.direction = 1

        # Jump
        if key[pygame.K_SPACE] and not self.jumping:
            self.vel_y = -self.jump_power
            self.jumping = True

        # Apply gravity
        self.vel_y += GRAVITY
        if self.vel_y > 10:
            self.vel_y = 10
        dy += self.vel_y

        # Check for collision with platforms
        for platform in platforms:
            # Check for collision in x direction
            if platform.rect.colliderect(
                self.rect.x + dx, self.rect.y, self.width, self.height
            ):
                dx = 0

            # Check for collision in y direction
            if platform.rect.colliderect(
                self.rect.x, self.rect.y + dy, self.width, self.height
            ):
                # Check if below platform
                if self.vel_y < 0:
                    dy = platform.rect.bottom - self.rect.top
                    self.vel_y = 0
                # Check if above platform
                elif self.vel_y >= 0:
                    dy = platform.rect.top - self.rect.bottom
                    self.vel_y = 0
                    self.jumping = False

        # Update player position
        self.rect.x += dx
        self.rect.y += dy

        # Keep player on screen
        if self.rect.left < 0:
            self.rect.left = 0

        # Shooting cooldown
        if self.shooting_cooldown > 0:
            self.shooting_cooldown -= 1

        # Invincibility frames
        if self.invincibility > 0:
            self.invincibility -= 1
            # Flash effect
            if self.invincibility % 10 < 5:
                self.color = WHITE
            else:
                self.color = BLUE
        else:
            self.color = BLUE

        # Check collisions with enemies
        if self.invincibility <= 0:
            for enemy in enemies:
                if self.rect.colliderect(enemy.rect):
                    self.take_damage(20)

        # Check collisions with collectibles
        collected_items = []
        for collectible in collectibles:
            if self.rect.colliderect(collectible.rect):
                collected_items.append(collectible)
                if isinstance(collectible, HealthBoost):
                    self.health = min(self.max_health, self.health + collectible.amount)
                elif isinstance(collectible, ExtraLife):
                    self.lives += 1
                elif isinstance(collectible, ScoreBoost):
                    self.score += collectible.amount

        return collected_items

    def shoot(self):
        if self.shooting_cooldown <= 0:
            self.shooting_cooldown = self.shooting_cooldown_max
            bullet_x = self.rect.right if self.direction == 1 else self.rect.left
            return Projectile(bullet_x, self.rect.centery, self.direction)
        return None

    def take_damage(self, amount):
        if self.invincibility <= 0:
            self.health -= amount
            self.invincibility = self.invincibility_duration
            if self.health <= 0:
                self.lives -= 1
                if self.lives > 0:
                    self.health = self.max_health

    def draw(self, surface, scroll):
        pygame.draw.rect(
            surface,
            self.color,
            (self.rect.x - scroll, self.rect.y, self.width, self.height),
        )
        # Draw direction indicator
        eye_x = (
            self.rect.x
            - scroll
            + (self.width * 0.75 if self.direction == 1 else self.width * 0.25)
        )
        pygame.draw.circle(surface, BLACK, (eye_x, self.rect.y + 20), 5)


# Projectile class
class Projectile(GameObject):
    def __init__(self, x, y, direction):
        super().__init__(x, y, 10, 5)
        self.direction = direction
        self.speed = 15
        self.damage = 20

    def update(self, scroll_x):
        self.rect.x += self.speed * self.direction
        # Check if bullet is off screen
        return self.rect.right < scroll_x or self.rect.left > scroll_x + SCREEN_WIDTH

    def draw(self, surface, scroll):
        pygame.draw.rect(
            surface,
            YELLOW,
            (self.rect.x - scroll, self.rect.y, self.width, self.height),
        )


# Enemy class
class Enemy(GameObject):
    def __init__(self, x, y, patrol_distance=150):
        super().__init__(x, y, 50, 50)
        self.start_x = x
        self.speed = 3
        self.direction = 1
        self.patrol_distance = patrol_distance
        self.health = 50
        self.max_health = 50
        self.damage = 10
        self.color = RED

    def update(self, scroll_x):
        # Move enemy
        self.rect.x += self.speed * self.direction

        # Check patrol boundaries
        if self.rect.x >= self.start_x + self.patrol_distance:
            self.direction = -1
        elif self.rect.x <= self.start_x - self.patrol_distance:
            self.direction = 1

        # Check if enemy is on screen
        return self.rect.right < scroll_x or self.rect.left > scroll_x + SCREEN_WIDTH

    def take_damage(self, amount):
        self.health -= amount

    def is_dead(self):
        return self.health <= 0

    def draw(self, surface, scroll):
        pygame.draw.rect(
            surface,
            self.color,
            (self.rect.x - scroll, self.rect.y, self.width, self.height),
        )
        # Draw health bar
        ratio = self.health / self.max_health
        bar_width = self.width
        pygame.draw.rect(
            surface, RED, (self.rect.x - scroll, self.rect.y - 10, bar_width, 5)
        )
        pygame.draw.rect(
            surface,
            GREEN,
            (self.rect.x - scroll, self.rect.y - 10, bar_width * ratio, 5),
        )


# Boss enemy class
class BossEnemy(Enemy):
    def __init__(self, x, y):
        super().__init__(x, y, patrol_distance=250)
        self.width = 100
        self.height = 100
        self.rect = pygame.Rect(x, y, self.width, self.height)
        self.health = 200
        self.max_health = 200
        self.speed = 2
        self.damage = 30
        self.shooting_cooldown = 0
        self.shooting_cooldown_max = 60
        self.color = (150, 0, 0)  # Darker red

    def update(self, scroll_x, player_x):
        # Move towards player
        if abs(player_x - self.rect.x) > 300:  # Keep some distance
            if player_x > self.rect.x:
                self.direction = 1
            else:
                self.direction = -1

            self.rect.x += self.speed * self.direction

        # Shooting cooldown
        if self.shooting_cooldown > 0:
            self.shooting_cooldown -= 1

        # Check if boss is on screen
        return self.rect.right < scroll_x or self.rect.left > scroll_x + SCREEN_WIDTH

    def shoot(self, player_x, player_y):
        if self.shooting_cooldown <= 0:
            self.shooting_cooldown = self.shooting_cooldown_max
            # Shoot towards player
            direction = 1 if player_x > self.rect.centerx else -1
            return Projectile(self.rect.centerx, self.rect.centery, direction)
        return None


# Platform class
class Platform(GameObject):
    def __init__(self, x, y, width, height):
        super().__init__(x, y, width, height)

    def draw(self, surface, scroll):
        pygame.draw.rect(
            surface,
            (100, 50, 0),
            (self.rect.x - scroll, self.rect.y, self.width, self.height),
        )


# Base collectible class
class Collectible(GameObject):
    def __init__(self, x, y, width=30, height=30):
        super().__init__(x, y, width, height)
        self.color = WHITE

    def draw(self, surface, scroll):
        pygame.draw.rect(
            surface,
            self.color,
            (self.rect.x - scroll, self.rect.y, self.width, self.height),
        )


# Health boost collectible
class HealthBoost(Collectible):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.amount = 25
        self.color = GREEN


# Extra life collectible
class ExtraLife(Collectible):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.color = BLUE


# Score boost collectible
class ScoreBoost(Collectible):
    def __init__(self, x, y):
        super().__init__(x, y)
        self.amount = 100
        self.color = YELLOW


# Level class
class Level:
    def __init__(self, level_number):
        self.level_number = level_number
        self.platforms = []
        self.enemies = []
        self.collectibles = []
        self.boss = None
        self.level_length = 3000 if level_number < 3 else 4000
        self.level_complete = False
        self.victory = False
        self.generate_level()

    def generate_level(self):
        # Create ground
        ground_height = 50

        # Create main ground platforms with gaps
        x = 0
        while x < self.level_length:
            # Add platform
            platform_length = random.randint(3, 8) * 100
            self.platforms.append(
                Platform(
                    x, SCREEN_HEIGHT - ground_height, platform_length, ground_height
                )
            )

            # Add gap if not near the start or end
            if 500 < x < self.level_length - 800:
                x += platform_length + random.randint(100, 200)
            else:
                x += platform_length

        # Create floating platforms
        num_platforms = 15 + (self.level_number * 5)
        for _ in range(num_platforms):
            x = random.randint(400, self.level_length - 400)
            y = random.randint(SCREEN_HEIGHT - 350, SCREEN_HEIGHT - 150)
            width = random.randint(100, 200)
            self.platforms.append(Platform(x, y, width, 20))

        # Create enemies
        num_enemies = 10 + (self.level_number * 5)
        for _ in range(num_enemies):
            x = random.randint(500, self.level_length - 500)
            # Make sure enemy is on a platform
            platform_y = self.find_platform_at_x(x)
            if platform_y:
                self.enemies.append(Enemy(x, platform_y - 50))

        # Create collectibles
        num_collectibles = 5 + self.level_number
        for _ in range(num_collectibles):
            x = random.randint(400, self.level_length - 400)
            # Make sure collectible is above a platform
            platform_y = self.find_platform_at_x(x)
            if platform_y:
                y = platform_y - random.randint(100, 200)
                collectible_type = random.randint(0, 2)
                if collectible_type == 0:
                    self.collectibles.append(HealthBoost(x, y))
                elif collectible_type == 1:
                    self.collectibles.append(ExtraLife(x, y))
                else:
                    self.collectibles.append(ScoreBoost(x, y))

        # Add boss at end of level 3
        if self.level_number == 3:
            boss_x = self.level_length - 500
            platform_y = self.find_platform_at_x(boss_x)
            if platform_y:
                self.boss = BossEnemy(boss_x, platform_y - 100)

    def find_platform_at_x(self, x):
        # Find a platform at the given x coordinate
        # Returns the y coordinate of the top of the platform, or None if no platform found
        possible_platforms = [
            p for p in self.platforms if p.rect.left <= x <= p.rect.right
        ]
        if possible_platforms:
            # Return the highest platform (lowest y value)
            return min(p.rect.top for p in possible_platforms)
        return None


# Game class
class Game:
    def __init__(self):
        self.state = GameState.MENU
        self.level = None
        self.level_number = 1
        self.player = None
        self.scroll_x = 0
        self.projectiles = []
        self.enemy_projectiles = []
        self.score = 0

    def start_game(self):
        self.level_number = 1
        self.score = 0
        self.load_level(self.level_number)
        self.state = GameState.PLAYING

    def load_level(self, level_number):
        self.level = Level(level_number)
        self.player = Player(100, SCREEN_HEIGHT - 200)
        self.projectiles = []
        self.enemy_projectiles = []
        self.scroll_x = 0

    def handle_events(self):
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                return False

            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    if self.state == GameState.PLAYING:
                        self.state = GameState.MENU
                    elif self.state == GameState.MENU:
                        return False

                if self.state == GameState.MENU:
                    if event.key == pygame.K_RETURN:
                        self.start_game()

                elif (
                    self.state == GameState.GAME_OVER or self.state == GameState.VICTORY
                ):
                    if event.key == pygame.K_RETURN:
                        self.state = GameState.MENU

                elif self.state == GameState.LEVEL_COMPLETE:
                    if event.key == pygame.K_RETURN:
                        self.level_number += 1
                        if self.level_number > 3:
                            self.state = GameState.VICTORY
                        else:
                            self.load_level(self.level_number)
                            self.state = GameState.PLAYING

                # Shooting
                if self.state == GameState.PLAYING and event.key == pygame.K_f:
                    new_projectile = self.player.shoot()
                    if new_projectile:
                        self.projectiles.append(new_projectile)

        return True

    def update(self):
        if self.state == GameState.PLAYING:
            # Update player
            collected = self.player.update(
                self.level.platforms, self.level.enemies, self.level.collectibles
            )

            # Remove collected items
            for item in collected:
                self.level.collectibles.remove(item)
                if isinstance(item, ScoreBoost):
                    self.score += item.amount

            # Camera follow
            if self.player.rect.right - self.scroll_x > SCROLL_THRESH:
                self.scroll_x = self.player.rect.right - SCROLL_THRESH

            # Update projectiles
            projectiles_to_remove = []
            for projectile in self.projectiles:
                if projectile.update(self.scroll_x):
                    projectiles_to_remove.append(projectile)
                else:
                    # Check projectile collision with enemies
                    for enemy in self.level.enemies:
                        if projectile.rect.colliderect(enemy.rect):
                            enemy.take_damage(projectile.damage)
                            projectiles_to_remove.append(projectile)
                            if enemy.is_dead():
                                self.level.enemies.remove(enemy)
                                self.score += 50
                            break

                    # Check projectile collision with boss
                    if self.level.boss and projectile.rect.colliderect(
                        self.level.boss.rect
                    ):
                        self.level.boss.take_damage(projectile.damage)
                        projectiles_to_remove.append(projectile)
                        if self.level.boss.is_dead():
                            self.level.boss = None
                            self.score += 500
                            if self.level_number == 3:
                                self.level.victory = True

            # Remove projectiles
            for projectile in projectiles_to_remove:
                if projectile in self.projectiles:
                    self.projectiles.remove(projectile)

            # Update enemies
            enemies_to_remove = []
            for enemy in self.level.enemies:
                if enemy.update(self.scroll_x):
                    enemies_to_remove.append(enemy)

            for enemy in enemies_to_remove:
                if enemy in self.level.enemies:
                    self.level.enemies.remove(enemy)

            # Update boss
            if self.level.boss:
                if self.level.boss.update(self.scroll_x, self.player.rect.x):
                    self.level.boss = None
                else:
                    # Boss shooting
                    new_projectile = self.level.boss.shoot(
                        self.player.rect.x, self.player.rect.y
                    )
                    if new_projectile:
                        self.enemy_projectiles.append(new_projectile)

            # Update enemy projectiles
            enemy_projectiles_to_remove = []
            for projectile in self.enemy_projectiles:
                if projectile.update(self.scroll_x):
                    enemy_projectiles_to_remove.append(projectile)
                elif projectile.rect.colliderect(self.player.rect):
                    self.player.take_damage(projectile.damage)
                    enemy_projectiles_to_remove.append(projectile)

            for projectile in enemy_projectiles_to_remove:
                if projectile in self.enemy_projectiles:
                    self.enemy_projectiles.remove(projectile)

            # Check for level completion
            if self.player.rect.x > self.level.level_length - 200 or self.level.victory:
                self.state = GameState.LEVEL_COMPLETE
                self.score += 1000  # Level completion bonus

            # Check for game over
            if self.player.lives <= 0 or self.player.rect.top > SCREEN_HEIGHT:
                self.state = GameState.GAME_OVER

    def draw(self):
        screen.fill((135, 206, 235))  # Sky blue background

        if self.state == GameState.MENU:
            draw_text("SPACE ADVENTURE", big_font, WHITE, SCREEN_WIDTH // 2 - 250, 200)
            draw_text("Press ENTER to start", font, WHITE, SCREEN_WIDTH // 2 - 130, 300)
            draw_text(
                "Move: LEFT/RIGHT, Jump: SPACE, Shoot: F",
                font,
                WHITE,
                SCREEN_WIDTH // 2 - 250,
                400,
            )

        elif self.state == GameState.PLAYING or self.state == GameState.LEVEL_COMPLETE:
            # Draw platforms
            for platform in self.level.platforms:
                platform.draw(screen, self.scroll_x)

            # Draw collectibles
            for collectible in self.level.collectibles:
                collectible.draw(screen, self.scroll_x)

            # Draw enemies
            for enemy in self.level.enemies:
                enemy.draw(screen, self.scroll_x)

            # Draw boss
            if self.level.boss:
                self.level.boss.draw(screen, self.scroll_x)

            # Draw projectiles
            for projectile in self.projectiles:
                projectile.draw(screen, self.scroll_x)

            # Draw enemy projectiles
            for projectile in self.enemy_projectiles:
                projectile.draw(screen, self.scroll_x)

            # Draw player
            self.player.draw(screen, self.scroll_x)

            # Draw UI
            draw_health_bar(20, 20, self.player.health, self.player.max_health)
            draw_text(f"Lives: {self.player.lives}", font, WHITE, 20, 40)
            draw_text(f"Score: {self.score}", font, WHITE, 20, 70)
            draw_text(f"Level: {self.level_number}", font, WHITE, 20, 100)

            # Draw level complete message
            if self.state == GameState.LEVEL_COMPLETE:
                draw_text(
                    "LEVEL COMPLETE!", big_font, WHITE, SCREEN_WIDTH // 2 - 250, 250
                )
                draw_text(
                    "Press ENTER to continue", font, WHITE, SCREEN_WIDTH // 2 - 150, 350
                )

        elif self.state == GameState.GAME_OVER:
            draw_text("GAME OVER", big_font, RED, SCREEN_WIDTH // 2 - 180, 250)
            draw_text(
                f"Final Score: {self.score}", font, WHITE, SCREEN_WIDTH // 2 - 100, 350
            )
            draw_text(
                "Press ENTER to return to menu",
                font,
                WHITE,
                SCREEN_WIDTH // 2 - 180,
                450,
            )

        elif self.state == GameState.VICTORY:
            draw_text("VICTORY!", big_font, YELLOW, SCREEN_WIDTH // 2 - 150, 200)
            draw_text(
                "You have completed all levels!",
                font,
                WHITE,
                SCREEN_WIDTH // 2 - 180,
                300,
            )
            draw_text(
                f"Final Score: {self.score}", font, WHITE, SCREEN_WIDTH // 2 - 100, 350
            )
            draw_text(
                "Press ENTER to return to menu",
                font,
                WHITE,
                SCREEN_WIDTH // 2 - 180,
                450,
            )

        # Update display
        pygame.display.flip()


# Main function
def main():
    # Create game instance
    game = Game()
    running = True

    # Main game loop
    while running:
        # Handle events
        running = game.handle_events()

        # Update game state
        game.update()

        # Draw everything
        game.draw()

        # Cap the frame rate
        clock.tick(FPS)

    pygame.quit()
    sys.exit()


if __name__ == "__main__":
    main()
