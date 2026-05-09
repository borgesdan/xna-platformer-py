import pygame
import math
from typing import Optional
from graphics import ContentManager, Animation, AnimationPlayer
from tile import Tile, TileCollision
from geometry import clamp, get_intersection_depth


class Player:
    """O nosso destemido aventureiro!"""

    # Constantes para controle de movimento horizontal
    MOVE_ACCELERATION: float = 13000.0
    MAX_MOVE_SPEED: float = 1750.0
    GROUND_DRAG_FACTOR: float = 0.48
    AIR_DRAG_FACTOR: float = 0.58

    # Constantes para controle de movimento vertical
    MAX_JUMP_TIME: float = 0.35
    JUMP_LAUNCH_VELOCITY: float = -3500.0
    GRAVITY_ACCELERATION: float = 3400.0
    MAX_FALL_SPEED: float = 550.0
    JUMP_CONTROL_POWER: float = 0.14

    def __init__(self, level, position: pygame.math.Vector2):
        self.level = level

        # Animações
        self.idle_animation: Optional[Animation] = None
        self.run_animation: Optional[Animation] = None
        self.jump_animation: Optional[Animation] = None
        self.celebrate_animation: Optional[Animation] = None
        self.die_animation: Optional[Animation] = None

        # Estado de renderização
        self.flip_x: bool = False
        self.sprite: AnimationPlayer = AnimationPlayer()

        # Áudios
        self.killed_sound: Optional[pygame.mixer.Sound] = None
        self.jump_sound: Optional[pygame.mixer.Sound] = None
        self.fall_sound: Optional[pygame.mixer.Sound] = None

        # Estado da Física
        self.position: pygame.math.Vector2 = pygame.math.Vector2(0, 0)
        self.velocity: pygame.math.Vector2 = pygame.math.Vector2(0, 0)
        self.is_alive: bool = True
        self.is_on_ground: bool = False
        self._previous_bottom: float = 0.0

        # Estado de Input e Pulo
        self.movement: float = 0.0
        self.is_jumping: bool = False
        self.was_jumping: bool = False
        self.jump_time: float = 0.0

        self._local_bounds: pygame.Rect = pygame.Rect(0, 0, 0, 0)

        self.load_content()
        self.reset(position)

    @property
    def bounding_rectangle(self) -> pygame.Rect:
        """Obtém um retângulo que delimita este jogador no espaço do mundo."""
        # math.floor ou round() para converter as coordenadas espaciais float para int do Rect
        left = round(self.position.x - self.sprite.origin.x) + self._local_bounds.x
        top = round(self.position.y - self.sprite.origin.y) + self._local_bounds.y
        return pygame.Rect(left, top, self._local_bounds.width, self._local_bounds.height)

    def load_content(self):
        """Carrega a spritesheet do jogador e os sons."""
        # Carrega texturas animadas usando o nosso ContentManager
        self.idle_animation = Animation("Sprites/Player/Idle.png", 0.1, True)
        self.run_animation = Animation("Sprites/Player/Run.png", 0.1, True)
        self.jump_animation = Animation("Sprites/Player/Jump.png", 0.1, False)
        self.celebrate_animation = Animation("Sprites/Player/Celebrate.png", 0.1, False)
        self.die_animation = Animation("Sprites/Player/Die.png", 0.1, False)

        # Calcula os limites (bounds) dentro do tamanho da textura
        width = int(self.idle_animation.frame_width * 0.4)
        left = (self.idle_animation.frame_width - width) // 2
        height = int(self.idle_animation.frame_width * 0.8)
        top = self.idle_animation.frame_height - height
        self._local_bounds = pygame.Rect(left, top, width, height)

        # Carrega sons (Assumindo que você inicializou o pygame.mixer)
        self.killed_sound = ContentManager.load_sound("Sounds/STAY_SE_00016.wav")
        self.jump_sound = ContentManager.load_sound("Sounds/STAY_SE_00010.wav")
        self.fall_sound = ContentManager.load_sound("Sounds/STAY_SE_00016.wav")

    def reset(self, position: pygame.math.Vector2):
        """Ressuscita e reposiciona o jogador."""
        self.position = pygame.math.Vector2(position)
        self.velocity = pygame.math.Vector2(0, 0)
        self.is_alive = True
        self.sprite.play_animation(self.idle_animation)

    def update(self, dt: float):
        """
        Lida com input, executa a física e anima a sprite do jogador.
        Substitui o GameTime pelo dt (delta time em segundos).
        """
        self.get_input()
        self.apply_physics(dt)

        if self.is_alive and self.is_on_ground:
            # Seleciona a animação baseada na velocidade horizontal
            if abs(self.velocity.x) - 0.02 > 0:
                self.sprite.play_animation(self.run_animation)
            else:
                self.sprite.play_animation(self.idle_animation)

        # Limpa o input
        self.movement = 0.0
        self.is_jumping = False

    def get_input(self):
        """Obtém comandos de movimento horizontal e pulo (Somente Desktop)."""
        keys = pygame.key.get_pressed()

        # Movimento Horizontal (Override digital)
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.movement = -1.0
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.movement = 1.0

        # Pulo
        self.is_jumping = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]

    def apply_physics(self, dt: float):
        """Atualiza a velocidade e posição do jogador baseado em input, gravidade, etc."""
        previous_position = pygame.math.Vector2(self.position)

        # Aceleração horizontal e gravidade
        self.velocity.x += self.movement * self.MOVE_ACCELERATION * dt
        self.velocity.y = clamp(self.velocity.y + self.GRAVITY_ACCELERATION * dt, -self.MAX_FALL_SPEED,
                                self.MAX_FALL_SPEED)

        self.velocity.y = self.do_jump(self.velocity.y, dt)

        # Aplica pseudo-atrito horizontal
        if self.is_on_ground:
            self.velocity.x *= self.GROUND_DRAG_FACTOR
        else:
            self.velocity.x *= self.AIR_DRAG_FACTOR

        # Impede que o jogador corra mais rápido que a velocidade máxima
        self.velocity.x = clamp(self.velocity.x, -self.MAX_MOVE_SPEED, self.MAX_MOVE_SPEED)

        # Aplica a velocidade à posição
        self.position += self.velocity * dt
        self.position.x = round(self.position.x)
        self.position.y = round(self.position.y)

        # Resolve colisões com o cenário
        self.handle_collisions()

        # Se a colisão nos parou, zera a velocidade naquele eixo
        if self.position.x == previous_position.x:
            self.velocity.x = 0
        if self.position.y == previous_position.y:
            self.velocity.y = 0

    def do_jump(self, velocity_y: float, dt: float) -> float:
        """Calcula a velocidade Y baseada na curva de pulo."""
        if self.is_jumping:
            # Inicia ou continua o pulo
            if (not self.was_jumping and self.is_on_ground) or self.jump_time > 0.0:
                if self.jump_time == 0.0:
                    self.jump_sound.play()

                self.jump_time += dt
                self.sprite.play_animation(self.jump_animation)

            # Se estamos na ascensão do pulo
            if 0.0 < self.jump_time <= self.MAX_JUMP_TIME:
                # Curva de poder para o controle preciso do pulo
                velocity_y = self.JUMP_LAUNCH_VELOCITY * (
                            1.0 - math.pow(self.jump_time / self.MAX_JUMP_TIME, self.JUMP_CONTROL_POWER))
            else:
                # Alcançou o ápice do pulo
                self.jump_time = 0.0
        else:
            # Cancela um pulo em progresso ou continua sem pular
            self.jump_time = 0.0

        self.was_jumping = self.is_jumping
        return velocity_y

    def handle_collisions(self):
        """Detecta e resolve todas as colisões entre o jogador e os blocos vizinhos."""
        bounds = self.bounding_rectangle

        # Mapeamento para o grid da matriz do Level
        left_tile = math.floor(bounds.left / Tile.WIDTH)
        right_tile = math.ceil(bounds.right / Tile.WIDTH) - 1
        top_tile = math.floor(bounds.top / Tile.HEIGHT)
        bottom_tile = math.ceil(bounds.bottom / Tile.HEIGHT) - 1

        self.is_on_ground = False

        # Verifica os blocos vizinhos
        for y in range(top_tile, bottom_tile + 1):
            for x in range(left_tile, right_tile + 1):
                collision = self.level.get_collision(x, y)

                if collision != TileCollision.PASSABLE:
                    tile_bounds = self.level.get_bounds(x, y)
                    depth = get_intersection_depth(bounds, tile_bounds)

                    if depth != pygame.math.Vector2(0, 0):
                        abs_depth_x = abs(depth.x)
                        abs_depth_y = abs(depth.y)

                        # Resolve a colisão ao longo do eixo mais raso
                        if abs_depth_y < abs_depth_x or collision == TileCollision.PLATFORM:
                            # Se cruzamos o topo do bloco, estamos no chão
                            if self._previous_bottom <= tile_bounds.top:
                                self.is_on_ground = True

                            # Ignora plataformas, a menos que estejamos no chão (caindo sobre elas)
                            if collision == TileCollision.IMPASSABLE or self.is_on_ground:
                                self.position.y += depth.y
                                bounds = self.bounding_rectangle

                        elif collision == TileCollision.IMPASSABLE:
                            # Resolve a colisão ao longo do eixo X
                            self.position.x += depth.x
                            bounds = self.bounding_rectangle

        self._previous_bottom = bounds.bottom

    def on_killed(self, killed_by):  # killed_by do tipo 'Enemy' (ou None)
        self.is_alive = False
        if killed_by is not None:
            self.killed_sound.play()
        else:
            self.fall_sound.play()

        self.sprite.play_animation(self.die_animation)

    def on_reached_exit(self):
        self.sprite.play_animation(self.celebrate_animation)

    def draw(self, dt: float, screen: pygame.Surface):
        # Espelha a sprite baseado na direção do movimento
        if self.velocity.x > 0:
            self.flip_x = True
        elif self.velocity.x < 0:
            self.flip_x = False

        self.sprite.draw(dt, screen, self.position, self.flip_x)