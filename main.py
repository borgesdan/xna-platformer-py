import pygame
import sys
import os
from graphics import ContentManager
from level import Level


class PlatformerGame:
    TEMPO_DE_AVISO: float = 30.0
    NUMERO_DE_LEVELS: int = 3

    def __init__(self):
        # Inicializa todos os módulos do Pygame (Vídeo, Áudio, Eventos, etc.)
        pygame.init()
        pygame.mixer.init()

        # Define o tamanho da tela
        self.largura_janela = 800
        self.altura_janela = 480
        self.tela = pygame.display.set_mode((self.largura_janela, self.altura_janela))
        pygame.display.set_caption("Jogo de plataforma")

        self.relogio = pygame.time.Clock()
        self.is_ativo = True

        # Recursos globais
        self.hud_font = None
        self.vitoria_overlay = None
        self.perdeu_overlay = None
        self.morreu_overlay = None

        # Estado meta-level
        self.level_index = -1
        self.level = None
        self.continue_pressionado = False


        self.tempo_total = 0.0

        self.carregar_conteudo()

    def carregar_conteudo(self):
        try:
            self.hud_font = pygame.font.Font("Content/Fonts/Hud.ttf", 36)
        except FileNotFoundError:
            self.hud_font = pygame.font.Font(None, 36)

        # Carrega as texturas de sobreposição
        self.vitoria_overlay = ContentManager.load_texture("Overlays/ganhou.png")
        self.perdeu_overlay = ContentManager.load_texture("Overlays/perdeu.png")
        self.morreu_overlay = ContentManager.load_texture("Overlays/morreu.png")

        # Inicia a música de fundo
        try:
            pygame.mixer.music.load("Content/Sounds/Music.mp3")
            pygame.mixer.music.play(loops=-1)  # -1 faz repetir infinitamente
        except pygame.error:
            print("Aviso: Música de fundo não encontrada ou formato não suportado.")

        self.carregar_proximo_nivel()

    def carregar_proximo_nivel(self):
        #move para o próximo nível
        self.level_index = (self.level_index + 1) % self.NUMERO_DE_LEVELS
        level_path = f"Levels/{self.level_index}.txt"
        self.level = Level(level_path, self.level_index)

    def recarregar_nivel(self):
        self.level_index -= 1
        self.carregar_proximo_nivel()

    def gerenciar_input(self):
        continue_pressed = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_ativo = False

            # Mapeamento do teclado para cliques únicos
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.is_ativo = False
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    continue_pressed = True

        # Executa a ação apropriada para avançar o jogo e retornar o jogador à ação
        if not self.continue_pressionado and continue_pressed:
            if not self.level.player.is_alive:
                self.level.start_new_life()
            elif self.level.time_remaining == 0.0:
                if self.level.reached_exit:
                    self.carregar_proximo_nivel()
                else:
                    self.recarregar_nivel()

        self.continue_pressionado = continue_pressed

    def update(self, dt: float):
        """Atualiza a lógica do nível."""
        self.gerenciar_input()
        self.level.update(dt, self.tempo_total)

    def draw(self, dt: float): # <- Adicione o parâmetro dt aqui
        """Desenha o jogo, do fundo ao primeiro plano."""
        # Limpa a tela com CornflowerBlue
        self.tela.fill((100, 149, 237))

        # Passa o 'dt' real para o nível atualizar os AnimationPlayers
        self.level.draw(dt, self.tela)

        self.desenhar_hud()

        pygame.display.flip()

    def desenhar_hud(self):
        """Desenha o tempo, pontuação e overlays."""
        # Área de segurança simulada
        margin_x, margin_y = 20, 20
        center_x = self.largura_janela / 2.0
        center_y = self.altura_janela / 2.0

        # Formata o tempo restante (MM:SS)
        minutes = int(self.level.time_remaining // 60)
        seconds = int(self.level.time_remaining % 60)
        time_string = f"TEMPO: {minutes:02}:{seconds:02}"

        # Lógica de piscar o tempo (usa módulo da divisão inteira)
        if (self.level.time_remaining > self.TEMPO_DE_AVISO or
                self.level.reached_exit or
                int(self.level.time_remaining) % 2 == 0):
            time_color = (255, 255, 0)  # Amarelo
        else:
            time_color = (255, 0, 0)  # Vermelho

        # Desenha o tempo
        self.desenhar_string_sombra(time_string, (margin_x, margin_y), time_color)

        # Desenha a pontuação logo abaixo do tempo
        # Em Pygame, font.size retorna (width, height)
        text_width, text_height = self.hud_font.size(time_string)
        score_string = f"SCORE: {self.level.score}"
        self.desenhar_string_sombra(score_string, (margin_x, margin_y + text_height * 1.2), (255, 255, 0))

        # Determina o overlay de status a ser mostrado
        status_texture = None
        if self.level.time_remaining == 0.0:
            if self.level.reached_exit:
                status_texture = self.vitoria_overlay
            else:
                status_texture = self.perdeu_overlay
        elif not self.level.player.is_alive:
            status_texture = self.morreu_overlay

        if status_texture is not None:
            # Centraliza o overlay
            status_rect = status_texture.get_rect(center=(center_x, center_y))
            self.tela.blit(status_texture, status_rect)

    def desenhar_string_sombra(self, text: str, position: tuple, color: tuple):
        """Renderiza um texto com uma sombra preta atrás."""
        # Sombra (Offset de +2 pixels em X e Y para melhor visibilidade em vez de 1.0f)
        shadow_surface = self.hud_font.render(text, True, (0, 0, 0))
        self.tela.blit(shadow_surface, (position[0] + 2, position[1] + 2))

        # Texto principal
        text_surface = self.hud_font.render(text, True, color)
        self.tela.blit(text_surface, position)

    def executar_jogo(self):
        #loop principal
        while self.is_ativo:
            ms = self.relogio.tick(60)
            dt = ms / 1000.0

            # Limite de segurança para o delta time caso a janela seja arrastada e trave
            if dt > 0.1:
                dt = 0.1

            self.tempo_total += dt

            self.update(dt)
            self.draw(dt)

        # Encerra o jogo
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = PlatformerGame()
    game.executar_jogo()