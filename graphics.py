import pygame
from typing import Union
from typing import Optional

import pygame
import os


class ContentManager:
    """
    Substituto simples para o Content Pipeline do XNA.
    Garante que texturas e sons sejam carregados do disco apenas uma vez.
    """
    _texture_cache = {}
    _sound_cache = {}

    ROOT_DIRECTORY = "Content"

    @classmethod
    def load_texture(cls, file_path: str) -> pygame.Surface:
        full_path = os.path.join(cls.ROOT_DIRECTORY, file_path)

        if full_path not in cls._texture_cache:
            try:
                cls._texture_cache[full_path] = pygame.image.load(full_path).convert_alpha()
            except FileNotFoundError:
                print(f"Erro fatal: Não foi possível encontrar a textura em: {full_path}")
                raise

        return cls._texture_cache[full_path]

    @classmethod
    def load_sound(cls, file_path: str) -> pygame.mixer.Sound:
        """Carrega e faz cache de efeitos sonoros (.wav, .ogg)."""
        full_path = os.path.join(cls.ROOT_DIRECTORY, file_path)

        if full_path not in cls._sound_cache:
            try:
                cls._sound_cache[full_path] = pygame.mixer.Sound(full_path)
            except FileNotFoundError:
                print(f"Erro fatal: Não foi possível encontrar o áudio em: {full_path}")
                raise

        return cls._sound_cache[full_path]

    @classmethod
    def get_full_path(cls, file_path: str) -> str:
        """Retorna o caminho absoluto do arquivo. Útil para streaming de música."""
        return os.path.join(cls.ROOT_DIRECTORY, file_path)


class Animation:
    """
    Representa uma textura animada.

    Atualmente, esta classe assume que cada quadro da animação é
    tão largo quanto a animação é alta. O número de quadros na
    animação é inferido a partir disso.
    """

    def __init__(self, texture_or_path: Union[pygame.Surface, str], frame_time: float, is_looping: bool):
        """
        Constrói uma nova animação. Pode receber diretamente a Surface (como no XNA)
        ou o caminho do arquivo para ser resolvido pelo ContentManager.
        """
        # Melhoria de carregamento: aceita o caminho da string e gerencia o cache
        if isinstance(texture_or_path, str):
            self._texture = ContentManager.load_texture(texture_or_path)
        else:
            self._texture = texture_or_path

        self._frame_time = frame_time
        self._is_looping = is_looping

    @property
    def texture(self) -> pygame.Surface:
        """Todos os quadros na animação organizados horizontalmente."""
        return self._texture

    @property
    def frame_time(self) -> float:
        """Tempo de duração para exibir cada quadro."""
        return self._frame_time

    @property
    def is_looping(self) -> bool:
        """Quando o fim da animação for alcançado, ela deve continuar tocando do início?"""
        return self._is_looping

    @property
    def frame_height(self) -> int:
        """Obtém a altura de um quadro na animação."""
        return self._texture.get_height()

    @property
    def frame_width(self) -> int:
        """Obtém a largura de um quadro na animação (Assume quadros quadrados)."""
        return self._texture.get_height()

    @property
    def frame_count(self) -> int:
        """Obtém o número de quadros na animação."""
        # Operador '//' força a divisão inteira em Python
        return self._texture.get_width() // self.frame_width

class AnimationPlayer:
    """
    Controla a reprodução de uma Animação.
    No XNA isso era uma struct (tipo de valor), mas em Python
    implementamos como uma classe padrão.
    """

    def __init__(self):
        self._animation: Optional['Animation'] = None
        self._frame_index: int = 0
        self._time: float = 0.0

    @property
    def animation(self) -> Optional['Animation']:
        """Obtém a animação que está sendo reproduzida no momento."""
        return self._animation

    @property
    def frame_index(self) -> int:
        """Obtém o índice do quadro atual na animação."""
        return self._frame_index

    @property
    def origin(self) -> pygame.math.Vector2:
        """Obtém a origem da textura no centro inferior de cada quadro."""
        if self._animation is None:
            return pygame.math.Vector2(0, 0)
        # Utiliza o Vector2 nativo do Pygame para operações matemáticas otimizadas
        return pygame.math.Vector2(self._animation.frame_width / 2.0, self._animation.frame_height)

    def play_animation(self, animation: 'Animation'):
        """Inicia ou continua a reprodução de uma animação."""
        # Se esta animação já estiver rodando, não a reinicie. (Compara referência)
        if self._animation is animation:
            return

        # Inicia a nova animação.
        self._animation = animation
        self._frame_index = 0
        self._time = 0.0

    def draw(self, dt: float, screen: pygame.Surface, position: pygame.math.Vector2, flip_x: bool = False):
        """
        Avança a posição do tempo e desenha o quadro atual da animação.

        :param dt: Delta time em segundos (substitui o GameTime).
        :param screen: A superfície onde a animação será desenhada (substitui o SpriteBatch).
        :param position: Posição onde a base/origem da animação ficará.
        :param flip_x: Booleano para inverter a sprite (substitui o SpriteEffects).
        """
        if self._animation is None:
            raise RuntimeError("Nenhuma animação está sendo reproduzida no momento.")

        # Processa a passagem do tempo utilizando o delta time
        self._time += dt
        while self._time > self._animation.frame_time:
            self._time -= self._animation.frame_time

            # Avança o índice do quadro; em loop ou travando no limite
            if self._animation.is_looping:
                self._frame_index = (self._frame_index + 1) % self._animation.frame_count
            else:
                self._frame_index = min(self._frame_index + 1, self._animation.frame_count - 1)

        # Calcula a área (source rectangle) do quadro atual na spritesheet
        frame_width = self._animation.frame_width
        frame_height = self._animation.frame_height
        source_rect = pygame.Rect(self._frame_index * frame_width, 0, frame_width, frame_height)

        # Extrai apenas o frame atual da textura completa
        current_frame = self._animation.texture.subsurface(source_rect)

        # Aplica o espelhamento se necessário (Equivalente ao SpriteEffects.FlipHorizontally)
        if flip_x:
            current_frame = pygame.transform.flip(current_frame, True, False)

        # O XNA subtrai o Origin (centro inferior) automaticamente na chamada do SpriteBatch.
        # No Pygame, o blit sempre ocorre a partir do canto superior esquerdo (Top-Left).
        # Precisamos calcular essa diferença manualmente:
        origin = self.origin
        top_left_x = position.x - origin.x
        top_left_y = position.y - origin.y

        # Desenha o quadro na tela
        screen.blit(current_frame, (top_left_x, top_left_y))