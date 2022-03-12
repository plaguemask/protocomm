import configparser
import json
import os
import sys
from enum import Enum
from typing import Dict
import logging

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QFocusEvent
from PyQt6.QtWidgets import QMainWindow, QWidget, QLineEdit, QApplication


# Enable logging
LOG = "./protocomm.log"
logging.basicConfig(filename=LOG,
                    filemode="w",
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.DEBUG)
logger = logging.getLogger(__name__)


def make_default_config(path: str) -> Dict:
    """
    Overwrite a file to contain default configurations.
    :param path: Path to file
    :return: Dict containing configurations
    """
    defaults = {
        'Options': {
            'x': 10,
            'y': 10,
            'width': 800,
            'height': 64,
            'text_size': 32,
            'font': 'Courier New',
            'foreground_color': 'white',
            'background_color': 'black',
            'opacity': 0.75,
        }
    }

    # Write defaults to config file
    logger.info(f'Writing default configurations to {path}...')

    cfp = configparser.ConfigParser()
    cfp.read_dict(defaults)
    with open(path, 'w', encoding='utf-8') as f:
        cfp.write(f)

    logger.info('Writing default configurations successful.')

    return defaults


def load_config(path: str) -> Dict:
    """
    Load user's configuration file. If none found, create a new one with default commands.
    :param path: Path to file
    :return: Dict containing configurations
    """
    cfp = configparser.ConfigParser()

    # If config file doesn't exist, create one with defaults
    if not os.path.exists(path):
        logger.warning(f'Config file does not exist. Creating one with defaults...')
        return make_default_config(path)

    logger.info(f'Loading configurations from {path}...')
    cfp.read(path)
    logger.info('Loading configurations successful.')

    # If config file empty or formatted incorrectly, nuke it and replace with defaults
    if 'Options' not in cfp:
        logger.warning(f'Config file formatted incorrectly, replacing with defaults...')
        return make_default_config(path)

    # Otherwise, return with configs present in file
    return dict(cfp)


def make_default_commands_file(path: str) -> Dict:
    """
    Overwrite a file to contain default commands.
    :param path: Path to file
    :return: Dict containing commands
    """
    defaults = {
        "commands": "commands.json",
        "config": "config.ini"
    }

    # Write json fancily to file
    logger.info(f'Writing default commands to {path}...')

    with open(path, 'w', encoding='utf-8') as f:
        f.write('{')

        commands_str = ''
        for c in defaults:
            commands_str += f'\n\t"{c}": "{defaults[c]}",'

        f.write(commands_str[:-1])  # Avoid trailing comma
        f.write('\n}')

    logger.info('Writing default commands successful.')

    return defaults


def load_commands_file(path: str) -> Dict:
    """
    Load user's commands file. If none found, create a new one with default commands.
    :param path: Path to commands file.
    :return: Dict of string command keys and string file path values.
    """
    # If commands file doesn't exist, create one with defaults
    if not os.path.exists(path):
        logger.warning(f'Commands file does not exist. Creating one with defaults...')
        return make_default_commands_file(path)

    logger.info(f'Loading commands from {path}...')
    with open(path, encoding='utf-8') as f:
        data = f.read().replace('\n', '')
    logger.info('Loading commands successful.')

    d = json.loads(data)
    return d


class CommandStatus(Enum):
    SUCCESS = 0,
    INVALID = 1,
    MISSING_FILE = 2


def run_command(command: str) -> CommandStatus:
    """
    Try to run a command.
    :param command: String input
    :return: CommandStatus describing result of attempt to run command
    """

    logger.info(f'Command entry: "{command}"')

    command = command.strip()

    if command:
        command = command.lower()

        commands = load_commands_file('commands.json')

        if command in commands:
            logger.info(f'Found command "{command}".')
            command_path = commands[command]
            try:
                logger.info(f'Opening "{command_path}"...')
                os.startfile(command_path)

                logger.info(f'Command ran successfully.')
                return CommandStatus.SUCCESS

            except FileNotFoundError:
                logger.error(f'File "{command_path}" not found.')
                return CommandStatus.MISSING_FILE
        else:
            logger.info(f'Command "{command}" not found.')
            return CommandStatus.INVALID


class NoCursorQLineEdit(QLineEdit):
    def __init__(self, parent: QWidget):
        super().__init__(parent=parent)
        self.setReadOnly(True)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        self.setReadOnly(False)
        super().keyPressEvent(e)
        self.setReadOnly(True)

    def focusOutEvent(self, e: QFocusEvent) -> None:
        logger.debug(f'{self.__class__}: FocusOut event')
        exit_app(self)


def exit_app(obj):
    logger.info(f'{obj.__class__}: Closing app...')
    QApplication.instance().quit()


class ProtocommWindow(QMainWindow):
    def __init__(self, x: int, y: int, width: int, height: int, padding: int, text_size: int, font: str, fg_color: str, bg_color: str,
                 opacity: float):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.x = x
        self.y = y
        self.width = width
        self.height = height
        self.padding = padding
        self.text_size = text_size
        self.font = font
        self.fg_color = fg_color
        self.bg_color = bg_color
        self.opacity = opacity

        logger.debug('Initializing UI...')
        self.initUI()

    def initUI(self):
        self.timer = QTimer(self)
        self.setGeometry(self.x, self.y, self.width + self.padding * 2, self.height + self.padding * 2)
        self.setWindowOpacity(self.opacity)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint  # Hides window's title bar
            | Qt.WindowType.WindowStaysOnTopHint  # Force window to top
            | Qt.WindowType.SplashScreen  # Hides window from task bar
        )
        self.setWindowTitle('Protocomm')

        logger.debug('Initializing QWidget...')
        self.frame = QWidget(self)
        self.frame.setGeometry(0, 0, self.width + self.padding * 2, self.height + self.padding * 2)
        self.frame.setStyleSheet(f'background-color: {self.bg_color}; border-radius: {int(self.height * 0.3)}px;')

        logger.debug('Initializing NoCursorQLineEdit...')
        self.le = NoCursorQLineEdit(self.frame)
        self.le.setGeometry(self.padding, self.padding, self.width, self.height)
        self.le.setFrame(False)
        self.le.setReadOnly(True)
        self.le.setStyleSheet(f"""
            QLineEdit{{
                background-color: {self.bg_color};
                color: {self.fg_color};
                font-family: {self.font};
                font-size: {self.text_size}pt;
                border-radius: {int(self.height * 0.2)}px;
            }}
        """)

        logger.debug('Stealing focus...')
        self.frame.setFocusProxy(self.le)
        self.setFocusProxy(self.le)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setFocus()

        logger.debug('Displaying...')
        self.show()

    def flash(self, color: str, duration: int) -> None:
        logger.info(f'Flashing {color} for {duration}ms...')

        current_style = self.frame.styleSheet()
        self.frame.setStyleSheet(f'background-color: {color}; border-radius: {int(self.height * 0.3)}px;')

        def timeout(obj, style):
            logger.debug('Duration has ended. Resetting style...')
            obj.frame.setStyleSheet(style)
            obj.timer.timeout.disconnect()
        self.timer.timeout.connect(lambda: timeout(self, current_style))

        logger.debug(f'Starting timer...')
        self.timer.start(duration)

    def clear(self):
        logger.debug(f'Clearing text entry box...')
        self.le.setText('')

    def keyPressEvent(self, e: QKeyEvent) -> None:
        logger.debug(f'Key event: {e.text()}')

        if e.key() == Qt.Key.Key_Escape.value:
            exit_app(self)
        if e.key() == Qt.Key.Key_Return.value:
            result = run_command(self.le.text())
            if result == CommandStatus.SUCCESS:
                exit_app(self)
            elif result == CommandStatus.INVALID:
                self.clear()
                self.flash('#FF0000', duration=200)
            elif result == CommandStatus.MISSING_FILE:
                self.clear()
                self.flash('#FF8800', duration=200)


def main() -> None:

    # Load config
    config_dict = load_config('config.ini')
    options = config_dict['Options']

    # Start app with arguments from command line
    logger.debug(f'Initializing QApplication...')
    app = QApplication(sys.argv)

    logger.debug(f'Initializing ProtocommWindow...')
    pcw = ProtocommWindow(
        x=int(options['x']),
        y=int(options['y']),
        width=int(options['width']),
        height=int(options['height']),
        padding=int(options['padding']),
        text_size=int(options['text_size']),
        font=options['font'],
        fg_color=options['foreground_color'],
        bg_color=options['background_color'],
        opacity=float(options['opacity'])
    )

    # Enter main loop (and close program if application is ended)
    logger.info(f'Entering main loop...')
    try:
        app.exec()
    except Exception as e:
        logger.exception(e)

    sys.exit()

    # TODO: Features to implement...
    #   ✓ text entry
    #   ✓ remove window title
    #   ~ forcing focus
    #      ✓ force focus from windowed
    #      ✗ force focus from fullscreen applications
    #   ✓ transparency
    #   ✓ event handling
    #      ✓ enter
    #      ✓ escape
    #      ✓ focus loss
    #   ✓ configurations


if __name__ == '__main__':
    main()
