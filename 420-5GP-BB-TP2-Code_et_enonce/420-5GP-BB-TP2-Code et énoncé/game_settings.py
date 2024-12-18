import pygame


class GameSettings:
    """ Singleton pour les paramètres de jeu. """

    SCREEN_WIDTH = 1280
    SCREEN_HEIGHT = 720
    FPS = 90

    NB_PLAYER_LIVES = 5

    # File names
    GAME_FONT = "fonts/boombox2.ttf"
    ASTRONAUT_FILENAME = "img/astronaut.png"
    LIVES_ICONS_FILENAME = "img/hud_lives.png"
    FUEL_GAUGE_FULL_FILENAME = "img/fuel_gauge_full.png"
    FUEL_GAUGE_EMPTY_FILENAME = "img/fuel_gauge_empty.png"
    LOADING_IMAGE = "img/loading.png"
    LOADING_AUDIO = "snd/390539__burghrecords__dystopian-future-fx-sounds-8.wav"
    MAIN_SOUNDTRACK = "snd/476556__magmisoundtracks__sci-fi-music-loop-01.wav"
    SPACE_TAXI_ICON = "img/space_taxi_icon.ico"
    SPLASH_IMAGE = "img/splash.png"
    SPLASH_AUDIO = "snd/371516__mrthenoronha__space-game-theme-loop.wav"
    TAXIS_FILENAME = "img/taxis.png"
    REACTOR_SOUND = "snd/170278__knova__jetpack-low.wav"
    CRASH_SOUND = "snd/237375__squareal__car-crash.wav"
    SMOOTH_LANDING_SOUND = "snd/8-bit-heaven-26287-[AudioTrimmer.com].wav"
    JINGLE_SOUND = "snd/petit_jingle_sound.mp3"
    GAME_OVER_IMAGE = "img/game_over.png"
    ERROR_ICON = "img/error-icon.png"
    ROUGH_LANDING_SOUND = "snd/rough_landing_sound.wav"
    LEVEL_LOADING_SCENE = "img/ecran_chargement.png"
    ETOILE = "img/etoile.png"

    _instance = None

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super(GameSettings, cls).__new__(cls, *args, **kwargs)
        return cls._instance

    def __init__(self) -> None:
        if not hasattr(self, '_initialized'):
            self.screen = None
            self.pad_font = pygame.font.Font(GameSettings.GAME_FONT, 11)
            self._initialized = True

    def get_level_configuration(self, level: int) -> str:
        """ Retourne le nom de fichier de configuration de niveau en fonction du niveau """
        return f"level{level}.cfg"

    def get_level_name(self, level: int) -> str:
        level_names = {
            1: "Niveau 1",
            2: "Niveau 2",
            3: "Niveau 3"
        }
        return level_names.get(level, f"Level {level}")