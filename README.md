# AnyShortcut

A Fusion 360 add-in for easily assigning keyboard shortcuts to many* commands.

When enabled, the add-in tracks the resulting commands of actions that the user performs and collects them in a menu. The commands in the menu can be assigned shortcut keys in the regular way.

\* Not all actions result in "Commands" in Fusion 360 and some commands are not usable on their own. Typical commands act on the Design space in some way. For example, *Find in Browser* and *Isolate* can be mapped, while *Pick Circle/Arc Tanget* does not generate a "Command" and *Roll History Marker Here* is a command, but it would need input on where to move the marker, which can not be provided (However, moving the history marker can be done by a script or add-in).

![Screenshot](screenshot.png)

## Installation
Drop the files in `%appdata%\Autodesk\Autodesk Fusion 360\API\AddIns` .

Make sure the directory is named `AnyShortcut`, with no suffix.

## Usage

Press Shift+S in Fusion 360 and go to the *Add-Ins* tab. Then select the add-in and click the *Run* button. Optionally select *Run on Startup*.

The new menu *TOOLS* -> *ADD-INS* -> *Any Shortcut* is now available.

To set up a shortcut:

* Click *Enable tracking* and then perform the command you want to create a shortcut for
* If you are lucky, the command will now have appeared in the menu.
* Find the command in the menu and click the three dots to assign a shortcut as usual.

To remove a shortcut, follow the same procedure. Hint: You can press the shortcut to trigger the command to be run.

