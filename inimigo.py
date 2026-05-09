import pygame
import math
from enum import IntEnum
from typing import Optional
from graphics import Animation, AnimationPlayer
from tile import Tile, TileCollision


class Direcao(IntEnum):
    """Direção para qual a entidade está olhando no eixo X."""
    LEFT = -1
    RIGHT = 1


class Inimigo:
    """Um monstro que está impedindo o progresso do nosso destemido aventureiro."""

    # Tempo para esperar antes de virar
    TEMPO_ESPERA: float = 0.5
    # A velocidade na qual o inimigo se move no eixo X
    VELOCIDADE_MOVEMENTO: float = 64.0

    def __init__(self, level, position: pygame.math.Vector2, sprite_set: str):
        self.level = level
        self.posicao = pygame.math.Vector2(position)

        self._local_bounds = pygame.Rect(0, 0, 0, 0)

        # Animações
        self.animacao_andar: Optional[Animation] = None
        self.animacao_espera: Optional[Animation] = None
        self.sprite = AnimationPlayer()

        # Estado da IA
        self.direcao = Direcao.LEFT
        self.tempo_espera: float = 0.0

        self.carregar_conteudo(sprite_set)

    @property
    def retangulo_limite(self) -> pygame.Rect:
        """Obtém um retângulo que delimita este inimigo no espaço do mundo."""
        esquerdo = round(self.posicao.x - self.sprite.origin.x) + self._local_bounds.x
        topo = round(self.posicao.y - self.sprite.origin.y) + self._local_bounds.y
        return pygame.Rect(esquerdo, topo, self._local_bounds.width, self._local_bounds.height)

    def carregar_conteudo(self, sprite_set: str):
        """Carrega a spritesheet específica do inimigo e calcula sua caixa de colisão."""
        base_path = f"Sprites/{sprite_set}/"

        # Carrega as animações passando o caminho para o ContentManager embutido
        self.animacao_andar = Animation(f"{base_path}Run.png", 0.1, True)
        self.animacao_espera = Animation(f"{base_path}Idle.png", 0.15, True)
        self.sprite.play_animation(self.animacao_espera)

        largura = int(self.animacao_espera.frame_width * 0.35)
        esquerda = (self.animacao_espera.frame_width - largura) // 2
        altura = int(self.animacao_espera.frame_height * 0.7)
        top = self.animacao_espera.frame_height - altura
        self._local_bounds = pygame.Rect(esquerda, top, largura, altura)

    def update(self, dt: float):
        # Calcula a posição do tile baseado no lado para o qual estamos andando
        pos_x = self.posicao.x + (self._local_bounds.width / 2.0) * self.direcao.value

        # Subtrai a direção para compensar o limite do tile
        tile_x = math.floor(pos_x / Tile.WIDTH) - self.direcao.value
        tile_y = math.floor(self.posicao.y / Tile.HEIGHT)

        if self.tempo_espera > 0:
            # Espera por um tempo
            self.tempo_espera = max(0.0, self.tempo_espera - dt)
            if self.tempo_espera <= 0.0:
                # Vira para o outro lado multiplicando por -1
                self.direcao = Direcao(-self.direcao.value)
        else:
            # Verifica se vamos bater em uma parede ou cair do penhasco no próximo tile
            # Adicionei checagem de limites simples caso o inimigo chegue na borda absoluta da matriz
            next_tile_x = tile_x + self.direcao.value

            # Precisamos garantir que não acessaremos índices fora da matriz no Level
            try:
                wall_check = self.level.get_collision(next_tile_x, tile_y - 1)
                floor_check = self.level.get_collision(next_tile_x, tile_y)
            except IndexError:
                # Se tentar ler fora do mapa, trata como abismo/parede
                wall_check = TileCollision.IMPASSABLE
                floor_check = TileCollision.PASSABLE

            if wall_check == TileCollision.IMPASSABLE or floor_check == TileCollision.PASSABLE:
                self.tempo_espera = self.TEMPO_ESPERA
            else:
                # Move na direção atual
                velocity = pygame.math.Vector2(self.direcao.value * self.VELOCIDADE_MOVEMENTO * dt, 0.0)
                self.posicao += velocity

    def draw(self, dt: float, screen: pygame.Surface):
        # Para de correr quando o jogo está pausado (tempo esgotado, jogador morto) ou antes de virar.
        # Assumimos que o level possuirá essas propriedades expostas (time_remaining, reached_exit)
        if (not self.level.player.is_alive or
                self.level.reached_exit or
                self.level.time_remaining <= 0.0 or
                self.tempo_espera > 0):

            self.sprite.play_animation(self.animacao_espera)
        else:
            self.sprite.play_animation(self.animacao_andar)

        # Pygame flip aceita booleanos (flip_x, flip_y).
        # Se a direção for RIGHT (1), vira horizontalmente (True).
        flip_x = (self.direcao.value > 0)

        self.sprite.draw(dt, screen, self.posicao, flip_x=flip_x)