# AnyShortcut

AnyShortcut is a Fusion 360 add-in for easily assigning keyboard shortcuts to commands where it is not usually possible to assign a shortcut*. It also has some built-in commands for Fusion 360 commands that cannot easily be capture and run without some extra tweaking (e.g. *Look At Sketch*).

## Tracking

When enabled, the add-in tracks the resulting commands of actions that the user performs and collects them in the *AnyShortcut* menu. The commands in the menu can then be assigned shortcut keys in the regular way.

If not stopped, the tracking stops automatically after a number of commands, to avoid any performance degradation when the user is not setting up shortcuts.

\* Not all actions in Fusion 360 result in "Commands" and some commands are not usable on their own. For example, *Pick Circle/Arc Tangent* does not generate a "Command" and *Roll History Marker Here* is triggered when clicking rewind in the history, but rewind actually first selects an item and then rolls. See 

![Screenshot](screenshot.png)

### Usage

To set up a shortcut:

* Click *Enable tracking* and then perform the command you want to create a shortcut for
* If you are lucky, the command will now have appeared at the bottom of the *AnyShortcut* menu.
* Find the command in the menu and click the three dots to assign a shortcut as usual.

To remove a shortcut, follow the same procedure. Hint: You can press the shortcut to trigger the command to be run.

## Built-in Commands

The built-in commands are always visible in the *AnyShortcut* menu. Assign shortcuts to them in the usual way.

## Installation

Download the add-in from the [Releases](https://github.com/thomasa88/AnyShortcut/releases) page.

Unpack it into `API\AddIns` (see [How to install an add-in or script in Fusion 360](https://knowledge.autodesk.com/support/fusion-360/troubleshooting/caas/sfdcarticles/sfdcarticles/How-to-install-an-ADD-IN-and-Script-in-Fusion-360.html)).

Make sure the directory is named `AnyShortcut`, with no suffix.

Press Shift+S in Fusion 360 and go to the *Add-Ins* tab. Then select the add-in and click the *Run* button. Optionally select *Run on Startup* (This is needed if you want the *AnyShortcut* built-in commands to function after restarting Fusion 360).

The new menu *TOOLS* -> *ADD-INS* -> *AnyShortcut* is now available.

## Ideas for commands to map

Here is a table of some commands that can be interesting to map, including a suggested key.

| Key  | Command                  | Notes                                                        |
| ---- | ------------------------ | ------------------------------------------------------------ |
| F2   | Rename, in the timeline  | Let's you select an item in the timeline and press F2 to rename it. I have not found any way to do this in the browser. |
|      | Look at (bottom toolbar) | Select a face and orient the view normal to it. I have not found any way to tell it to "Look at" the current. |
|      | Isolate                  |                                                              |
|      | Find in Browser          |                                                              |
|      | Find in Window           |                                                              |
|      | Activate Component       | Works in the Browser and in the 3D space, but you must have selected a component in 3D space, not a body or a face. |

## Finding out what keys you have mapped

See [KeyboardShortcutsSimple](https://github.com/thomasa88/KeyboardShortcutsSimple/blob/master/README.md).