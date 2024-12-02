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
        return f"level{level}.cfg"