import pygame
import math
from typing import Optional
from geometry import Circle
from tile import Tile
from graphics import ContentManager


class Gem:
    """Um item valioso que o jogador pode coletar."""

    POINT_VALUE: int = 30
    # Equivalente ao Color.Yellow
    COLOR: pygame.Color = pygame.Color(255, 255, 0)

    def __init__(self, level, position: pygame.math.Vector2):
        self.level = level

        # A gema é animada a partir de uma posição base ao longo do eixo Y.
        self.base_position: pygame.math.Vector2 = pygame.math.Vector2(position)
        self.bounce: float = 0.0

        self.texture: Optional[pygame.Surface] = None
        self.origin: pygame.math.Vector2 = pygame.math.Vector2(0, 0)
        self.collected_sound: Optional[pygame.mixer.Sound] = None

        self.load_content()

    @property
    def position(self) -> pygame.math.Vector2:
        """Obtém a posição atual desta gema no espaço do mundo."""
        return self.base_position + pygame.math.Vector2(0.0, self.bounce)

    @property
    def bounding_circle(self) -> Circle:
        """Obtém um círculo que delimita esta gema no espaço do mundo."""
        # Utiliza a nossa classe Circle criada no geometry.py
        return Circle(self.position, Tile.WIDTH / 3.0)

    def load_content(self):
        """Carrega a textura da gema, aplica a cor e carrega o som."""
        base_texture = ContentManager.load_texture("Sprites/Gem.png")

        # OTIMIZAÇÃO: Copiamos a textura base e a tingimos com a cor amarela no momento
        # do carregamento. O 'BLEND_RGBA_MULT' multiplica os pixels, preservando transparência.
        self.texture = base_texture.copy()
        self.texture.fill(self.COLOR, special_flags=pygame.BLEND_RGBA_MULT)

        self.origin = pygame.math.Vector2(self.texture.get_width() / 2.0, self.texture.get_height() / 2.0)

        # Agora o áudio passa pelo gerenciador e ganha o prefixo "Content/"
        self.collected_sound = ContentManager.load_sound("Sounds/GemCollected.wav")

    def update(self, total_time: float):
        """
        Pula para cima e para baixo no ar para atrair os jogadores a coletá-la.

        :param total_time: Tempo total de jogo em segundos (equivalente ao TotalGameTime.TotalSeconds).
        """
        # Constantes de controle do pulo
        BOUNCE_HEIGHT: float = 0.18
        BOUNCE_RATE: float = 3.0
        BOUNCE_SYNC: float = -0.75

        # Pula ao longo de uma curva seno com o passar do tempo.
        # Inclui a coordenada X para que as gemas vizinhas pulem em um belo padrão de onda.
        t = (total_time * BOUNCE_RATE) + (self.base_position.x * BOUNCE_SYNC)

        # O XNA usava Texture.Height para ditar a altura do pulo proporcional ao tamanho da imagem.
        self.bounce = math.sin(t) * BOUNCE_HEIGHT * self.texture.get_height()

    def on_collected(self, collected_by):  # collected_by do tipo 'Player'
        """Chamado quando esta gema foi coletada por um jogador."""
        self.collected_sound.play()

    def draw(self, screen: pygame.Surface):
        """Desenha a gema na tela."""
        # Assim como no Player, precisamos compensar o origin, pois o Pygame
        # desenha a partir do canto superior esquerdo (Top-Left).
        top_left_x = self.position.x - self.origin.x
        top_left_y = self.position.y - self.origin.y

        screen.blit(self.texture, (top_left_x, top_left_y))