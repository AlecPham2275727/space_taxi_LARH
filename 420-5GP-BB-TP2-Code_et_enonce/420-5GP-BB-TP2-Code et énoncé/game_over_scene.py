import time

import pygame

from scene import Scene
from scene_manager import SceneManager


class GameOverScene(Scene):
    """ Scène de fin de jeu. """

    _FADE_OUT_DURATION: int = 600  # ms

    def __init__(self) -> None:
        super().__init__()
        self._surface = pygame.image.load("img/game_over.png").convert_alpha()
        self._music = pygame.mixer.Sound("snd/game-over-snd.wav")
        self._music_started = False
        self._fade_out_start_time = None

    def handle_event(self, event: pygame.event.Event) -> None:
        if event.type == pygame.KEYDOWN:
            if event.key in (pygame.K_RETURN, pygame.K_SPACE):
                self._fade_out_start_time = pygame.time.get_ticks()
                SceneManager().change_scene(f"splash", GameOverScene._FADE_OUT_DURATION)

    def update(self) -> None:
        if not self._music_started:
            self._music.play()
            self._music_started = True

        if self._fade_out_start_time:
            elapsed_time = pygame.time.get_ticks() - self._fade_out_start_time
            volume = max(0.0, 1.0 - (elapsed_time / GameOverScene._FADE_OUT_DURATION))
            self._music.set_volume(volume)
            if volume == 0:
                self._fade_out_start_time = None

    def render(self, screen: pygame.Surface) -> None:
        screen.blit(self._surface, (0, 0))

    def surface(self) -> pygame.Surface:
        return self._surface
