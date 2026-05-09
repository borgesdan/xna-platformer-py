import pygame
import math
from typing import Optional
from graphics import ContentManager, Animation, AnimationPlayer
from tile import Tile, TileCollision
from geometry import clamp, get_intersection_depth


class Player:
    """O nosso destemido aventureiro!"""

    # Constantes para controle de movimento horizontal
    ACELERACAO: float = 13000.0
    MAXIMO_VELOCIDADE: float = 1750.0
    FATOR_TERRA: float = 0.48
    FATOR_AR: float = 0.58

    # Constantes para controle de movimento vertical
    TEMPO_PULO: float = 0.35
    PULO_VELOCIDADE: float = -3500.0
    GRAVIDADE: float = 3400.0
    QUEDA_VELOCIDADE: float = 550.0
    PULO_POTENCIA: float = 0.14

    def __init__(self, level, position: pygame.math.Vector2):
        self.level = level

        # Animações
        self.anim_espera: Optional[Animation] = None
        self.andar_anim: Optional[Animation] = None
        self.pulo_anim: Optional[Animation] = None
        self.vitoria_anim: Optional[Animation] = None
        self.morte_anim: Optional[Animation] = None

        # Estado de renderização
        self.flip_x: bool = False
        self.sprite: AnimationPlayer = AnimationPlayer()

        # Áudios
        self.som_perdeu: Optional[pygame.mixer.Sound] = None
        self.som_pulo: Optional[pygame.mixer.Sound] = None
        self.som_queda: Optional[pygame.mixer.Sound] = None

        # Estado da Física
        self.posicao: pygame.math.Vector2 = pygame.math.Vector2(0, 0)
        self.velocidade: pygame.math.Vector2 = pygame.math.Vector2(0, 0)
        self.is_alive: bool = True
        self.is_on_ground: bool = False
        self._previous_bottom: float = 0.0

        # Estado de Input e Pulo
        self.movement: float = 0.0
        self.is_pulando: bool = False
        self.pulou: bool = False
        self.jump_time: float = 0.0

        self._local_bounds: pygame.Rect = pygame.Rect(0, 0, 0, 0)

        self.carregar_conteudo()
        self.reset(position)

    @property
    def limites(self) -> pygame.Rect:
        """Obtém um retângulo que delimita este jogador no espaço do mundo."""
        # math.floor ou round() para converter as coordenadas espaciais float para int do Rect
        left = round(self.posicao.x - self.sprite.origin.x) + self._local_bounds.x
        top = round(self.posicao.y - self.sprite.origin.y) + self._local_bounds.y
        return pygame.Rect(left, top, self._local_bounds.width, self._local_bounds.height)

    def carregar_conteudo(self):
        """Carrega a spritesheet do jogador e os sons."""
        # Carrega texturas animadas usando o nosso ContentManager
        self.anim_espera = Animation("Sprites/Player/Idle.png", 0.1, True)
        self.andar_anim = Animation("Sprites/Player/Run.png", 0.1, True)
        self.pulo_anim = Animation("Sprites/Player/Jump.png", 0.1, False)
        self.vitoria_anim = Animation("Sprites/Player/Celebrate.png", 0.1, False)
        self.morte_anim = Animation("Sprites/Player/Die.png", 0.1, False)

        # Calcula os limites (bounds) dentro do tamanho da textura
        width = int(self.anim_espera.frame_width * 0.4)
        left = (self.anim_espera.frame_width - width) // 2
        height = int(self.anim_espera.frame_width * 0.8)
        top = self.anim_espera.frame_height - height
        self._local_bounds = pygame.Rect(left, top, width, height)

        # Carrega sons (Assumindo que você inicializou o pygame.mixer)
        self.som_perdeu = ContentManager.load_sound("Sounds/STAY_SE_00016.wav")
        self.som_pulo = ContentManager.load_sound("Sounds/STAY_SE_00010.wav")
        self.som_queda = ContentManager.load_sound("Sounds/STAY_SE_00016.wav")

    def reset(self, position: pygame.math.Vector2):
        """Ressuscita e reposiciona o jogador."""
        self.posicao = pygame.math.Vector2(position)
        self.velocidade = pygame.math.Vector2(0, 0)
        self.is_alive = True
        self.sprite.play_animation(self.anim_espera)

    def update(self, dt: float):
        """
        Lida com input, executa a física e anima a sprite do jogador.
        Substitui o GameTime pelo dt (delta time em segundos).
        """
        self.get_input()
        self.aplicar_fisica(dt)

        if self.is_alive and self.is_on_ground:
            # Seleciona a animação baseada na velocidade horizontal
            if abs(self.velocidade.x) - 0.02 > 0:
                self.sprite.play_animation(self.andar_anim)
            else:
                self.sprite.play_animation(self.anim_espera)

        # Limpa o input
        self.movement = 0.0
        self.is_pulando = False

    def get_input(self):
        """Obtém comandos de movimento horizontal e pulo (Somente Desktop)."""
        keys = pygame.key.get_pressed()

        # Movimento Horizontal (Override digital)
        if keys[pygame.K_LEFT] or keys[pygame.K_a]:
            self.movement = -1.0
        elif keys[pygame.K_RIGHT] or keys[pygame.K_d]:
            self.movement = 1.0

        # Pulo
        self.is_pulando = keys[pygame.K_SPACE] or keys[pygame.K_UP] or keys[pygame.K_w]

    def aplicar_fisica(self, dt: float):
        """Atualiza a velocidade e posição do jogador baseado em input, gravidade, etc."""
        previous_position = pygame.math.Vector2(self.posicao)

        # Aceleração horizontal e gravidade
        self.velocidade.x += self.movement * self.ACELERACAO * dt
        self.velocidade.y = clamp(self.velocidade.y + self.GRAVIDADE * dt, -self.QUEDA_VELOCIDADE,
                                  self.QUEDA_VELOCIDADE)

        self.velocidade.y = self.pular(self.velocidade.y, dt)

        # Aplica pseudo-atrito horizontal
        if self.is_on_ground:
            self.velocidade.x *= self.FATOR_TERRA
        else:
            self.velocidade.x *= self.FATOR_AR

        # Impede que o jogador corra mais rápido que a velocidade máxima
        self.velocidade.x = clamp(self.velocidade.x, -self.MAXIMO_VELOCIDADE, self.MAXIMO_VELOCIDADE)

        # Aplica a velocidade à posição
        self.posicao += self.velocidade * dt
        self.posicao.x = round(self.posicao.x)
        self.posicao.y = round(self.posicao.y)

        # Resolve colisões com o cenário
        self.gerenciar_colisao()

        # Se a colisão nos parou, zera a velocidade naquele eixo
        if self.posicao.x == previous_position.x:
            self.velocidade.x = 0
        if self.posicao.y == previous_position.y:
            self.velocidade.y = 0

    def pular(self, velocity_y: float, dt: float) -> float:
        """Calcula a velocidade Y baseada na curva de pulo."""
        if self.is_pulando:
            # Inicia ou continua o pulo
            if (not self.pulou and self.is_on_ground) or self.jump_time > 0.0:
                if self.jump_time == 0.0:
                    self.som_pulo.play()

                self.jump_time += dt
                self.sprite.play_animation(self.pulo_anim)

            # Se estamos na ascensão do pulo
            if 0.0 < self.jump_time <= self.TEMPO_PULO:
                # Curva de poder para o controle preciso do pulo
                velocity_y = self.PULO_VELOCIDADE * (
                            1.0 - math.pow(self.jump_time / self.TEMPO_PULO, self.PULO_POTENCIA))
            else:
                # Alcançou o ápice do pulo
                self.jump_time = 0.0
        else:
            # Cancela um pulo em progresso ou continua sem pular
            self.jump_time = 0.0

        self.pulou = self.is_pulando
        return velocity_y

    def gerenciar_colisao(self):
        """Detecta e resolve todas as colisões entre o jogador e os blocos vizinhos."""
        bounds = self.limites

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
                                self.posicao.y += depth.y
                                bounds = self.limites

                        elif collision == TileCollision.IMPASSABLE:
                            # Resolve a colisão ao longo do eixo X
                            self.posicao.x += depth.x
                            bounds = self.limites

        self._previous_bottom = bounds.bottom

    def morreu(self, killed_by):  # killed_by do tipo 'Enemy' (ou None)
        self.is_alive = False
        if killed_by is not None:
            self.som_perdeu.play()
        else:
            self.som_queda.play()

        self.sprite.play_animation(self.morte_anim)

    def colidiu_saida(self):
        self.sprite.play_animation(self.vitoria_anim)

    def draw(self, dt: float, screen: pygame.Surface):
        # Espelha a sprite baseado na direção do movimento
        if self.velocidade.x > 0:
            self.flip_x = False
        elif self.velocidade.x < 0:
            self.flip_x = True

        self.sprite.draw(dt, screen, self.posicao, self.flip_x)