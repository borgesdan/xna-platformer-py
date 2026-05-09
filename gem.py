import pygame
import math
from typing import Optional
from geometry import Circle
from tile import Tile
from graphics import ContentManager


class Gem:
    PONTO: int = 30
    # Equivalente ao Color.Yellow
    COR: pygame.Color = pygame.Color(255, 255, 0)

    def __init__(self, level, position: pygame.math.Vector2):
        self.level = level

        # A gema é animada a partir de uma posição base ao longo do eixo Y.
        self.base_position: pygame.math.Vector2 = pygame.math.Vector2(position)
        self.bounce: float = 0.0

        self.textura: Optional[pygame.Surface] = None
        self.origin: pygame.math.Vector2 = pygame.math.Vector2(0, 0)
        self.som_obteve: Optional[pygame.mixer.Sound] = None

        self.carregar_conteudo()

    @property
    def posicao(self) -> pygame.math.Vector2:
        """Obtém a posição atual desta gema no espaço do mundo."""
        return self.base_position + pygame.math.Vector2(0.0, self.bounce)

    @property
    def limites(self) -> Circle:
        return Circle(self.posicao, Tile.WIDTH / 3.0)

    def carregar_conteudo(self):
        """Carrega a textura da gema, aplica a cor e carrega o som."""
        base_texture = ContentManager.load_texture("Sprites/Item.png")

        # OTIMIZAÇÃO: Copiamos a textura base e a tingimos com a cor amarela no momento
        # do carregamento. O 'BLEND_RGBA_MULT' multiplica os pixels, preservando transparência.
        self.textura = base_texture.copy()
        self.textura.fill(self.COR, special_flags=pygame.BLEND_RGBA_MULT)

        self.origin = pygame.math.Vector2(self.textura.get_width() / 2.0, self.textura.get_height() / 2.0)

        # Agora o áudio passa pelo gerenciador e ganha o prefixo "Content/"
        self.som_obteve = ContentManager.load_sound("Sounds/STAY_SE_00033.wav")

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
        self.bounce = math.sin(t) * BOUNCE_HEIGHT * self.textura.get_height()

    def on_collected(self, collected_by):
        self.som_obteve.play()

    def draw(self, screen: pygame.Surface):
        # Assim como no Player, precisamos compensar o origin, pois o Pygame
        # desenha a partir do canto superior esquerdo (Top-Left).
        top_left_x = self.posicao.x - self.origin.x
        top_left_y = self.posicao.y - self.origin.y

        screen.blit(self.textura, (top_left_x, top_left_y))