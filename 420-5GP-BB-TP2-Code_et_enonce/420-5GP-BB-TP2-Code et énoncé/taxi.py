# CRÉDIT: Pour la tâche des réacteurs qui tue l'astronaute, j'ai consulté les sources suivantes:
# https://www.pygame.org/docs/ref/mask.html
# https://scuba.cs.uchicago.edu/pygame/ref/mask.html#pygame.mask.Mask.overlap
# https://stackoverflow.com/questions/67846651/pygame-masks-python
# https://www.pygame.org/docs/ref/mask.html#pygame.mask.Mask.draw

from enum import Enum, auto

import pygame

from astronaut import Astronaut
from hud import HUD
from obstacle import Obstacle
from pad import Pad
from pump import Pump
from input_settings import InputSettings
from game_settings import GameSettings


class ImgSelector(Enum):
    """ Sélecteur d'image de taxi. """
    IDLE = auto()
    BOTTOM_REACTOR = auto()
    TOP_REACTOR = auto()
    REAR_REACTOR = auto()
    BOTTOM_AND_REAR_REACTORS = auto()
    TOP_AND_REAR_REACTORS = auto()
    GEAR_OUT = auto()
    GEAR_SHOCKS = auto()
    GEAR_OUT_AND_BOTTOM_REACTOR = auto()
    DESTROYED = auto()

class InputSelector(Enum):
    LEFT = auto()
    RIGHT = auto()
    UP = auto()
    DOWN = auto()

class Taxi(pygame.sprite.Sprite):
    """ Un taxi spatial. """

    _NB_TAXI_IMAGES = 6

    _FLAG_LEFT = 1 << 0  # indique si le taxi va vers la gauche
    _FLAG_TOP_REACTOR = 1 << 1  # indique si le réacteur du dessus est allumé
    _FLAG_BOTTOM_REACTOR = 1 << 2  # indique si le réacteur du dessous est allumé
    _FLAG_REAR_REACTOR = 1 << 3  # indique si le réacteur arrière est allumé
    _FLAG_GEAR_OUT = 1 << 4  # indique si le train d'atterrissage est sorti
    _FLAG_DESTROYED = 1 << 5  # indique si le taxi est détruit

    _REACTOR_SOUND_VOLUME = 0.25

    _REAR_REACTOR_POWER = 0.001
    _BOTTOM_REACTOR_POWER = 0.0005
    _TOP_REACTOR_POWER = 0.00025

    _MAX_ACCELERATION_X = 0.075
    _MAX_ACCELERATION_Y_UP = 0.08
    _MAX_ACCELERATION_Y_DOWN = 0.05

    _MAX_VELOCITY_SMOOTH_LANDING = 0.50  # vitesse maximale permise pour un atterrissage en douceur
    _CRASH_ACCELERATION = 0.10

    _FRICTION_MUL = 0.9995  # la vitesse horizontale est multipliée par la friction
    _GRAVITY_ADD = 0.005  # la gravité est ajoutée à la vitesse verticale

    def __init__(self, pos: tuple) -> None:
        """
        Initialise une instance de taxi.
        :param pos:
        """
        super(Taxi, self).__init__()
        self._settings = GameSettings()

        self._initial_pos = pos

        self._hud = HUD()

        self._joystick = InputSettings().joystick

        self._reactor_sound = pygame.mixer.Sound(self._settings.REACTOR_SOUND)
        self._reactor_sound.set_volume(0)
        self._reactor_sound.play(-1)

        self._crash_sound = pygame.mixer.Sound(self._settings.CRASH_SOUND)

        self._surfaces, self._masks = Taxi._load_and_build_surfaces()

        self._reinitialize()

    @property
    def pad_landed_on(self) -> Pad or None:
        return self._pad_landed_on

    def board_astronaut(self, astronaut: Astronaut) -> None:
        self._astronaut = astronaut

    def crash_on_obstacle(self, obstacle: Obstacle) -> bool:
        """
        Vérifie si le taxi est en situation de crash contre un obstacle.
        :param obstacle: obstacle avec lequel vérifier
        :return: True si le taxi est en contact avec l'obstacle, False sinon
        """
        self._crash_on_level_objects(obstacle)

    def _crash_on_level_objects(self, object: pygame.sprite.Sprite) -> bool:
        if not isinstance(object, (Pump, Pad, Obstacle)):
            return
        
        if self._flags & Taxi._FLAG_DESTROYED == Taxi._FLAG_DESTROYED:
            return False

        if self.rect.colliderect(object.rect):
            if self.mask.overlap(object.mask, (object.rect.x - self.rect.x, object.rect.y - self.rect.y)):
                self._flags = self._FLAG_DESTROYED
                self._crash_sound.play()
                self._velocity = pygame.Vector2(0.0)
                self._acceleration.y = Taxi._CRASH_ACCELERATION
                self._acceleration.x = 0.0
                return True

        return False

        

    def crash_on_pad(self, pad: Pad) -> bool:
        """
        Vérifie si le taxi est en situation de crash contre une plateforme.
        :param pad: plateforme avec laquelle vérifier
        :return: True si le taxi est en contact avec la plateforme, False sinon
        """
        self._crash_on_level_objects(pad)
        

    def crash_on_pump(self, pump: Pump) -> bool:
        """
        Vérifie si le taxi est en situation de crash contre une pompe.
        :param pump: pompe avec laquelle vérifier
        :return: True si le taxi est en contact avec la pompe, False sinon
        """
        self._crash_on_level_objects(pump)

    def draw(self, surface: pygame.Surface) -> None:
        """ Dessine le taxi sur la surface fournie comme argument. """
        surface.blit(self.image, self.rect)

    def handle_event(self, event: pygame.event.Event) -> None:
        """ Gère les événements du taxi. """
        if event.type == pygame.KEYDOWN:
            if event.key == pygame.K_SPACE:
                if self._pad_landed_on is None:
                    if self._flags & Taxi._FLAG_GEAR_OUT != Taxi._FLAG_GEAR_OUT:
                        # pas de réacteurs du dessus et arrière lorsque le train d'atterrissage est sorti
                        self._flags &= ~(Taxi._FLAG_TOP_REACTOR | Taxi._FLAG_REAR_REACTOR)

                    self._flags ^= Taxi._FLAG_GEAR_OUT  # flip le bit pour refléter le nouvel état

                    self._select_image()

        if event.type == pygame.JOYBUTTONDOWN:
            if event.button == 1:
                if self._pad_landed_on is None:
                    if self._flags & Taxi._FLAG_GEAR_OUT != Taxi._FLAG_GEAR_OUT:
                        self._flags &= ~(Taxi._FLAG_TOP_REACTOR | Taxi._FLAG_REAR_REACTOR)

                    self._flags ^= Taxi._FLAG_GEAR_OUT

                    self._select_image()


    def has_exited(self) -> bool:
        """
        Vérifie si le taxi a quitté le niveau (par la sortie).
        :return: True si le taxi est sorti du niveau, False sinon
        """
        return self.rect.y <= -self.rect.height
    

    def stop_reactor_sound(self) -> None:
        self._reactor_sound.stop()


    def hit_astronaut(self, astronaut: Astronaut) -> bool:
        """
        Vérifie si le taxi frappe un astronaute.
        :param astronaut: astronaute pour lequel vérifier
        :return: True si le taxi frappe l'astronaute, False sinon
        """
        
        if self._pad_landed_on or astronaut.is_onboard():
            return False
    
        if self.rect.colliderect(astronaut.rect):
            if self.mask_taxi_reactor.overlap(astronaut.mask, (astronaut.rect.x - self.rect.x, astronaut.rect.y - self.rect.y)):
                return True

        return False

    def is_destroyed(self) -> bool:
        """
        Vérifie si le taxi est détruit.
        :return: True si le taxi est détruit, False sinon
        """
        return self._flags & Taxi._FLAG_DESTROYED == Taxi._FLAG_DESTROYED

    def land_on_pad(self, pad: Pad) -> bool:
        """
        Vérifie si le taxi est en situation d'atterrissage sur une plateforme.
        :param pad: plateforme pour laquelle vérifier
        :return: True si le taxi est atterri, False sinon
        """
        gear_out = self._flags & Taxi._FLAG_GEAR_OUT == Taxi._FLAG_GEAR_OUT
        if not gear_out:
            return False

        if self._velocity.y > Taxi._MAX_VELOCITY_SMOOTH_LANDING or self._velocity.y < 0.0:#self._acceleration_y < 0.0:
            return False

        if not self.rect.colliderect(pad.rect):
            return False

        if pygame.sprite.collide_mask(self, pad):
            self.rect.bottom = pad.rect.top + 4
            self._position.y = float(self.rect.y)
            self._flags &= Taxi._FLAG_LEFT | Taxi._FLAG_GEAR_OUT
            self._velocity.x = self._velocity.y = self._acceleration.x = self._acceleration.y = 0.0
            self._pad_landed_on = pad
            if self._astronaut and self._astronaut.target_pad.number == pad.number:
                self.unboard_astronaut()
            return True

        return False

    def refuel_from(self, pump: Pump) -> bool:
        """
        Vérifie si le taxi est en position de faire le plein d'essence.
        :param pump: pompe pour laquelle vérifier
        :return: True si le taxi est en bonne position, False sinon
        """
        if self._pad_landed_on is None:
            return False

        if not self.rect.colliderect(pump.rect):
            return False

        return True

    def reset(self) -> None:
        """ Réinitialise le taxi. """
        self._reinitialize()

    def unboard_astronaut(self) -> None:
        """ Fait descendre l'astronaute qui se trouve à bord. """
        self._astronaut.set_arrived_target(True)
        if self._astronaut.target_pad is not Pad.UP:
            self._astronaut.move(self.rect.x + 20, self._pad_landed_on.rect.y - self._astronaut.rect.height)
            self._astronaut.jump(self._pad_landed_on.astronaut_end.x)

        self._hud.add_bank_money(self._astronaut.get_trip_money())
        self._astronaut.set_money_saved(self._astronaut.get_trip_money())
        self._astronaut.set_trip_money(0.0)

    def update(self, *args, **kwargs) -> None:
        """
        Met à jour le taxi. Cette méthode est appelée à chaque itération de la boucle de jeu.
        :param args: inutilisé
        :param kwargs: inutilisé
        """

        # ÉTAPE 1 - gérer les touches présentement enfoncées
        input_detected = self._detect_input()
        self._handle_input_action(input_detected)

        # ÉTAPE 2 - calculer la nouvelle position du taxi
        self._velocity.x += self._acceleration.x
        self._velocity.x *= Taxi._FRICTION_MUL
        self._velocity.y += self._acceleration.y

        if self._pad_landed_on is None:
            self._velocity.y += Taxi._GRAVITY_ADD


        self._position += self._velocity

        self.rect.x = round(self._position.x)
        self.rect.y = round(self._position.y)

        # ÉTAPE 3 - fait entendre les réacteurs ou pas
        reactor_flags = Taxi._FLAG_TOP_REACTOR | Taxi._FLAG_REAR_REACTOR | Taxi._FLAG_BOTTOM_REACTOR
        if self._flags & reactor_flags:
            self._reactor_sound.set_volume(Taxi._REACTOR_SOUND_VOLUME)
        else:
            self._reactor_sound.set_volume(0)

        # ÉTAPE 4 - sélectionner la bonne image en fonction de l'état du taxi
        self._select_image()

        self._combine_reactor_mask()

        self._consume_fuel()

    def _combine_reactor_mask(self) -> None:
        facing = self._flags & Taxi._FLAG_LEFT

        mask_with_reactor = pygame.mask.from_surface(self.image)

        reactors = [
        (Taxi._FLAG_BOTTOM_REACTOR, ImgSelector.BOTTOM_REACTOR), 
        (Taxi._FLAG_TOP_REACTOR, ImgSelector.TOP_REACTOR),     
        (Taxi._FLAG_REAR_REACTOR, ImgSelector.REAR_REACTOR)
    ]

        for flag, selector in reactors:
            if self._flags & flag:
                reactor_mask = self._masks[selector][facing]
                mask_with_reactor.draw(reactor_mask, (0, 0))

        self.mask_taxi_reactor = mask_with_reactor

    def _detect_input(self) -> InputSelector:
        input_value = None
        keys = pygame.key.get_pressed()

        if self._joystick:
            x_axis = self._joystick.get_axis(0) 
            y_axis = self._joystick.get_axis(4) 

            if x_axis < -0.5: 
                input_value = InputSelector.LEFT
            elif x_axis > 0.5: 
                input_value = InputSelector.RIGHT
            elif y_axis > 0.5:  
                input_value = InputSelector.DOWN
            elif y_axis < -0.5: 
                input_value = InputSelector.UP

        if keys[pygame.K_LEFT]:
            input_value = InputSelector.LEFT
        elif keys[pygame.K_RIGHT]:
            input_value = InputSelector.RIGHT
        elif keys[pygame.K_DOWN]:
            input_value = InputSelector.DOWN
        elif keys[pygame.K_UP]:
            input_value = InputSelector.UP

        if input_value is not None:
            return input_value


    def _handle_input_action(self, action: InputSelector) -> None:
        """ Change ou non l'état du taxi en fonction des touches présentement enfoncées. """
        if self._flags & Taxi._FLAG_DESTROYED == Taxi._FLAG_DESTROYED:
            return

        gear_out = self._flags & Taxi._FLAG_GEAR_OUT == Taxi._FLAG_GEAR_OUT

        if action == InputSelector.LEFT and not gear_out:
            self._flags |= Taxi._FLAG_LEFT | Taxi._FLAG_REAR_REACTOR
            self._acceleration.x = max(self._acceleration.x - Taxi._REAR_REACTOR_POWER, -Taxi._MAX_ACCELERATION_X)

        elif action == InputSelector.RIGHT and not gear_out:
            self._flags &= ~Taxi._FLAG_LEFT
            self._flags |= self._FLAG_REAR_REACTOR
            self._acceleration.x = min(self._acceleration.x + Taxi._REAR_REACTOR_POWER, Taxi._MAX_ACCELERATION_X)

        else:
            self._flags &= ~Taxi._FLAG_REAR_REACTOR
            self._acceleration.x = 0.0

        if action == InputSelector.DOWN and not gear_out:
            self._flags &= ~Taxi._FLAG_BOTTOM_REACTOR
            self._flags |= Taxi._FLAG_TOP_REACTOR
            self._acceleration.y = min(self._acceleration.y + Taxi._TOP_REACTOR_POWER, Taxi._MAX_ACCELERATION_Y_DOWN)

        elif action == InputSelector.UP:
            self._flags &= ~Taxi._FLAG_TOP_REACTOR
            self._flags |= Taxi._FLAG_BOTTOM_REACTOR
            self._acceleration.y = max(self._acceleration.y - Taxi._BOTTOM_REACTOR_POWER, -Taxi._MAX_ACCELERATION_Y_UP)
            if self._pad_landed_on:
                self._pad_landed_on = None

        else:
            self._flags &= ~(Taxi._FLAG_TOP_REACTOR | Taxi._FLAG_BOTTOM_REACTOR)
            self._acceleration.y = 0.0

    def _reinitialize(self) -> None:
        """ Initialise (ou réinitialise) les attributs de l'instance. """
        self._flags = 0
        self._select_image()

        self.rect = self.image.get_rect()
        self.rect.x = self._initial_pos[0] - self.rect.width / 2
        self.rect.y = self._initial_pos[1] - self.rect.height / 2

        self._position = pygame.Vector2(float(self.rect.x), float(self.rect.y))
        self._velocity = pygame.Vector2(0.0, 0.0)
        self._acceleration = pygame.Vector2(0.0,0.0)

        self._pad_landed_on = None
        self._taking_off = False

        self._astronaut = None
        self._hud.set_trip_money(0.0)
        self._hud.reset_fuel()

    def _consume_fuel(self):
        """
            Consomme du carburant basé sur les réacteurs actifs.
        """
        total_consumption = 0.0
        if self._flags & Taxi._FLAG_TOP_REACTOR:
            total_consumption += Taxi._TOP_REACTOR_POWER * 50

        if self._flags & Taxi._FLAG_BOTTOM_REACTOR:
            total_consumption += Taxi._BOTTOM_REACTOR_POWER * 50

        if self._flags & Taxi._FLAG_REAR_REACTOR:
            total_consumption += Taxi._REAR_REACTOR_POWER * 50

        if total_consumption > 0.0:
            self._hud.consume_fuel(total_consumption)

        if self._hud.get_current_fuel() <= 0.0:
            self._flags = Taxi._FLAG_DESTROYED
            self._velocity.x = 0.0
            self._acceleration = pygame.Vector2(0.0, Taxi._CRASH_ACCELERATION)

    def _select_image(self) -> None:
        """ Sélectionne l'image et le masque à utiliser pour l'affichage du taxi en fonction de son état. """
        facing = self._flags & Taxi._FLAG_LEFT

        if self._flags & Taxi._FLAG_DESTROYED:
            self.image = self._surfaces[ImgSelector.DESTROYED][facing]
            self.mask = self._masks[ImgSelector.DESTROYED][facing]
            return

        condition_flags = Taxi._FLAG_TOP_REACTOR | Taxi._FLAG_REAR_REACTOR
        if self._flags & condition_flags == condition_flags:
            self.image = self._surfaces[ImgSelector.TOP_AND_REAR_REACTORS][facing]
            self.mask = self._masks[ImgSelector.TOP_AND_REAR_REACTORS][facing]
            return

        condition_flags = Taxi._FLAG_BOTTOM_REACTOR | Taxi._FLAG_REAR_REACTOR
        if self._flags & condition_flags == condition_flags:
            self.image = self._surfaces[ImgSelector.BOTTOM_AND_REAR_REACTORS][facing]
            self.mask = self._masks[ImgSelector.BOTTOM_AND_REAR_REACTORS][facing]
            return

        if self._flags & Taxi._FLAG_REAR_REACTOR:
            self.image = self._surfaces[ImgSelector.REAR_REACTOR][facing]
            self.mask = self._masks[ImgSelector.REAR_REACTOR][facing]
            return

        condition_flags = Taxi._FLAG_GEAR_OUT | Taxi._FLAG_BOTTOM_REACTOR
        if self._flags & condition_flags == condition_flags:
            self.image = self._surfaces[ImgSelector.GEAR_OUT_AND_BOTTOM_REACTOR][facing]
            self.mask = self._masks[ImgSelector.GEAR_OUT_AND_BOTTOM_REACTOR][facing]
            return

        if self._flags & Taxi._FLAG_BOTTOM_REACTOR:
            self.image = self._surfaces[ImgSelector.BOTTOM_REACTOR][facing]
            self.mask = self._masks[ImgSelector.BOTTOM_REACTOR][facing]
            return

        if self._flags & Taxi._FLAG_TOP_REACTOR:
            self.image = self._surfaces[ImgSelector.TOP_REACTOR][facing]
            self.mask = self._masks[ImgSelector.TOP_REACTOR][facing]
            return

        if self._flags & Taxi._FLAG_GEAR_OUT:
            self.image = self._surfaces[ImgSelector.GEAR_OUT][facing]
            self.mask = self._masks[ImgSelector.GEAR_OUT][facing]
            return

        if self._flags & Taxi._FLAG_DESTROYED:
            self.image = self._surfaces[ImgSelector.DESTROYED][facing]
            self.mask = self._masks[ImgSelector.DESTROYED][facing]
            return

        self.image = self._surfaces[ImgSelector.IDLE][facing]
        self.mask = self._masks[ImgSelector.IDLE][facing]

    @staticmethod
    def _load_and_build_surfaces() -> tuple:
        """
        Charge et découpe la feuille de sprites (sprite sheet) pour le taxi.
        Construit les images et les masques pour chaque état.
        :return: un tuple contenant deux dictionnaires (avec les états comme clés):
                     - un dictionnaire d'images (pygame.Surface)
                     - un dictionnaire de masques (pygame.Mask)
        """
        surfaces = {}
        masks = {}
        sprite_sheet = pygame.image.load(GameSettings.TAXIS_FILENAME).convert_alpha()
        sheet_width = sprite_sheet.get_width()
        sheet_height = sprite_sheet.get_height()

        # taxi normal - aucun réacteur - aucun train d'atterrissage
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.IDLE] = surface, flipped
        masks[ImgSelector.IDLE] = pygame.mask.from_surface(surface), pygame.mask.from_surface(flipped)

        # taxi avec réacteur du dessous
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.BOTTOM_REACTOR] = surface, flipped
        masks[ImgSelector.BOTTOM_REACTOR] = masks[ImgSelector.IDLE]

        # taxi avec réacteur du dessus
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 2 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.TOP_REACTOR] = surface, flipped
        masks[ImgSelector.TOP_REACTOR] = masks[ImgSelector.IDLE]

        # taxi avec réacteur arrière
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 3 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.REAR_REACTOR] = surface, flipped
        masks[ImgSelector.REAR_REACTOR] = masks[ImgSelector.IDLE]

        # taxi avec réacteurs du dessous et arrière
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 3 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.BOTTOM_AND_REAR_REACTORS] = surface, flipped
        masks[ImgSelector.BOTTOM_AND_REAR_REACTORS] = masks[ImgSelector.IDLE]

        # taxi avec réacteurs du dessus et arrière
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 2 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 3 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.TOP_AND_REAR_REACTORS] = surface, flipped
        masks[ImgSelector.TOP_AND_REAR_REACTORS] = masks[ImgSelector.IDLE]

        # taxi avec train d'atterrissage
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 4 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.GEAR_OUT] = surface, flipped
        masks[ImgSelector.GEAR_OUT] = pygame.mask.from_surface(surface), pygame.mask.from_surface(flipped)

        # taxi avec train d'atterrissage comprimé
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        source_rect.x = 5 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.GEAR_SHOCKS] = surface, flipped
        masks[ImgSelector.GEAR_SHOCKS] = pygame.mask.from_surface(surface), pygame.mask.from_surface(flipped)

        # taxi avec réacteur du dessous et train d'atterrissage
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        source_rect.x = 4 * source_rect.width
        surface.blit(sprite_sheet, (0, 0), source_rect)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.GEAR_OUT_AND_BOTTOM_REACTOR] = surface, flipped
        masks[ImgSelector.GEAR_OUT_AND_BOTTOM_REACTOR] = masks[ImgSelector.GEAR_OUT]

        # taxi détruit
        surface = pygame.Surface((sheet_width / Taxi._NB_TAXI_IMAGES, sheet_height), flags=pygame.SRCALPHA)
        source_rect = surface.get_rect()
        surface.blit(sprite_sheet, (0, 0), source_rect)
        surface = pygame.transform.flip(surface, False, True)
        flipped = pygame.transform.flip(surface, True, False)
        surfaces[ImgSelector.DESTROYED] = surface, flipped
        masks[ImgSelector.DESTROYED] = pygame.mask.from_surface(surface), pygame.mask.from_surface(flipped)

        return surfaces, masks


