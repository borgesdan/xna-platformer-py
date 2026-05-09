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
        # Inicializa todos os módulos do Pygame
        pygame.init()
        pygame.mixer.init()

        self.screen_width = 800
        self.screen_height = 480
        self.screen = pygame.display.set_mode((self.screen_width, self.screen_height))
        pygame.display.set_caption("Jogo de Plataforma")

        self.clock = pygame.time.Clock()
        self.is_running = True

        # --- MÁQUINA DE ESTADOS ---
        self.state = "MENU"
        self.menu_selected_index = 0

        # Recursos globais
        self.hud_font = None
        self.title_font = None
        self.win_overlay = None
        self.lose_overlay = None
        self.died_overlay = None

        # Estado meta-level
        self.level_index = -1
        self.level = None
        self.was_continue_pressed = False

        self.total_time = 0.0

        self.load_content()

    def load_content(self):
        """Carrega todo o conteúdo global do jogo."""
        # Fontes: Uma para o HUD (padrão) e uma maior para o Título do Menu
        try:
            self.hud_font = pygame.font.Font("Fonts/Hud.ttf", 36)
            self.title_font = pygame.font.Font("Fonts/Hud.ttf", 72)
        except FileNotFoundError:
            self.hud_font = pygame.font.Font(None, 36)
            self.title_font = pygame.font.Font(None, 72)

            # Overlays
        self.win_overlay = ContentManager.load_texture("Overlays/ganhou.png")
        self.lose_overlay = ContentManager.load_texture("Overlays/morreu.png")
        self.died_overlay = ContentManager.load_texture("Overlays/perdeu.png")

        # Música
        try:
            music_path = ContentManager.get_full_path("Sounds/Music.mp3")
            pygame.mixer.music.load(music_path)
            pygame.mixer.music.play(loops=-1)
        except pygame.error:
            print("Aviso: Música de fundo não encontrada ou formato não suportado.")

        self.load_next_level()

    def load_next_level(self):
        self.level_index = (self.level_index + 1) % self.NUMBER_OF_LEVELS
        level_path = f"Levels/{self.level_index}.txt"
        self.level = Level(level_path, self.level_index)

    def reload_current_level(self):
        self.level_index -= 1
        self.load_next_level()

    def update(self, dt: float):
        """Atualiza a lógica dependendo do estado atual."""
        continue_pressed = False

        # Centraliza o processamento de eventos do OS
        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                self.is_running = False

            # --- LÓGICA DO MENU ---
            if self.state == "MENU":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_UP:
                        self.menu_selected_index = (self.menu_selected_index - 1) % 2
                    elif event.key == pygame.K_DOWN:
                        self.menu_selected_index = (self.menu_selected_index + 1) % 2
                    elif event.key == pygame.K_RETURN or event.key == pygame.K_SPACE:
                        if self.menu_selected_index == 0:  # Iniciar
                            self.state = "PLAYING"
                        elif self.menu_selected_index == 1:  # Sair
                            self.is_running = False

            # --- LÓGICA DE GAMEPLAY ---
            elif self.state == "PLAYING":
                if event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        self.state = "MENU"  # ESC agora pausa o jogo e volta pro Menu
                    if event.key == pygame.K_SPACE or event.key == pygame.K_RETURN:
                        continue_pressed = True

        # Executa a física e a atualização apenas se estiver jogando
        if self.state == "PLAYING":
            if not self.was_continue_pressed and continue_pressed:
                if not self.level.player.is_alive:
                    self.level.start_new_life()
                elif self.level.time_remaining == 0.0:
                    if self.level.reached_exit:
                        self.load_next_level()
                    else:
                        self.reload_current_level()

            self.was_continue_pressed = continue_pressed
            self.level.update(dt, self.total_time)

    def draw(self, dt: float):
        """Desenha o jogo, roteando para a UI correta dependendo do estado."""
        self.screen.fill((100, 149, 237))

        # Renderizamos o nível independentemente do estado.
        # Se for MENU, passamos dt=0 para que os bonecos não se mexam no fundo!
        if self.level is not None:
            tempo_frame = dt if self.state == "PLAYING" else 0
            self.level.draw(tempo_frame, self.screen)

        # Camadas superiores
        if self.state == "MENU":
            # Película escura para dar destaque ao menu
            overlay = pygame.Surface((self.screen_width, self.screen_height))
            overlay.set_alpha(150)  # 0 é transparente, 255 é opaco
            overlay.fill((0, 0, 0))
            self.screen.blit(overlay, (0, 0))

            self.draw_menu()
        elif self.state == "PLAYING":
            self.draw_hud()

        pygame.display.flip()

    def draw_menu(self):
        """Desenha a tela inicial (Título, Botões e Controles)."""
        center_x = self.screen_width / 2.0

        # Título
        title_text = "SUPER PLATAFORMA"
        title_width, _ = self.title_font.size(title_text)
        self.draw_shadowed_string(title_text, (center_x - title_width / 2, 70), (255, 255, 255), self.title_font)

        # Opções do Menu
        options = ["Iniciar ", "  Sair  "]
        for i, option in enumerate(options):
            color = (255, 255, 0) if i == self.menu_selected_index else (255, 255, 255)
            # Adiciona setinhas laterais na opção selecionada
            text = f"> {option} <" if i == self.menu_selected_index else option

            text_w, _ = self.hud_font.size(text)
            self.draw_shadowed_string(text, (center_x - text_w / 2, 220 + i * 50), color, self.hud_font)

        # Seção de Controles
        controls = [
            "Controles:",
            "<- e -> : Andar",
            "Espaço : Pular/Selecionar",
            "ESC : Menu"
        ]

        for i, line in enumerate(controls):
            line_w, _ = self.hud_font.size(line)
            # Renderiza os controles um pouco mais abaixo com uma cor cinza (200, 200, 200)
            self.draw_shadowed_string(line, (center_x - line_w / 2, 340 + i * 30), (200, 200, 200), self.hud_font)

    def draw_hud(self):
        """Desenha o tempo, pontuação e overlays do jogo."""
        margin_x, margin_y = 20, 20
        center_x = self.screen_width / 2.0
        center_y = self.screen_height / 2.0

        minutes = int(self.level.time_remaining // 60)
        seconds = int(self.level.time_remaining % 60)
        time_string = f"TIME: {minutes:02}:{seconds:02}"

        if (self.level.time_remaining > self.WARNING_TIME or
                self.level.reached_exit or
                int(self.level.time_remaining) % 2 == 0):
            time_color = (255, 255, 0)
        else:
            time_color = (255, 0, 0)

        self.draw_shadowed_string(time_string, (margin_x, margin_y), time_color, self.hud_font)

        _, text_height = self.hud_font.size(time_string)
        score_string = f"SCORE: {self.level.score}"
        self.draw_shadowed_string(score_string, (margin_x, margin_y + text_height * 1.2), (255, 255, 0), self.hud_font)

        status_texture = None
        if self.level.time_remaining == 0.0:
            if self.level.reached_exit:
                status_texture = self.win_overlay
            else:
                status_texture = self.lose_overlay
        elif not self.level.player.is_alive:
            status_texture = self.died_overlay

        if status_texture is not None:
            status_rect = status_texture.get_rect(center=(center_x, center_y))
            self.screen.blit(status_texture, status_rect)

    # Modificamos a função para aceitar a fonte como parâmetro opcional
    def draw_shadowed_string(self, text: str, position: tuple, color: tuple, font: pygame.font.Font):
        """Renderiza um texto com uma sombra preta atrás."""
        shadow_surface = font.render(text, True, (0, 0, 0))
        self.screen.blit(shadow_surface, (position[0] + 2, position[1] + 2))

        text_surface = font.render(text, True, color)
        self.screen.blit(text_surface, position)

    def run(self):
        """O Loop principal do jogo."""
        while self.is_running:
            ms = self.clock.tick(60)
            dt = ms / 1000.0

            if dt > 0.1:
                dt = 0.1

            # Só incrementa o tempo global se o jogo estiver rodando (Pausa a música nas gemas também)
            if self.state == "PLAYING":
                self.total_time += dt

            self.update(dt)
            self.draw(dt)

        pygame.quit()
        sys.exit()


if __name__ == "__main__":
    game = PlatformerGame()
    game.run()