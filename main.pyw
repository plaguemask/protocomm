import configparser
import json
import os
import sys
import tkinter as tk
from enum import Enum
from pathlib import Path
from typing import Dict


def make_default_config(path: Path) -> Dict:
    """
    Overwrite a file to contain default configurations.
    :param path: Path to file
    :return: Dict containing configurations
    """
    defaults = {
        'Options': {
            'x': 10,
            'y': 10,
            'opacity': 0.8,
            'foreground_color': 'white',
            'background_color': 'black',
            'font': 'Courier New',
            'text_size': 32,
        }
    }

    # Write defaults to config file
    cfp = configparser.ConfigParser()
    cfp.read_dict(defaults)
    with open(path, 'w', encoding='utf-8') as f:
        cfp.write(f)

    return defaults


def load_config(path: Path) -> Dict:
    """
    Load user's configurations from the config file. Creates config file if none exists.
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


def make_default_commands_file(path: Path) -> Dict:
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


def load_commands_file(path: Path) -> Dict:
    """
    Load the commands file. If none found, create a new one with default commands.
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


def run_command(commands_file_path: Path, command: str) -> CommandStatus:
    """
    Try to run a command.
    :param commands_file_path: Path to commands file
    :param command: String input
    :return: CommandStatus describing result of attempt to run command
    """
    command = command.strip()

    if command:
        command = command.lower()

        commands = load_commands_file(commands_file_path)

        if command in commands:
            try:
                os.startfile(commands[command])
                return CommandStatus.SUCCESS
            except FileNotFoundError:
                return CommandStatus.MISSING_FILE
        else:
            return CommandStatus.INVALID


def flash_widget_background(widget: tk.Widget, color: str, duration: int = 200) -> None:
    """Make a widget's background turn a color for an amount of time."""
    bg_color = widget['bg']
    widget.config(bg=color)
    widget.after(duration, lambda: widget.config(bg=bg_color))


def clear_entry(entry: tk.Entry) -> None:
    """Clear the contents of the entry widget."""
    entry.delete(0, len(entry.get()))


def handle_return(window: tk.Tk, entry: tk.Entry, commands_file_path: Path) -> None:
    """Process command and give visual feedback for an error."""
    command_status = run_command(commands_file_path, entry.get())

    if command_status == CommandStatus.SUCCESS:
        close_window(window)

    elif command_status == CommandStatus.INVALID:
        clear_entry(entry)
        flash_widget_background(entry, 'red')

    elif command_status == CommandStatus.MISSING_FILE:
        clear_entry(entry)
        flash_widget_background(entry, 'orange')


def close_window(window: tk.Tk) -> None:
    """
    Close the window and exit the program.
    :param window: The window to close
    :return: None
    """
    window.destroy()
    sys.exit()


def main() -> None:
    config_path = Path('config.ini')
    commands_path = Path('commands.json')

    # Load config
    config_dict = load_config(config_path)
    x = config_dict['Options']['x']
    y = config_dict['Options']['y']
    opacity = config_dict['Options']['opacity']
    fg = config_dict['Options']['foreground_color']
    bg = config_dict['Options']['background_color']
    font = config_dict['Options']['font']
    text_size = int(config_dict['Options']['text_size'])

    # Create top-level window
    window = tk.Tk()

    # Create text entry box
    entry_box = tk.Entry(window,
                         cnf={
                             'fg': fg,
                             'bg': bg,
                             'font': (font, text_size)
                         })

    # Make entry box span entire window
    entry_box.grid(row=0, column=0)

    # Add handlers for keyboard and window events
    window.bind('<Return>', lambda _: handle_return(window, entry_box, commands_path))
    window.bind('<Escape>', lambda _: close_window(window))
    window.bind('<FocusOut>', lambda _: close_window(window))

    # Remove toolbar from window
    window.overrideredirect(True)

    # Place window at user specification
    window.geometry(f'+{x}+{y}')

    # Add some transparency
    window.attributes('-alpha', opacity)

    # Force window to foreground and give focus to the text entry box
    window.focus_force()
    entry_box.focus_set()

    # Start window's update loop
    window.mainloop()


if __name__ == '__main__':
    main()
