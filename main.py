import pygame
import sys
import os
from graphics import ContentManager
from level import Level


class PlatformerGame:
    """Este é o tipo principal do seu jogo."""

    WARNING_TIME: float = 30.0
    NUMBER_OF_LEVELS: int = 3

    def __init__(self):
        # Inicializa todos os módulos do Pygame (Vídeo, Áudio, Eventos, etc.)
        pygame.init()
        pygame.mixer.init()

        # O Platformer Starter Kit rodava originalmente em 800x480
        self.screen_width = 800
        self.screen_height = 480
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Platformer")

        self.clock = pygame.time.Clock()
        self.is_running = True

        # Recursos globais
        self.hud_font = None
        self.win_overlay = None
        self.lose_overlay = None
        self.died_overlay = None

        # Estado meta-level
        self.level_index = -1
        self.level = None
        self.was_continue_pressed = False

        # O acumulador substitui o TotalGameTime do XNA
        self.total_time = 0.0

        self.load_content()

    def load_content(self):
        """Carrega todo o conteúdo global do jogo."""
        # No Pygame, carregar a fonte requer o tamanho desejado. 
        # Assumindo que você tenha um arquivo .ttf. Caso não tenha, None usa a fonte padrão.
        try:
            self.hud_font = pygame.font.Font("Fonts/Hud.ttf", 36)
        except FileNotFoundError:
            self.hud_font = pygame.font.Font(None, 36)  # Fallback seguro

        # Carrega as texturas de sobreposição
        self.win_overlay = ContentManager.load_texture("Overlays/you_win.png")
        self.lose_overlay = ContentManager.load_texture("Overlays/you_lose.png")
        self.died_overlay = ContentManager.load_texture("Overlays/you_died.png")

        # Inicia a música de fundo (Equivalente ao MediaPlayer.IsRepeating = true)
        try:
            pygame.mixer.music.load("Sounds/Music.mp3")
            pygame.mixer.music.play(loops=-1)  # -1 faz repetir infinitamente
        except pygame.error:
            print("Aviso: Música de fundo não encontrada ou formato não suportado.")

        self.load_next_level()

    def load_next_level(self):
        """Move para o próximo nível."""
        self.level_index = (self.level_index + 1) % self.NUMBER_OF_LEVELS

        # O Pygame e o coletor de lixo do Python gerenciam o Dispose de texturas antigas 
        # automaticamente quando perdemos a referência, desde que não estejam no ContentManager.
        level_path = f"Levels/{self.level_index}.txt"

        # Passamos o path em vez de um Stream
        self.level = Level(level_path, self.level_index)

    def reload_current_level(self):
        self.level_index -= 1
        self.load_next_level()

    def handle_input(self):
        """Lida com a fila de eventos e comandos de alto nível (Voltar/Continuar)."""
        continue_pressed = False

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False

            # Mapeamento do teclado para cliques únicos
            if event.type == pygame.KEYDOWN:
                if event.key == pygame.K_ESCAPE:
                    self.is_running = False
                if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                    continue_pressed = True

        # Executa a ação apropriada para avançar o jogo e retornar o jogador à ação
        if not self.was_continue_pressed and continue_pressed:
            if not self.level.player.is_alive:
                self.level.start_new_life()
            elif self.level.time_remaining == 0.0:
                if self.level.reached_exit:
                    self.load_next_level()
                else:
                    self.reload_current_level()

        self.was_continue_pressed = continue_pressed

    def update(self, dt: float):
        """Atualiza a lógica do nível."""
        self.handle_input()
        self.level.update(dt, self.total_time)

    def draw(self):
        """Desenha o jogo, do fundo ao primeiro plano."""
        # Limpa a tela com CornflowerBlue
        self.screen.fill((100, 149, 237))

        # Chama o draw do level
        self.level.draw(0, self.screen)  # dt não é estritamente necessário no draw na maioria dos casos

        self.draw_hud()

        # Apresenta (Flip) o backbuffer para a tela (Equivalente ao GraphicsDevice.Present)
        pygame.display.flip()

    def draw_hud(self):
        """Desenha o tempo, pontuação e overlays."""
        # Área de segurança simulada
        margin_x, margin_y = 20, 20
        center_x = self.screen_width / 2.0
        center_y = self.screen_height / 2.0

        # Formata o tempo restante (MM:SS)
        minutes = int(self.level.time_remaining // 60)
        seconds = int(self.level.time_remaining % 60)
        time_string = f"TIME: {minutes:02}:{seconds:02}"

        # Lógica de piscar o tempo (usa módulo da divisão inteira)
        if (self.level.time_remaining > self.WARNING_TIME or
                self.level.reached_exit or
                int(self.level.time_remaining) % 2 == 0):
            time_color = (255, 255, 0)  # Amarelo
        else:
            time_color = (255, 0, 0)  # Vermelho

        # Desenha o tempo
        self.draw_shadowed_string(time_string, (margin_x, margin_y), time_color)

        # Desenha a pontuação logo abaixo do tempo
        # Em Pygame, font.size retorna (width, height)
        text_width, text_height = self.hud_font.size(time_string)
        score_string = f"SCORE: {self.level.score}"
        self.draw_shadowed_string(score_string, (margin_x, margin_y + text_height * 1.2), (255, 255, 0))

        # Determina o overlay de status a ser mostrado
        status_texture = None
        if self.level.time_remaining == 0.0:
            if self.level.reached_exit:
                status_texture = self.win_overlay
            else:
                status_texture = self.lose_overlay
        elif not self.level.player.is_alive:
            status_texture = self.died_overlay

        if status_texture is not None:
            # Centraliza o overlay
            status_rect = status_texture.get_rect(center=(center_x, center_y))
            self.screen.blit(status_texture, status_rect)

    def draw_shadowed_string(self, text: str, position: tuple, color: tuple):
        """Renderiza um texto com uma sombra preta atrás."""
        # Sombra (Offset de +2 pixels em X e Y para melhor visibilidade em vez de 1.0f)
        shadow_surface = self.hud_font.render(text, True, (0, 0, 0))
        self.screen.blit(shadow_surface, (position[0] + 2, position[1] + 2))

        # Texto principal
        text_surface = self.hud_font.render(text, True, color)
        self.screen.blit(text_surface, position)

    def run(self):
        """O Loop principal do jogo."""
        while self.is_running:
            # O XNA tenta rodar o Update a 60 vezes por segundo (IsFixedTimeStep)
            # clock.tick(60) trava o framerate a 60 FPS e retorna o tempo em milissegundos
            ms = self.clock.tick(60)
            dt = ms / 1000.0

            # Limite de segurança para o delta time caso a janela seja arrastada e trave
            if dt > 0.1:
                dt = 0.1

            self.total_time += dt

            self.update(dt)
            self.draw()

        # Encerra o jogo graciosamente
        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = PlatformerGame()
    game.run()