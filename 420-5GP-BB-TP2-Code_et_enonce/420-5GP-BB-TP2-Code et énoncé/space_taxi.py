"""
  Tribute to Space Taxi!

  Ce programme rend hommage au jeu Space Taxi écrit par John Kutcher et publié pour le
  Commodore 64 en 1984.  Il s'agit  d'une interprétation libre inspirée  de la version
  originale. Aucune ressource originale (son, image, code) n'a été réutilisée.

  Le code propose un nombre important  d'opportunités de refactorisation.  Il contient
  également plusieurs erreurs à corriger. Il a été conçu pour un travail pratique dans
  le cadre du cours de Maintenance logicielle (420-5GP-BB) du programme de  Techniques
  de l'informatique au Collège de Bois-de-Boulogne, à Montréal.  L'usage en est permis
  à des fins pédagogiques seulement.

  Eric Drouin
  Novembre 2024
"""
import os
import re
import pygame
import sys

from game_settings import GameSettings
from level_loading_scene import LevelLoadingScene
from scene_manager import SceneManager
from splash_scene import SplashScene
from error_scene import ErrorScene
from game_over_scene import GameOverScene
from input_settings import InputSettings

os.environ['PYGAME_HIDE_SUPPORT_PROMPT'] = '1'


def main() -> None:
    scene_manager = SceneManager()
    """ Programme principal. """
    pygame.init()
    pygame.mixer.init()

    pygame.joystick.init()
    settings = GameSettings()
    input_settings = InputSettings()
    screen = pygame.display.set_mode((settings.SCREEN_WIDTH, settings.SCREEN_HEIGHT))
    pygame.display.set_caption("Tribute to Space Taxi!")
    error_scene = None

    # Ajouter l'icône personnalisée
    try:
        # Source du code : https://stackoverflow.com/questions/21271059/how-do-i-change-the-pygame-icon
        icon = pygame.image.load(settings.SPACE_TAXI_ICON)
        pygame.display.set_icon(icon)
    except pygame.error as e:
        print(f"Erreur lors du chargement de l'icône : {e}")

    clock = pygame.time.Clock()

    show_fps = False

    if show_fps:
        fps_font = pygame.font.Font(None, 36)

    try:
        scene_manager.add_scene("splash", SplashScene())
        level = 1
        level_name = GameSettings().get_level_name(level)
        scene_manager.add_scene("level1_load", LevelLoadingScene(level, level_name))
        level += 1
        level_name = GameSettings().get_level_name(level)
        scene_manager.add_scene("level2_load", LevelLoadingScene(level, level_name))
        scene_manager.add_scene("game_over", GameOverScene())
        scene_manager.set_scene("splash")
    except FileNotFoundError as e:
        error_scene = handle_errors(scene_manager, e)
        scene_manager.add_scene("error", error_scene)
        scene_manager.set_scene("error")

    try:
        while True:
            try:
                clock.tick(settings.FPS) / 1000  # en secondes

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        if error_scene:
                            print("Error")
                            error_scene.stop_thread()
                        quit_game()

                    scene_manager.handle_event(event)

                scene_manager.update()

                scene_manager.render(screen)

                if show_fps:
                    fps = clock.get_fps()
                    fps_text = fps_font.render(f"FPS: {int(fps)}", True, (255, 255, 255))
                    screen.blit(fps_text, (10, 10))

                pygame.display.flip()

            except FileNotFoundError as e:
                error_scene = handle_errors(scene_manager, e)
                scene_manager.add_scene("error", error_scene)
                scene_manager.set_scene("error")

    except KeyboardInterrupt:
        quit_game()


def handle_errors(scene_manager: SceneManager, error_message: Exception):
    # Source :
    # https://www.geeksforgeeks.org/python-program-to-get-the-file-name-from-the-file-path/
    # https://docs.python.org/fr/3/howto/regex.html
    # Dans le str(e), recherche une chaine qui commence par No file suivie de chaine différentes de ' et finit par '
    match = re.search(r"No file '([^']+)'", str(error_message))
    filename = ""
    if match:
        filepath = match.group(1)
        filename = os.path.basename(filepath)
    return ErrorScene(filename)


def quit_game() -> None:
    pygame.mixer.music.stop()
    pygame.quit()
    sys.exit(0)


if __name__ == '__main__':
    main()
