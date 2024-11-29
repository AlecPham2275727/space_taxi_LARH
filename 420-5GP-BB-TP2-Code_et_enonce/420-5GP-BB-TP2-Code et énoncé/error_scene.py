# error_scene.py
import pygame
import sys
import threading
import time

from scene import Scene

class ErrorScene(Scene):
    def __init__(self, error_message: str):
        super().__init__()
        self.error_message = 'FATAL ERROR loading ' + error_message

        self.font_file = pygame.font.Font(None, 30)
        self.font_thread = pygame.font.Font(None, 30)
        self.font_escape = pygame.font.Font(None, 35)

        self.time_remaining = 10
        self._key_to_press = "ESCAPE"

        self.thread = threading.Thread(target=self.countdown)
        self.thread.start()
        self._time_up = False
        self.start_time = time.time()

        try:
            self._error_icon = pygame.image.load("img/error-icon.png").convert_alpha()
            self._error_icon = pygame.transform.scale(self._error_icon, (200, 200))
        except pygame.error as e:
            print(f"Erreur lors du chargement de l'icône : {e}")


    def countdown(self):
        time.sleep(10)
        self._time_up = True

    def handle_event(self, event):
        if event.type == pygame.QUIT:
            self.quit_game()
        elif event.type == pygame.KEYDOWN:
            if event.key == pygame.K_ESCAPE:
                self.quit_game()

    def update(self):
        """Mettre à jour le temps restant."""
        time_left = time.time() - self.start_time
        self.time_remaining = max(0, 10 - int(time_left))
        if self._time_up:
            self.quit_game()

    def render(self, screen):
        screen.fill((0, 0, 0))

        if self._error_icon:
            error_icon_rect = self._error_icon.get_rect(center=(screen.get_width() // 2, screen.get_height() - 500))
            screen.blit(self._error_icon, error_icon_rect)

        text_file = self.font_file.render(self.error_message, True, (255, 0, 0))
        text_file_rect = text_file.get_rect(center=(screen.get_width() // 2, screen.get_height() - 350))
        screen.blit(text_file, text_file_rect)

        before_countdown = "Program will be terminated in "
        before_countdown_surface = self.font_thread.render(before_countdown, True, (255, 0, 0))

        countdown_text = self.font_thread.render(str(self.time_remaining), True, (255, 255, 255))

        seconds_text = " seconds (or press "
        seconds_text_surface = self.font_thread.render(seconds_text, True, (255, 0, 0))

        key_text_surface = self.font_escape.render(self._key_to_press, True, (255, 255, 255))

        after_key_text = " to terminate now)"
        after_key_text_surface = self.font_thread.render(after_key_text, True, (255, 0, 0))

        total_width_surfaces = (
            before_countdown_surface.get_width() +
            countdown_text.get_width() +
            seconds_text_surface.get_width() +
            key_text_surface.get_width() +
            after_key_text_surface.get_width()
        )

        dest_y = screen.get_height() - 50

        dest_x = (screen.get_width() - total_width_surfaces) // 2
        screen.blit(before_countdown_surface, (dest_x, dest_y))

        dest_x += before_countdown_surface.get_width()
        screen.blit(countdown_text, (dest_x, dest_y))

        dest_x += countdown_text.get_width()
        screen.blit(seconds_text_surface, (dest_x, dest_y))

        dest_x += seconds_text_surface.get_width()
        screen.blit(key_text_surface, (dest_x, screen.get_height() - 55))

        dest_x += key_text_surface.get_width()
        screen.blit(after_key_text_surface, (dest_x, dest_y))

    def surface(self) -> pygame.Surface:
        return pygame.display.get_surface()

    def quit_game(self):
        pygame.mixer.music.stop()
        pygame.quit()
        sys.exit(0)
