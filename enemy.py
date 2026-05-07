import pygame
import math
from enum import IntEnum
from typing import Optional
from graphics import Animation, AnimationPlayer
from tile import Tile, TileCollision


class FaceDirection(IntEnum):
    """Direção para qual a entidade está olhando no eixo X."""
    LEFT = -1
    RIGHT = 1


class Enemy:
    """Um monstro que está impedindo o progresso do nosso destemido aventureiro."""

    # Tempo para esperar antes de virar
    MAX_WAIT_TIME: float = 0.5
    # A velocidade na qual o inimigo se move no eixo X
    MOVE_SPEED: float = 64.0

    def __init__(self, level, position: pygame.math.Vector2, sprite_set: str):
        self.level = level
        self.position = pygame.math.Vector2(position)

        self._local_bounds = pygame.Rect(0, 0, 0, 0)

        # Animações
        self.run_animation: Optional[Animation] = None
        self.idle_animation: Optional[Animation] = None
        self.sprite = AnimationPlayer()

        # Estado da IA
        self.direction = FaceDirection.LEFT
        self.wait_time: float = 0.0

        self.load_content(sprite_set)

    @property
    def bounding_rectangle(self) -> pygame.Rect:
        """Obtém um retângulo que delimita este inimigo no espaço do mundo."""
        left = round(self.position.x - self.sprite.origin.x) + self._local_bounds.x
        top = round(self.position.y - self.sprite.origin.y) + self._local_bounds.y
        return pygame.Rect(left, top, self._local_bounds.width, self._local_bounds.height)

    def load_content(self, sprite_set: str):
        """Carrega a spritesheet específica do inimigo e calcula sua caixa de colisão."""
        base_path = f"Sprites/{sprite_set}/"

        # Carrega as animações passando o caminho para o ContentManager embutido
        self.run_animation = Animation(f"{base_path}Run.png", 0.1, True)
        self.idle_animation = Animation(f"{base_path}Idle.png", 0.15, True)
        self.sprite.play_animation(self.idle_animation)

        # Calcula os limites (bounds) dentro do tamanho da textura.
        # No XNA era feito um cast (int) no double. Usamos int() ou // em Python.
        width = int(self.idle_animation.frame_width * 0.35)
        left = (self.idle_animation.frame_width - width) // 2
        height = int(self.idle_animation.frame_height * 0.7)
        top = self.idle_animation.frame_height - height
        self._local_bounds = pygame.Rect(left, top, width, height)

    def update(self, dt: float):
        """Patrulha de um lado para o outro na plataforma, esperando nas extremidades."""

        # Calcula a posição do tile baseado no lado para o qual estamos andando
        pos_x = self.position.x + (self._local_bounds.width / 2.0) * self.direction.value

        # Subtrai a direção para compensar o limite do tile
        tile_x = math.floor(pos_x / Tile.WIDTH) - self.direction.value
        tile_y = math.floor(self.position.y / Tile.HEIGHT)

        if self.wait_time > 0:
            # Espera por um tempo
            self.wait_time = max(0.0, self.wait_time - dt)
            if self.wait_time <= 0.0:
                # Vira para o outro lado multiplicando por -1
                self.direction = FaceDirection(-self.direction.value)
        else:
            # Verifica se vamos bater em uma parede ou cair do penhasco no próximo tile
            # Adicionei checagem de limites simples caso o inimigo chegue na borda absoluta da matriz
            next_tile_x = tile_x + self.direction.value

            # Precisamos garantir que não acessaremos índices fora da matriz no Level
            try:
                wall_check = self.level.get_collision(next_tile_x, tile_y - 1)
                floor_check = self.level.get_collision(next_tile_x, tile_y)
            except IndexError:
                # Se tentar ler fora do mapa, trata como abismo/parede
                wall_check = TileCollision.IMPASSABLE
                floor_check = TileCollision.PASSABLE

            if wall_check == TileCollision.IMPASSABLE or floor_check == TileCollision.PASSABLE:
                self.wait_time = self.MAX_WAIT_TIME
            else:
                # Move na direção atual
                velocity = pygame.math.Vector2(self.direction.value * self.MOVE_SPEED * dt, 0.0)
                self.position += velocity

    def draw(self, dt: float, screen: pygame.Surface):
        """Desenha o inimigo animado."""

        # Para de correr quando o jogo está pausado (tempo esgotado, jogador morto) ou antes de virar.
        # Assumimos que o level possuirá essas propriedades expostas (time_remaining, reached_exit)
        if (not self.level.player.is_alive or
                self.level.reached_exit or
                self.level.time_remaining <= 0.0 or
                self.wait_time > 0):

            self.sprite.play_animation(self.idle_animation)
        else:
            self.sprite.play_animation(self.run_animation)

        # Pygame flip aceita booleanos (flip_x, flip_y).
        # Se a direção for RIGHT (1), vira horizontalmente (True).
        flip_x = (self.direction.value > 0)

        self.sprite.draw(dt, screen, self.position, flip_x=flip_x)