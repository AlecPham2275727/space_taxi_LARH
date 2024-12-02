import time

import pygame

from scene import Scene
from scene_manager import SceneManager
from game_settings import GameSettings


class GameOverScene(Scene):
    """ Scène de fin de jeu. """

    def __init__(self) -> None:
        super().__init__()
        self._settings = GameSettings()
        self._surface = pygame.image.load(self._settings.GAME_OVER_IMAGE).convert_alpha()

    def handle_event(self, event: pygame.event.Event) -> None:
        pass

    def update(self) -> None:
        pass

    def render(self, screen: pygame.Surface) -> None:
        screen.blit(self._surface, (0, 0))

    def surface(self) -> pygame.Surface:
        return self._surface
