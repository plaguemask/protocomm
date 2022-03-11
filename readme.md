# Protocomm

A simple command line that does exactly what you want it to. Think a pared down Windows Run that's a bit sleeker and
customizable.

Add specific commands in `commands.json` that point to files or directories to be opened. Customize where Protocomm
appears and how it looks in `config.ini`. These two files will be created when `main.pyw` runs for the first time.

When `protocomm.ahk` is running, pull up Protocomm with `Ctrl + \ `. Type in a command and Protocomm will open what it
points to before closing itself. Entering something that's not in `commands.json` will make it flash red, and entering a
command that points to a non-existent file/directory will make it flash orange. Protocomm will automatically close
quietly if it loses focus, you press Escape, or you enter an empty command.

The commands `commands` and `config` are included by default, pointing to the `commands.json` and `config.ini` files,
respectively.

Works best when `protocomm.ahk` is launched on startup.