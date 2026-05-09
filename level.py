import os

import pygame
import math
import random
from typing import List, Optional, Tuple
from graphics import ContentManager
from tile import Tile, TileCollision
from player import Player
from inimigo import Inimigo
from gem import Gem
from geometry import get_bottom_center


class Level:
    """
    Uma grade uniforme de tiles com coleções de gemas e inimigos.
    O nível possui o jogador e controla as condições de vitória e derrota,
    bem como a pontuação.
    """

    POINTS_PER_SECOND: int = 5
    ENTITY_LAYER: int = 2
    INVALID_POSITION = pygame.math.Vector2(-1, -1)

    def __init__(self, file_path: str, level_index: int):
        # Estado do jogo do nível
        self.score: int = 0
        self.reached_exit: bool = False
        self.time_remaining: float = 120.0  # 2 minutos em segundos

        # Entidades no nível
        self.player: Optional[Player] = None
        self.gems: List[Gem] = []
        self.enemies: List[Inimigo] = []

        # Locais chave no nível
        self.start_position: pygame.math.Vector2 = pygame.math.Vector2(0, 0)
        self.exit_position: pygame.math.Vector2 = pygame.math.Vector2(-1, -1)

        # Estrutura física
        self.tiles: List[List[Tile]] = []
        self.layers: List[pygame.Surface] = []

        # Gerador de números aleatórios com seed fixa como no original
        self.random = random.Random(354668)

        self._load_tiles(file_path)

        # Carrega as texturas de fundo.
        # Assume-se que as imagens estão em "Backgrounds/Layer{i}_{segment_index}.png"
        for i in range(3):
            bg_path = f"Backgrounds/Layer{i}_{level_index}.png"
            self.layers.append(ContentManager.load_texture(bg_path))

        # Carrega o som
        self.exit_reached_sound = ContentManager.load_sound("Sounds/TITLE_SE_00000.wav")

    def _load_tiles(self, file_path: str):
        """Lê o arquivo de texto e constrói a matriz de tiles."""

        # OTIMIZAÇÃO: Constrói o caminho absoluto respeitando a pasta Content
        full_path = os.path.join(ContentManager.ROOT_DIRECTORY, file_path)

        try:
            with open(full_path, 'r') as f:
                lines = [line.rstrip('\n') for line in f.readlines()]
        except FileNotFoundError:
            raise FileNotFoundError(f"Erro fatal: Arquivo de nível não encontrado em: {full_path}")

        height = len(lines)
        if height == 0:
            raise ValueError("O arquivo de nível está vazio.")

        width = len(lines[0])

        # Verifica se todas as linhas têm o mesmo comprimento
        for i, line in enumerate(lines):
            if len(line) != width:
                raise ValueError(f"O comprimento da linha {i} é diferente das anteriores.")

        # Aloca a grade de tiles (lista de colunas)
        self.tiles = [[Tile(None, TileCollision.PASSABLE) for _ in range(height)] for _ in range(width)]

        # Percorre cada posição de tile (y primeiro no arquivo de texto, mas armazenamos [x][y])
        for y in range(height):
            for x in range(width):
                tile_type = lines[y][x]
                self.tiles[x][y] = self._load_tile(tile_type, x, y)

        if self.player is None:
            raise RuntimeError("Um nível deve ter um ponto de partida (1).")
        if self.exit_position == self.INVALID_POSITION:
            raise RuntimeError("Um nível deve ter uma saída (X).")

    def _load_tile(self, tile_type: str, x: int, y: int) -> Tile:
        """Carrega a aparência e o comportamento de um tile individual."""
        if tile_type == '.':
            # Espaço em branco
            return Tile(None, TileCollision.PASSABLE)
        elif tile_type == 'X':
            # Saída
            return self._load_exit_tile(x, y)
        elif tile_type == 'G':
            # Gema
            return self._load_gem_tile(x, y)
        elif tile_type == '-':
            # Plataforma flutuante
            return self._create_tile("Platform", TileCollision.PLATFORM)
        elif tile_type in ('A', 'B', 'C', 'D'):
            # Vários inimigos
            return self._load_enemy_tile(x, y, f"Monster{tile_type}")
        elif tile_type == '~':
            # Bloco de plataforma
            return self._load_variety_tile("BlockB", 2, TileCollision.PLATFORM)
        elif tile_type == ':':
            # Bloco transponível (Passable)
            return self._load_variety_tile("BlockB", 2, TileCollision.PASSABLE)
        elif tile_type == '1':
            # Ponto de início do jogador
            return self._load_start_tile(x, y)
        elif tile_type == '#':
            # Bloco intransponível
            return self._load_variety_tile("BlockA", 7, TileCollision.IMPASSABLE)
        else:
            raise ValueError(f"Caractere de tipo de tile não suportado '{tile_type}' na posição {x}, {y}.")

    def _create_tile(self, name: str, collision: TileCollision) -> Tile:
        """Utilitário para criar um tile carregando sua textura."""
        texture = ContentManager.load_texture(f"Tiles/{name}.png")
        return Tile(texture, collision)

    def _load_variety_tile(self, base_name: str, variation_count: int, collision: TileCollision) -> Tile:
        """Carrega um tile com uma aparência aleatória baseada nas variações."""
        index = self.random.randint(0, variation_count - 1)
        return self._create_tile(f"{base_name}{index}", collision)

    def _load_start_tile(self, x: int, y: int) -> Tile:
        """Instancia o jogador e lembra onde colocá-lo ao ressuscitar."""
        if self.player is not None:
            raise RuntimeError("Um nível só pode ter um ponto de partida.")

        bounds = self.get_bounds(x, y)
        self.start_position = get_bottom_center(bounds)
        self.player = Player(self, self.start_position)

        return Tile(None, TileCollision.PASSABLE)

    def _load_exit_tile(self, x: int, y: int) -> Tile:
        """Lembra a localização da saída do nível."""
        if self.exit_position != self.INVALID_POSITION:
            raise RuntimeError("Um nível só pode ter uma saída.")

        bounds = self.get_bounds(x, y)
        self.exit_position = pygame.math.Vector2(bounds.center)

        return self._create_tile("Exit", TileCollision.PASSABLE)

    def _load_enemy_tile(self, x: int, y: int, sprite_set: str) -> Tile:
        """Instancia um inimigo e o coloca no nível."""
        position = get_bottom_center(self.get_bounds(x, y))
        self.enemies.append(Inimigo(self, position, sprite_set))
        return Tile(None, TileCollision.PASSABLE)

    def _load_gem_tile(self, x: int, y: int) -> Tile:
        """Instancia uma gema e a coloca no nível."""
        position = self.get_bounds(x, y).center
        self.gems.append(Gem(self, pygame.math.Vector2(position)))
        return Tile(None, TileCollision.PASSABLE)

    # Limites e colisão

    def get_collision(self, x: int, y: int) -> TileCollision:
        """Obtém o modo de colisão de um tile tratando limites da tela."""
        # Evita escapar das bordas laterais do nível
        if x < 0 or x >= self.width:
            return TileCollision.IMPASSABLE
        # Permite pular além do topo do nível e cair através da base
        if y < 0 or y >= self.height:
            return TileCollision.PASSABLE

        return self.tiles[x][y].collision

    def get_bounds(self, x: int, y: int) -> pygame.Rect:
        """Obtém o retângulo delimitador de um tile no espaço do mundo."""
        return pygame.Rect(x * Tile.WIDTH, y * Tile.HEIGHT, Tile.WIDTH, Tile.HEIGHT)

    @property
    def width(self) -> int:
        return len(self.tiles)

    @property
    def height(self) -> int:
        return len(self.tiles[0]) if self.width > 0 else 0

    # Atualização

    def update(self, dt: float, total_time: float):
        """
        Atualiza todos os objetos do mundo, realiza colisão e gerencia o limite de tempo.
        """
        # Pausa enquanto o jogador estiver morto ou o tempo esgotado
        if not self.player.is_alive or self.time_remaining <= 0.0:
            self.player.aplicar_fisica(dt)
        elif self.reached_exit:
            # Converte o tempo restante em pontos
            seconds = int(round(dt * 100.0))
            seconds = min(seconds, int(math.ceil(self.time_remaining)))
            self.time_remaining -= seconds
            self.score += seconds * self.POINTS_PER_SECOND
        else:
            self.time_remaining -= dt
            self.player.update(dt)
            self._update_gems(total_time)

            # Cair da base do nível mata o jogador
            if self.player.limites.top >= self.height * Tile.HEIGHT:
                self.on_player_killed(None)

            self._update_enemies(dt)

            # Checa se o jogador alcançou a saída
            if (self.player.is_alive and
                    self.player.is_on_ground and
                    self.player.limites.collidepoint(self.exit_position.x, self.exit_position.y)):
                self.on_exit_reached()

        # Garante que o tempo nunca seja negativo
        if self.time_remaining < 0:
            self.time_remaining = 0.0

    def _update_gems(self, total_time: float):
        """Anima cada gema e permite que o jogador as colete."""
        # Iterando de trás para frente para remover itens da lista de forma segura
        for i in range(len(self.gems) - 1, -1, -1):
            gem = self.gems[i]
            gem.update(total_time)

            # Colisão circular básica com o retângulo do jogador
            if gem.limites.intersects(self.player.limites):
                self._on_gem_collected(gem, self.player)
                self.gems.pop(i)

    def _update_enemies(self, dt: float):
        """Anima inimigos e permite que matem o jogador."""
        for enemy in self.enemies:
            enemy.update(dt)

            if enemy.retangulo_limite.colliderect(self.player.limites):
                self.on_player_killed(enemy)

    def _on_gem_collected(self, gem: Gem, collected_by: Player):
        self.score += Gem.PONTO
        gem.on_collected(collected_by)

    def on_player_killed(self, killed_by: Optional[Inimigo]):
        self.player.morreu(killed_by)

    def on_exit_reached(self):
        self.player.colidiu_saida()
        self.exit_reached_sound.play()
        self.reached_exit = True

    def start_new_life(self):
        """Restaura o jogador ao ponto de partida para tentar novamente."""
        self.player.reset(self.start_position)

    # Renderização

    def draw(self, dt: float, screen: pygame.Surface):
        """Desenha tudo no nível, do fundo ao primeiro plano."""

        # Desenha as camadas de fundo e as entidades entre elas
        for i in range(self.ENTITY_LAYER + 1):
            if i < len(self.layers):
                screen.blit(self.layers[i], (0, 0))

        self._draw_tiles(screen)

        for gem in self.gems:
            gem.draw(screen)

        self.player.draw(dt, screen)

        for enemy in self.enemies:
            enemy.draw(dt, screen)

        # Desenha camadas que ficam na frente das entidades
        for i in range(self.ENTITY_LAYER + 1, len(self.layers)):
            if i < len(self.layers):
                screen.blit(self.layers[i], (0, 0))

    def _draw_tiles(self, screen: pygame.Surface):
        """Desenha cada tile no nível."""
        for y in range(self.height):
            for x in range(self.width):
                texture = self.tiles[x][y].texture
                if texture is not None:
                    position = (x * Tile.WIDTH, y * Tile.HEIGHT)
                    screen.blit(texture, position)