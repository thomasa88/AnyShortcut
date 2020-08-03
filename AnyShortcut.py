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
import threading
import time

NAME = 'AnyShortcut'
FILE_DIR = os.path.dirname(os.path.realpath(__file__))

# Import relative path to avoid namespace pollution
from .thomasa88lib import utils
from .thomasa88lib import events
from .thomasa88lib import manifest
from .thomasa88lib import error
from .thomasa88lib import settings
from .thomasa88lib import timeline

# Force modules to be fresh during development
import importlib
importlib.reload(thomasa88lib.utils)
importlib.reload(thomasa88lib.events)
importlib.reload(thomasa88lib.manifest)
importlib.reload(thomasa88lib.error)
importlib.reload(thomasa88lib.settings)
importlib.reload(thomasa88lib.timeline)

ENABLE_CMD_DEF_ID = 'thomasa88_anyShortcutList'
MENU_DROPDOWN_ID = 'thomasa88_anyShortcutDropdown'
BUILTIN_DROPDOWN_ID = 'thomasa88_anyShortcutPremadeDropdown'
DELAYED_EVENT_ID = 'thomasa88_anyShortcutEndOfQueueEvent'

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

next_delay_id_ = 0
delayed_funcs_ = {}

termination_funcs_ = []
termination_handler_info_ = None

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
                                callback=enable_command_execute_handler)

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
                                                                 callback=command_starting_handler)
    update_enable_text()

def stop_tracking():
    global tracking_
    tracking_ = False
    events_manager_.remove_handler(command_starting_handler_info_)
    update_enable_text()

def update_enable_text():
    if tracking_:
        text = f'Enable tracking ({MAX_TRACK - track_count_} more unique commands)'
        enable_cmd_def_.resourceFolder = thomasa88lib.utils.get_fusion_deploy_folder() + '/Neutron/UI/Base/Resources/Browser/CheckBoxChecked'
    else:
        text = f'Enable tracking ({MAX_TRACK} unique commands)'
        enable_cmd_def_.resourceFolder = thomasa88lib.utils.get_fusion_deploy_folder() + '/Neutron/UI/Base/Resources/Browser/CheckBoxUnchecked'
    enable_cmd_def_.controlDefinition.name = text

def look_at_sketch_handler(args):
    # Look at is usually not added to the history. Skip transaction (command).
    edit_object = app_.activeEditObject
    if edit_object.classType() == 'adsk::fusion::Sketch':
        # laughingcreek provided the way that Fusion actually does this "Look At"
        # https://forums.autodesk.com/t5/fusion-360-design-validate/shortcut-for-look-at/m-p/9517669/highlight/true#M217044
        ui_.activeSelections.clear()
        ui_.activeSelections.add(edit_object)
        ui_.commandDefinitions.itemById('LookAtCommand').execute()

        # We must give the Look At command time to run. This seems to imitate the
        # way that Fusion does it.
        # Using lambda to get fresh/valid instance of activeSelections at the end of
        # the wait.
        on_command_terminate('LookAtCommand',
                             adsk.core.CommandTerminationReason.CancelledTerminationReason,
                             lambda: ui_.activeSelections.clear())
        #delay(lambda: ui_.activeSelections.clear(), secs=1)

def look_at_sketch_or_selected_handler(args):
    # Look at is usually not added to the history. Skip transaction (command).
    if ui_.activeSelections.count == 0:
        edit_object = app_.activeEditObject
        if edit_object.classType() == 'adsk::fusion::Sketch':
            look_at_sketch_handler(args)
    else:
        ui_.commandDefinitions.itemById('LookAtCommand').execute()

def activate_containing_component_handler(args):
    if ui_.activeSelections.count == 1:
        selected = ui_.activeSelections[0].entity
        if selected.classType() not in ['adsk::fusion::Component', 'adsk::fusion::Occurrence']:
            ui_.activeSelections.clear()
            ui_.activeSelections.add(selected.assemblyContext)
        ui_.commandDefinitions.itemById('FusionActivateLocalCompCmd').execute()
        ui_.commandDefinitions.itemById('FindInBrowser').execute()

def create_roll_history_handler(move_function_name):
    # Cannot use select + the native FusionRollCommand, due to this bug (2020-08-02):
    # https://forums.autodesk.com/t5/fusion-360-api-and-scripts/cannot-select-object-in-component-using-activeselections/m-p/9653216

    def execute_handler(args):
        args = adsk.core.CommandEventArgs.cast(args)
        timeline_status, timeline = thomasa88lib.timeline.get_timeline()
        if timeline_status != thomasa88lib.timeline.TIMELINE_STATUS_OK:
            args.executeFailed = True
            args.executeFailedMessage = 'Failed to get the timeline'
            return
        move_function = getattr(timeline, move_function_name)
        move_function()

    def created_handler(args):
        args = adsk.core.CommandCreatedEventArgs.cast(args)
        events_manager_.add_handler(args.command.execute,
                                    callback=execute_handler)

    return created_handler

def create_view_orientation_handler(view_orientation_name):
    def created_handler(args):
        # We don't want undo history, so no execute handler
        args = adsk.core.CommandCreatedEventArgs.cast(args)

        camera_copy = app_.activeViewport.camera
        #camera_copy.isSmoothTransition = False # This seems to be ignored
        camera_copy.viewOrientation = getattr(adsk.core.ViewOrientations,
                                              view_orientation_name + 'ViewOrientation')
        app_.activeViewport.camera = camera_copy

        def rotate_up():
            camera_copy = app_.activeViewport.camera
            if view_orientation_name in ['Top', 'Bottom']:
                up = adsk.core.Vector3D.create(0.0, 1.0, 0.0)
            else:
                up = adsk.core.Vector3D.create(0.0, 0.0, 1.0)
            camera_copy.upVector = up
            app_.activeViewport.camera = camera_copy
        
        delay(rotate_up, secs=1)

    return created_handler

def delayed_event_handler(args):
    args = adsk.core.CustomEventArgs.cast(args)
    delay_id = int(args.additionalInfo)
    func = delayed_funcs_.pop(delay_id, lambda: None)
    func()

def delay(func, secs=0):
    '''Puts a function at the end of the event queue,
    and optionally delays it.
    '''
    global next_delay_id_
    delay_id = next_delay_id_
    next_delay_id_ += 1

    def waiter():
        time.sleep(secs)
        app_.fireCustomEvent(DELAYED_EVENT_ID, str(delay_id))

    delayed_funcs_[delay_id] = func

    if secs > 0:
        thread = threading.Thread(target=waiter)
        thread.isDaemon = True
        thread.start()
    else:
        app_.fireCustomEvent(DELAYED_EVENT_ID, str(delay_id))

def on_command_terminate(command_id, termination_reason, func):
    global termination_handler_info_
    if not termination_handler_info_:
        termination_handler_info_ = events_manager_.add_handler(ui_.commandTerminated,
                                                                callback=command_terminated_handler)
    
    termination_funcs_.append((command_id, termination_reason, func))   

def command_terminated_handler(args):
    global termination_handler_info_

    args = adsk.core.ApplicationCommandEventArgs.cast(args)
    
    print("TERM", args.commandId, args.terminationReason, app_.activeEditObject.classType())
    
    remove_indices = []
    for i, (command_id, termination_reason, func) in enumerate(termination_funcs_):
        if (command_id == args.commandId and
            (termination_reason is None or termination_reason == args.terminationReason)):
            remove_indices.append(i)
            func()
    
    for i in reversed(remove_indices):
        del termination_funcs_[i]

    if len(termination_funcs_) == 0:
        events_manager_.remove_handler(termination_handler_info_)
        termination_handler_info_ = None

def add_builtin_dropdown(parent):
    builtin_dropdown_ = dropdown_.controls.addDropDown('Built-in Commands',
                                            '', BUILTIN_DROPDOWN_ID)
    builtin_dropdown_.resourceFolder = './resources/builtin'

    def create(cmd_def_id, text, tooltip, resource_folder, handler):
        # The cmd_def_id must never change during development of the add-in
        # as users hotkeys will map to the command definition ID.
        cmd_def = ui_.commandDefinitions.itemById(cmd_def_id)
        if cmd_def:
            cmd_def.deleteMe()
        cmd_def = ui_.commandDefinitions.addButtonDefinition(
            cmd_def_id, text, tooltip, resource_folder)
        events_manager_.add_handler(cmd_def.commandCreated,
                                    callback=handler)
        return cmd_def

    # Nested drop-down bug (2020-08-03):
    # https://forums.autodesk.com/t5/fusion-360-api-and-scripts/api-bug-cannot-click-menu-items-in-nested-dropdown/td-p/9669144
    c = create('thomasa88_anyShortcutBugInfo',
                'Fusion Bug: Menu items sometimes not clickable. But shortcuts work!',
                '',
                '',
                lambda args: None)
    c.controlDefinition.isEnabled = False
    control = builtin_dropdown_.controls.addCommand(c)
    builtin_dropdown_.controls.addSeparator()

    c = create('thomasa88_anyShortcutListLookAtSketchCommand',
                'Look At Sketch',
                'Rotates the view to look at the sketch currently being edited. ' + 
                'No action is performed if a sketch is not being edited.',
                thomasa88lib.utils.get_fusion_deploy_folder() +
                '/Neutron/UI/Commands/Resources/Camera/LookAt',
                look_at_sketch_handler)
    builtin_dropdown_.controls.addCommand(c)

    c = create('thomasa88_anyShortcutListLookAtSketchOrSelectedCommand',
                'Look At Selected or Sketch',
                'Rotates the view to look at, in priority order:\n' +
                ' 1. The selected object, if any\n' +
                ' 2. The sketch being edited',
                thomasa88lib.utils.get_fusion_deploy_folder() +
                '/Neutron/UI/Commands/Resources/Camera/LookAt',
                look_at_sketch_or_selected_handler)
    builtin_dropdown_.controls.addCommand(c)

    c = create('thomasa88_anyShortcutListActivateContainingOrComponentCommand',
                'Activate (containing) Component',
                'Activates the selected component. If no component is selected, '
                + 'the component directly containing the selected object is activated.',
                thomasa88lib.utils.get_fusion_deploy_folder() +
                '/Fusion/UI/FusionUI/Resources/Assembly/Activate',
                activate_containing_component_handler)
    builtin_dropdown_.controls.addCommand(c)

    c = create('thomasa88_anyShortcutListRollToBeginning',
                'Roll History Marker to Beginning',
                '',
                thomasa88lib.utils.get_fusion_deploy_folder() +
                '/Fusion/UI/FusionUI/Resources/Timeline/RollBegin',
                create_roll_history_handler('moveToBeginning'))
    builtin_dropdown_.controls.addCommand(c)

    c = create('thomasa88_anyShortcutListRollBack',
                'Roll History Marker Back',
                '',
                thomasa88lib.utils.get_fusion_deploy_folder() +
                '/Fusion/UI/FusionUI/Resources/Timeline/RollBack',
                create_roll_history_handler('moveToPreviousStep'))
    builtin_dropdown_.controls.addCommand(c)
    
    c = create('thomasa88_anyShortcutListRollForward',
                'Roll History Marker Forward',
                '',
                thomasa88lib.utils.get_fusion_deploy_folder() +
                '/Fusion/UI/FusionUI/Resources/Timeline/RollFwd',
                create_roll_history_handler('movetoNextStep'))
    builtin_dropdown_.controls.addCommand(c)

    c = create('thomasa88_anyShortcutListRollToEnd',
        'Roll History Marker to End',
        '',
        thomasa88lib.utils.get_fusion_deploy_folder() +
        '/Fusion/UI/FusionUI/Resources/Timeline/RollEnd',
        create_roll_history_handler('moveToEnd'))
    builtin_dropdown_.controls.addCommand(c)

    # timeline.play() just seems to skip to the end. Disabled.
    # c = create('thomasa88_anyShortcutListHistoryPlay',
    #     'Play History from Current Position',
    #     '',
    #     thomasa88lib.utils.get_fusion_deploy_folder() +
    #     '/Fusion/UI/FusionUI/Resources/Timeline/RollPlay',
    #     create_roll_history_handler('play'))
    # builtin_dropdown_.controls.addCommand(c)

    for view in ['Front', 'Back', 'Top', 'Bottom', 'Left', 'Right']:
        c = create('thomasa88_anyShortcutBuiltinView' + view,
            'View ' + view,
            '',
            '',
            create_view_orientation_handler(view))
        builtin_dropdown_.controls.addCommand(c)

def run(context):
    global app_
    global ui_
    global dropdown_
    with error_catcher_:
        app_ = adsk.core.Application.get()
        ui_ = app_.userInterface

        delayed_event = events_manager_.register_event(DELAYED_EVENT_ID)
        events_manager_.add_handler(delayed_event,
                                    callback=delayed_event_handler)

        # Add the command to the toolbar.
        panel = ui_.allToolbarPanels.itemById('SolidScriptsAddinsPanel')

        dropdown_ = panel.controls.itemById(MENU_DROPDOWN_ID)
        if dropdown_:
            dropdown_.deleteMe()
        
        dropdown_ = panel.controls.addDropDown(f'{NAME} v{manifest_["version"]}',
                                               '', MENU_DROPDOWN_ID)
        dropdown_.resourceFolder = './resources/anyshortcut'
        
        add_builtin_dropdown(dropdown_)

        dropdown_.controls.addSeparator()

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
        events_manager_.add_handler(event=enable_cmd_def_.commandCreated,
                                    callback=enable_cmd_def__created_handler)
        
        dropdown_.controls.addCommand(enable_cmd_def_)
        enable_cmd_def_.controlDefinition.isEnabled = False
        dropdown_.controls.addSeparator()

def stop(context):
    with error_catcher_:
        events_manager_.clean_up()

        panel = ui_.allToolbarPanels.itemById('SolidScriptsAddinsPanel')
        dropdown_ = panel.controls.itemById(MENU_DROPDOWN_ID)
        if dropdown_:
            dropdown_.deleteMe()

        # Need to delete children?

