import pygame
from enum import IntEnum
from dataclasses import dataclass
from typing import Optional, ClassVar

class TileCollision(IntEnum):
    """Controla a detecção de colisão e o comportamento de resposta de um tile."""
    PASSABLE = 0   # Não bloqueia o jogador
    IMPASSABLE = 1 # Completamente sólido
    PLATFORM = 2   # Permite pular por baixo, mas colide caindo por cima


@dataclass
class Tile:
    """Armazena a aparência e o comportamento de colisão de um tile."""
    # Usamos Optional pois blocos PASSABLE geralmente não possuem textura (espaço vazio)
    texture: Optional[pygame.Surface]
    collision: TileCollision

    # ClassVar avisa ao dataclass que isso é um "static readonly" e não uma propriedade de instância
    WIDTH: ClassVar[int] = 40
    HEIGHT: ClassVar[int] = 32
    SIZE: ClassVar[pygame.math.Vector2] = pygame.math.Vector2(WIDTH, HEIGHT)