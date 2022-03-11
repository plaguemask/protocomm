import configparser
import json
import os
import sys
from enum import Enum
from typing import Dict

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QFocusEvent
from PyQt6.QtWidgets import QMainWindow, QWidget, QLineEdit, QApplication


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
    cfp = configparser.ConfigParser()
    cfp.read_dict(defaults)
    with open(path, 'w', encoding='utf-8') as f:
        cfp.write(f)

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
        return make_default_config(path)

    cfp.read(path)

    # If config file empty or formatted incorrectly, nuke it and replace with defaults
    if 'Options' not in cfp:
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
    with open(path, 'w', encoding='utf-8') as f:
        f.write('{')

        commands_str = ''
        for c in defaults:
            commands_str += f'\n\t"{c}": "{defaults[c]}",'

        f.write(commands_str[:-1])  # Avoid trailing comma
        f.write('\n}')

    return defaults


def load_commands_file(path: str) -> Dict:
    """
    Load user's commands file. If none found, create a new one with default commands.
    :param path: Path to commands file.
    :return: Dict of string command keys and string file path values.
    """
    # If commands file doesn't exist, create one with defaults
    if not os.path.exists(path):
        return make_default_commands_file(path)

    with open(path, encoding='utf-8') as f:
        data = f.read().replace('\n', '')
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
    command = command.strip()

    if command:
        command = command.lower()

        commands = load_commands_file('commands.json')

        if command in commands:
            try:
                os.startfile(commands[command])
                return CommandStatus.SUCCESS
            except FileNotFoundError:
                return CommandStatus.MISSING_FILE
        else:
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

        self.frame = QWidget(self)
        self.frame.setGeometry(0, 0, self.width + self.padding * 2, self.height + self.padding * 2)
        self.frame.setStyleSheet(f'background-color: {self.bg_color}; border-radius: {int(self.height * 0.3)}px;')

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

        self.frame.setFocusProxy(self.le)
        self.setFocusProxy(self.le)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setFocus()

        self.show()

    def flash(self, color: str, duration: int) -> None:
        current_style = self.frame.styleSheet()
        self.frame.setStyleSheet(f'background-color: {color}; border-radius: {int(self.height * 0.3)}px;')
        self.timer.timeout.connect(lambda: self.frame.setStyleSheet(current_style))
        self.timer.start(duration)

    def clear(self):
        self.le.setText('')

    def keyPressEvent(self, e: QKeyEvent) -> None:
        if e.key() == Qt.Key.Key_Escape.value:
            QApplication.instance().quit()
        if e.key() == Qt.Key.Key_Return.value:
            result = run_command(self.le.text())
            if result == CommandStatus.SUCCESS:
                QApplication.instance().quit()
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
    app = QApplication(sys.argv)

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
    sys.exit(app.exec())

    # TODO: Features to implement...
    #   ✓ text entry
    #   ✓ remove window title
    #   ~ forcing focus
    #   ✓ transparency
    #   ✓ event handling
    #      ✓ enter
    #      ✓ escape
    #      ✓ focus loss
    #   ✓ configurations


if __name__ == '__main__':
    main()
