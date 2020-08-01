#Author-Thomas Axelsson
#Description-Shows a menu that let's you assign shortcuts to your last run commands.

# This file is part of AnyShortcut, a Fusion 360 add-in for assigning
# shortcuts to the last run commands.
#
# Copyright (C) 2020  Thomas Axelsson
#
# AnyShortcut is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# AnyShortcut is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with AnyShortcut.  If not, see <https://www.gnu.org/licenses/>.

import adsk.core, adsk.fusion, adsk.cam, traceback

from collections import deque
import os

NAME = 'Any Shortcut'
FILE_DIR = os.path.dirname(os.path.realpath(__file__))

# Import relative path to avoid namespace pollution
from .thomasa88lib import utils
from .thomasa88lib import events
from .thomasa88lib import manifest
from .thomasa88lib import error
from .thomasa88lib import settings

# Force modules to be fresh during development
import importlib
importlib.reload(thomasa88lib.utils)
importlib.reload(thomasa88lib.events)
importlib.reload(thomasa88lib.manifest)
importlib.reload(thomasa88lib.error)
importlib.reload(thomasa88lib.settings)

ENABLE_CMD_DEF_ID = 'thomasa88_anyShortcutList'
MENU_DROPDOWN_ID = 'thomasa88_anyShortcutDropdown'

app_ = None
ui_ = None
error_catcher_ = thomasa88lib.error.ErrorCatcher()
events_manager_ = thomasa88lib.events.EventsManager(error_catcher_)
manifest_ = thomasa88lib.manifest.read()
settings_ = thomasa88lib.settings.SettingsManager({})
command_starting_handler_info_ = None

dropdown_ = None
enable_cmd_def_ = None
HISTORY_LENGTH = 10
cmd_def_history_ = deque()
# Keeping info in a separate container, as the search is much faster
# if we can do cmd_def in cmd_def_history, not making the GUI sluggish.
cmd_controls_ = deque()
MAX_TRACK = 10
track_count_ = 0
tracking_ = False

def command_starting_handler(args):
    event_args = adsk.core.ApplicationCommandEventArgs.cast(args)

    print("STARTING", event_args.commandId)
    cmd_def = event_args.commandDefinition

    if cmd_def == enable_cmd_def_:
        # Skip ourselves
        return
    
    if cmd_def not in cmd_def_history_:
        while len(cmd_def_history_) >= HISTORY_LENGTH:
            cmd_def_history_.popleft()
            cmd_controls_.popleft().deleteMe()
        
        print("ADD")
        try:
            # Commands without icons cannot have shortcuts, so add
            # one if needed. Maybe because the "Pin to" options in
            # the same menu would fail?
            # Creds to u/lf_1 on reddit.
            res_folder = cmd_def.resourceFolder
        except:
            cmd_def.resourceFolder = './resources/noicon'

        cmd_control = dropdown_.controls.addCommand(cmd_def)
        if cmd_control:
            cmd_def_history_.append(cmd_def)
            cmd_controls_.append(cmd_control)

            global track_count_
            track_count_ += 1
            update_enable_text()

            if track_count_ >= MAX_TRACK:
                stop_tracking()
        else:
            print("ADD FAIL", cmd_def.execute)

def enable_cmd_def__created_handler(args):
    command = args.command
    events_manager_.add_handler(command.execute,
                               adsk.core.CommandEventHandler,
                               enable_command_execute_handler)

def enable_command_execute_handler(args):
    global tracking_

    if not tracking_:
        start_tracking()
    else:
        stop_tracking()

def start_tracking():
    global tracking_
    global track_count_
    global command_starting_handler_info_
    tracking_ = True
    track_count_ = 0
    command_starting_handler_info_ = events_manager_.add_handler(ui_.commandStarting,
                                adsk.core.ApplicationCommandEventHandler,
                                command_starting_handler)
    update_enable_text()

def stop_tracking():
    global tracking_
    tracking_ = False
    events_manager_.remove_handler(command_starting_handler_info_)
    update_enable_text()

def update_enable_text():
    if tracking_:
        text = f'Enable tracking (stopping after {MAX_TRACK - track_count_} commands)'
        enable_cmd_def_.resourceFolder = thomasa88lib.utils.get_fusion_deploy_folder() + '/Neutron/UI/Base/Resources/Browser/CheckBoxChecked'
    else:
        text = f'Enable tracking (stops after {MAX_TRACK} unique commands)'
        enable_cmd_def_.resourceFolder = thomasa88lib.utils.get_fusion_deploy_folder() + '/Neutron/UI/Base/Resources/Browser/CheckBoxUnchecked'
    enable_cmd_def_.controlDefinition.name = text

def run(context):
    global app_
    global ui_
    global dropdown_
    with error_catcher_:
        app_ = adsk.core.Application.get()
        ui_ = app_.userInterface


        # Add the command to the toolbar.
        panel = ui_.allToolbarPanels.itemById('SolidScriptsAddinsPanel')

        dropdown_ = panel.controls.itemById(MENU_DROPDOWN_ID)
        if dropdown_:
            dropdown_.deleteMe()
        
        dropdown_ = panel.controls.addDropDown(f'{NAME} v{manifest_["version"]}',
                                               '', MENU_DROPDOWN_ID)
        dropdown_.resourceFolder = './resources/anyshortcut'
        
        global enable_cmd_def_
        enable_cmd_def_ = ui_.commandDefinitions.itemById(ENABLE_CMD_DEF_ID)

        if enable_cmd_def_:
            enable_cmd_def_.deleteMe()

        # Cannot get checkbox to play nicely (won't update without collapsing
        # the menu and the default checkbox icon is not showing...).
        # See checkbox-test branch.
        enable_cmd_def_ = ui_.commandDefinitions.addButtonDefinition(
            ENABLE_CMD_DEF_ID,
            f'Loading...',
            '')
        update_enable_text()
        events_manager_.add_handler(enable_cmd_def_.commandCreated,
                        adsk.core.CommandCreatedEventHandler,
                        enable_cmd_def__created_handler)
        
        dropdown_.controls.addCommand(enable_cmd_def_)
        dropdown_.controls.addSeparator()

def stop(context):
    with error_catcher_:
        events_manager_.clean_up()

        panel = ui_.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        dropdown_ = panel.controls.itemById(MENU_DROPDOWN_ID)
        if dropdown_:
            dropdown_.deleteMe()

        # Need to delete children?

