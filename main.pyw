import os
import re
import sys
import json
import logging
import argparse
import subprocess
import configparser
from enum import Enum
from pathlib import Path
from dataclasses import dataclass

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QKeyEvent, QFocusEvent
from PyQt6.QtWidgets import QMainWindow, QWidget, QLineEdit, QApplication


logger = logging.getLogger(__name__)


class CommandStatus(Enum):
    SUCCESS = 0,
    INVALID = 1,
    MISSING_FILE = 2


class CommandManager:

    """Class representation of available Protocomm commands."""

    def __init__(self, commands: dict):
        self.commands = commands

    def load_from_file(self, path: Path) -> None:
        """
        Load a commands file. If one does not exist at the path, create a new one with default commands.
        :param path: Path to commands file.
        :return: Dict of string command keys and string file path values.
        """
        if not os.path.exists(path):
            logger.warning(f'Commands file at "{path}" does not exist')
            self.write_to_file(path)

        logger.info(f'Loading commands from "{path}"')
        with open(path, encoding='utf-8') as f:
            data = f.read().replace('\n', '')

        commands_from_file = json.loads(data)
        for c in commands_from_file:
            self.commands[c] = commands_from_file[c]

    def write_to_file(self, path: Path) -> None:
        """
        Write commands to file, formatted with new-lines between entries.
        :param path: Path to file
        :return: None
        """
        logger.info(f'Writing commands to "{path}"')

        # Write json fancily to file
        with open(path, 'w', encoding='utf-8') as f:
            f.write('{')

            commands_str = ''
            for c in self.commands:
                commands_str += f'\n\t"{c}": "{self.commands[c].as_posix()}",'

            f.write(commands_str[:-1])  # Avoid trailing comma
            f.write('\n}')

    def run_command(self, command: str) -> CommandStatus:
        """
        Try to run a command.
        :param command: String input
        :return: CommandStatus describing result of attempt to run command
        """
        logger.info(f'Command entry: "{command}"')

        command = command.lower().strip()

        if command:
            if command in self.commands:
                logger.info(f'Found command "{command}"')
                operation = self.commands[command]
                try:
                    if type(operation) == list:
                        # Replace special phrase {CLIPBOARD} with clipboard's contents
                        clipboard_text = QApplication.clipboard().text()
                        for i in range(len(operation)):
                            operation[i] = re.sub('({CLIPBOARD})', clipboard_text, operation[i])

                        logger.info(f'Running "{operation}"')
                        subprocess.run(operation, shell=True)
                    else:
                        logger.info(f'Opening "{operation}"')
                        os.startfile(operation)
                    return CommandStatus.SUCCESS

                except FileNotFoundError:
                    logger.error(f'File "{operation}" not found')
                    return CommandStatus.MISSING_FILE
            else:
                logger.info(f'Command "{command}" not found')
                return CommandStatus.INVALID


class NoCursorQLineEdit(QLineEdit):

    """A version of QLineEdit that hides the blinking text cursor."""

    def __init__(self, parent: QWidget):
        super().__init__(parent=parent)

        # Read-only mode is what hides the cursor
        self.setReadOnly(True)

    def keyPressEvent(self, e: QKeyEvent) -> None:
        # Disable read-only mode to process key events, then re-enable afterwards
        self.setReadOnly(False)

        super().keyPressEvent(e)
        logger.debug(f'{self.__class__.__name__}: keyPressEvent: {Qt.Key(e.key()).name}')

        self.setReadOnly(True)

    def focusOutEvent(self, e: QFocusEvent) -> None:
        # Quit application on focus out
        logger.debug(f'{self.__class__.__name__}: FocusOut event')
        exit_app()


@dataclass
class ProtocommWindowConfig:

    """Class representation of available Protocomm configurations."""

    x: int = 10
    y: int = 10
    width: int = 600
    height: int = 42
    padding: int = 8
    text_size: int = 32
    font: str = 'Courier New'
    fg_color: str = '#FFFFFF'
    bg_color: str = '#000000'
    opacity: float = 0.75

    def load_from_file(self, path: Path) -> None:
        """
        Load a configuration file. If one does not exist at the path, create a new one with default configurations.
        :param path: Path to file
        :return: Dict containing configurations
        """
        cfp = configparser.ConfigParser()

        # If config file doesn't exist, create one with defaults
        if not os.path.exists(path):
            logger.warning(f'Config file does not exist at "{path}"')
            self.write_to_file(path)

        logger.info(f'Loading configurations from "{path}"')
        cfp.read(path)
        o = cfp['Options']

        # Get a list of variables in this class and their respective types
        var_types = self.__class__.__dict__['__annotations__']
        for v in var_types:

            try:
                logger.debug(f'Processing variable {v}...')
                v_type = var_types[v]
                conf_value = o[v]

                if var_types[v] != str:
                    # Take the option in the config file with the variable's name and convert it to the variable's type
                    # e.g. for config x = 10: var_types[v] = int, o[v] = "10", ergo v_type(conf_value) -> int("10")
                    logger.debug(f'Converting config value {conf_value} to {v_type}')
                    conf_value = v_type(conf_value)

                # Then set the variable to that value
                logger.debug(f'Setting variable {v} to {conf_value}')
                setattr(self, v, conf_value)

            except Exception as e:
                logger.exception(e)

    def write_to_file(self, path: Path) -> None:
        """
        Write current configuration to file.
        :param path: Path to file
        :return: None
        """
        # Write defaults to config file
        logger.info(f'Writing configurations to "{path}"')

        cfp = configparser.ConfigParser()

        config_dict = {'Options': vars(self)}
        cfp.read_dict(config_dict)
        with open(path, 'w', encoding='utf-8') as f:
            cfp.write(f)


class ProtocommWindow(QMainWindow):

    """The main user interface of Protocomm"""

    def __init__(self, config: ProtocommWindowConfig, cm: CommandManager):
        super().__init__()
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)

        self.config = config
        self.cm = cm

        self.initUI()

    def initUI(self):
        logger.debug('Initializing UI')

        self.timer = QTimer(self)
        self.setGeometry(self.config.x,
                         self.config.y,
                         self.config.width + self.config.padding * 2,
                         self.config.height + self.config.padding * 2)
        self.setWindowOpacity(self.config.opacity)
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint  # Hides window's title bar
            | Qt.WindowType.WindowStaysOnTopHint  # Force window to top
            | Qt.WindowType.SplashScreen  # Hides window from task bar
        )
        self.setWindowTitle('Protocomm')

        logger.debug('Initializing QWidget')
        self.frame = QWidget(self)
        self.frame.setGeometry(0,
                               0,
                               self.config.width + self.config.padding * 2,
                               self.config.height + self.config.padding * 2)
        self.frame.setStyleSheet(
            f'background-color: {self.config.bg_color}; border-radius: {int(self.config.height * 0.3)}px;')

        logger.debug('Initializing NoCursorQLineEdit')
        self.le = NoCursorQLineEdit(self.frame)
        self.le.setGeometry(self.config.padding,
                            self.config.padding,
                            self.config.width,
                            self.config.height)
        self.le.setFrame(False)
        self.le.setReadOnly(True)
        self.le.setStyleSheet(f"""
            QLineEdit{{
                background-color: {self.config.bg_color};
                color: {self.config.fg_color};
                font-family: {self.config.font};
                font-size: {self.config.text_size}pt;
                border-radius: {int(self.config.height * 0.2)}px;
            }}
        """)

        logger.debug('Stealing focus')
        self.frame.setFocusProxy(self.le)
        self.setFocusProxy(self.le)
        self.setFocusPolicy(Qt.FocusPolicy.ClickFocus)
        self.setFocus()

        logger.debug('Showing ProtocommWindow')
        self.show()

    def flash(self, color: str, duration: int) -> None:
        logger.debug(f'Flashing {color} for {duration}ms')

        current_style = self.frame.styleSheet()
        self.frame.setStyleSheet(f'background-color: {color}; border-radius: {int(self.config.height * 0.3)}px;')

        def timeout(obj, style):
            logger.debug('Duration has ended. Resetting style.')
            obj.frame.setStyleSheet(style)
            obj.timer.timeout.disconnect()

        self.timer.timeout.connect(lambda: timeout(self, current_style))

        logger.debug(f'Starting timer')
        self.timer.start(duration)

    def clear(self):
        logger.debug(f'Clearing text entry box')
        self.le.setText('')

    def keyPressEvent(self, e: QKeyEvent) -> None:
        logger.info(f'{self.__class__.__name__}: keyPressEvent: {Qt.Key(e.key()).name}')

        if e.key() == Qt.Key.Key_Escape.value:
            logger.debug(f'Unfocusing self')
            self.clearFocus()

        if e.key() == Qt.Key.Key_Return.value:
            result = self.cm.run_command(self.le.text())
            if result == CommandStatus.SUCCESS:
                self.clearFocus()
            elif result == CommandStatus.INVALID:
                self.clear()
                self.flash('#FF0000', duration=200)
            elif result == CommandStatus.MISSING_FILE:
                self.clear()
                self.flash('#FF8800', duration=200)


def exit_app():
    """Quits QApplication instance."""
    logger.info('Closing app')
    QApplication.instance().quit()


def main() -> None:
    try:
        # Defaults for when no command line arguments are given
        log_path = Path('protocomm.log')
        commands_path = Path('commands.json')
        config_path = Path('config.ini')

        # Parse command line arguments
        if sys.argv[1:]:
            logger.debug(f'Additional command line arguments given: {sys.argv[1:]}')
            parser = argparse.ArgumentParser(
                description='Protocomm: A simple command line that does exactly what you want it to.'
            )
            parser.add_argument('--configfile', type=str, help='Path to configuration file')
            parser.add_argument('--commandsfile', type=str, help='Path to command list file')
            parser.add_argument('--logfile', type=str, help='Path to log file')
            args = parser.parse_args()

            if args.configfile:
                logger.debug(f'Setting config file to "{args.configfile}"')
                config_path = args.configfile
            if args.commandsfile:
                logger.debug(f'Setting commands file to "{args.commandsfile}"')
                commands_path = args.commandsfile
            if args.logfile:
                logger.debug(f'Setting log file to "{args.logfile}"')
                log_path = args.logfile

        # Configure logging
        logging.basicConfig(filename=log_path,
                            filemode="w",
                            encoding='utf-8',
                            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                            level=logging.DEBUG)

        # Load config
        logger.debug(f'Initializing ProtocommWindowConfig')
        config = ProtocommWindowConfig()
        config.load_from_file(config_path)

        # Load commands
        commands = CommandManager({
            "commands": commands_path,
            "config": config_path
        })
        commands.load_from_file(commands_path)

        # Start app with arguments from command line
        logger.debug(f'Initializing QApplication')
        app = QApplication(sys.argv)

        logger.debug(f'Initializing ProtocommWindow')
        pcw = ProtocommWindow(config, commands)

        # Enter main loop
        logger.info(f'Entering main loop')
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
