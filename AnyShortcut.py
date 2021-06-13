#Author-Thomas Axelsson
#Description-Shows a menu that let's you assign shortcuts to your last run commands.

# This file is part of AnyShortcut, a Fusion 360 add-in for assigning
# shortcuts to the last run commands.
#
# Copyright (c) 2020 Thomas Axelsson
# 
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
# 
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
# 
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

import adsk.core, adsk.fusion, adsk.cam, traceback

from collections import deque
import math
import os
import operator
import time

NAME = 'AnyShortcut'
FILE_DIR = os.path.dirname(os.path.realpath(__file__))

# Import relative path to avoid namespace pollution
from .thomasa88lib import utils
from .thomasa88lib import events
from .thomasa88lib import manifest
from .thomasa88lib import error
from .thomasa88lib import timeline

# Force modules to be fresh during development
import importlib
importlib.reload(thomasa88lib.utils)
importlib.reload(thomasa88lib.events)
importlib.reload(thomasa88lib.manifest)
importlib.reload(thomasa88lib.error)
importlib.reload(thomasa88lib.timeline)

ENABLE_CMD_DEF_ID = 'thomasa88_anyShortcutList'
PANEL_ID = 'thomasa88_anyShortcutPanel'
MAIN_DROPDOWN_ID = 'thomasa88_anyShortcutMainDropdown'
TRACKING_DROPDOWN_ID = 'thomasa88_anyShortcutDropdown'
BUILTIN_DROPDOWN_ID = 'thomasa88_anyShortcutPremadeDropdown'

app_ = None
ui_ = None
error_catcher_ = thomasa88lib.error.ErrorCatcher()
events_manager_ = thomasa88lib.events.EventsManager(error_catcher_)
manifest_ = thomasa88lib.manifest.read()
command_starting_handler_info_ = None

panel_ = None
tracking_dropdown_ = None
builtin_dropdown_ = None
enable_cmd_def_ = None
HISTORY_LENGTH = 10
cmd_def_history_ = deque()
# Keeping info in a separate container, as the search is much faster
# if we can do cmd_def in cmd_def_history, not making the GUI sluggish.
cmd_controls_ = deque()
MAX_TRACK = 10
track_count_ = 0
tracking_ = False

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

        cmd_control = tracking_dropdown_.controls.addCommand(cmd_def)
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
        text = f'Stop recording (Auto-stop after {MAX_TRACK - track_count_} more commands)'
        enable_cmd_def_.resourceFolder = './resources/stop'
    else:
        text = f'Start recording (Auto-stop after {MAX_TRACK} unique commands)'
        enable_cmd_def_.resourceFolder = './resources/record'
    enable_cmd_def_.controlDefinition.name = text

def look_at_sketch_handler(args: adsk.core.CommandCreatedEventArgs):
    # Look At is usually not added to the history - skip execution.
    # Avoid getting listed as a repeatable command.
    args.command.isRepeatable = False
    edit_object = app_.activeEditObject
    if edit_object.classType() == 'adsk::fusion::Sketch':
        # Doing this ourselves instead of calling Look At, to speed it up
        # and avoid changing the active selection
        # "Look At" for a sketch "flattens" the view and centers on the origin
        view_normal_to_sketch(edit_object, center_on_origin=True)

def look_at_sketch_or_selected_handler(args: adsk.core.CommandCreatedEventArgs):
    # Look At is usually not added to the history - skip execution handler.
    # Avoid getting listed as a repeatable command.
    args.command.isRepeatable = False
    if ui_.activeSelections.count == 0:
        edit_object = app_.activeEditObject
        if edit_object.classType() == 'adsk::fusion::Sketch':
            look_at_sketch_handler(args)
    else:
        ui_.commandDefinitions.itemById('LookAtCommand').execute()

def view_normal_to_sketch_handler(args: adsk.core.CommandCreatedEventArgs):
    # View commands are usually not added to the history - skip execution handler.
    # Avoid getting listed as a repeatable command.
    args.command.isRepeatable = False
    edit_object = app_.activeEditObject
    if edit_object.classType() == 'adsk::fusion::Sketch':
        view_normal_to_sketch(edit_object)

def view_normal_to_selected_or_sketch_handler(args: adsk.core.CommandCreatedEventArgs):
    # View commands are usually not added to the history - skip execution handler.
    # Avoid getting listed as a repeatable command.
    args.command.isRepeatable = False
    if ui_.activeSelections.count == 0:
        edit_object = app_.activeEditObject
        if edit_object.classType() == 'adsk::fusion::Sketch':
            view_normal_to_sketch_handler(args)
    else:
        view_normal_to_object(ui_.activeSelections[0].entity)
        #ui_.commandDefinitions.itemById('LookAtCommand').execute()

from ctypes import windll, Structure, c_long, byref

class POINT(Structure):
    _fields_ = [("x", c_long), ("y", c_long)]

def win32_mouse_pos():
    win_point = POINT()
    windll.user32.GetCursorPos(byref(win_point))
    #return (pt.x, pt.y)
    return adsk.core.Point2D.create(win_point.x, win_point.y)

def view_normal_to_sketch(sketch, center_on_origin=False, ninety_degree_steps=False):
    #                                                                                               
    #  Rotate the camera to look at the selected sketch. The distances (eye, plane_point) and      
    #  (target, plane_point) are kept, to not zoom in/out. The camera up direction is set to       
    #  the closest sketch Y or X/Y direction.                                                      
    #                                                                                           
    #                                                                      new_target O            
    #                                                                                 |            
    #                               target  O                                         |            
    #                                      /                                          |            
    #                                     /                                           |            
    #                                    /                                            |            
    #   +-------------------------------/-----+            +--------------------------|----------+ 
    #   |                              /      |            |                          |          | 
    #   |                             /       |            |                          |          | 
    #   |                            /        |            |                          |          | 
    #   |                           /         |            |                          |          | 
    #   |                          /          |            |                          |          | 
    #   |            plane_point  X           |            |            plane_point   X          | 
    #   |                        /            |            |                          |          | 
    #   |       up  ^           /             |            |                          |          | 
    #   |            \         /              |            |                          |          | 
    #   |             \       /               |            |                  new_up  ^          | 
    #   +--------------\-----/----------------+            +--------------------------|----------+ 
    #                   \   /                                                         |            
    #                    \ /                                                          |            
    #                eye  O                                                           |            
    #                                                                                 |            
    #                                                                        new_eye  O            
    #

    # Even though center_on_origin=False it sometimes seems like the object skips
    # The problem is that we rotate the camera about the sketch plane, while a user might expect the
    # camera to rotate about the center (center of gravity?) of the seen object.

    # Make sure we have unit vectors
    sketch_x = sketch.xDirection
    sketch_x.normalize()
    sketch_y = sketch.yDirection
    sketch_y.normalize()

    camera = app_.activeViewport.camera

    # normal will be a unit vector since x and y are perpendicular
    sketch_normal_vector = sketch_x.crossProduct(sketch_y)

    # Vector target->eye
    target_eye_vector = camera.target.vectorTo(camera.eye)

    target_eye_line = adsk.core.InfiniteLine3D.create(camera.target, target_eye_vector)
    sketch_plane = adsk.core.Plane.create(sketch.origin, sketch_normal_vector)

    plane_point = sketch_plane.intersectWithLine(target_eye_line)
    if plane_point is None:
        # Don't seem to hit this even when using the view cube to view perpendiculary to the
        # plane, so just skip if this happens.
        return

    # Determine if the eye vector is looking mostly along or opposite the sketch normal
    eye_sign = math.copysign(1, target_eye_vector.dotProduct(sketch_normal_vector))

    center_point = sketch.origin.copy() if center_on_origin else plane_point.copy()

    # Experiment: Rotate about the mouse    
    # mouse_2d = app_.activeViewport.screenToView(win32_mouse_pos())
    # mouse_3d = app_.activeViewport.viewToModelSpace(mouse_2d)
    # eye_target_vector = camera.eye.vectorTo(camera.target)
    # mouse_line = adsk.core.InfiniteLine3D.create(mouse_3d, eye_target_vector)
    # mouse_3d = sketch_plane.intersectWithLine(mouse_line)
    # center_point = mouse_3d

    new_eye_vector = sketch_normal_vector.copy()
    new_eye_vector.scaleBy(camera.eye.distanceTo(plane_point) * eye_sign)
    new_eye = center_point.copy()
    new_eye.translateBy(new_eye_vector)

    new_target_vector = sketch_normal_vector.copy()
    new_target_vector.scaleBy(camera.target.distanceTo(plane_point) * -eye_sign)
    new_target = center_point.copy()
    new_target.translateBy(new_target_vector)

    # Is camera up vector closest to +X, -X, +Y or -Y direction?
    # angleTo() only gives values in [0, pi], but we need the sign
    camera_up = camera.upVector
    camera_up.normalize()
    # Since we have perpendicular unit vectors, could we just do a check for e.g. dot product > value?
    x_closeness = camera_up.dotProduct(sketch_x)
    y_closeness = camera_up.dotProduct(sketch_y)
    if ninety_degree_steps and abs(x_closeness) > abs(y_closeness):
        closest_dir = sketch_x
        closest_sign = x_closeness
    else:
        closest_dir = sketch_y
        closest_sign = y_closeness
    
    new_up = closest_dir
    new_up.scaleBy(math.copysign(1, closest_sign))

    #print(f"OLD target: {point_str(camera.target)}, eye: {point_str(camera.eye)}, up: {point_str(camera.upVector)}")
    #print(f"NEW target: {point_str(new_target)}, eye: {point_str(new_eye)}, up: {point_str(new_up)}")

    camera.target = new_target
    camera.eye = new_eye
    camera.upVector = new_up

    # Don't animate the camera change
    camera.isSmoothTransition = False

    app_.activeViewport.camera = camera

    # Needed?
    app_.activeViewport.refresh()

def point_str(point):
    return '(' + ', '.join(['{: 6.2f}'.format(c) for c in point.asArray()]) + ')'

def view_normal_to_object(entity):
    #### Change to View Normal on objects too!
    # Possible objects: BRepFace, Profile (for sketch), 
    # Test a cylindrical face. Look At puts the cylinder straight and looks at the cylindrical face.
    # Look At also centers the view on the face. Should we do that? No? The user can use Look At in that case.
    # brepface: .centroid, .pointOnFace, .geometry?, .evaluator?, .vertices?
    # .geometry is a Plane for a flat face - what about a cylindrical face? sphere? -> We get Sphere and Cylinder x)
    # .. NurbsSurface for coil (also for a cut done with a coil) and curving loft, 
    #### What about a wavy face (e.g. boundary face) or a cut cylinder?
    # profile: .plane (normal, origin, uDirection, vDirection)
    # evaluator has getNormalAtPoint(), but we have no center to use? no boundingbox for nurbssurface?
    #---- can we use any of the U/V properties?
    if isinstance(entity, adsk.fusion.Profile):
        # Sketch profile
        profile: adsk.fusion.Profile = entity
    elif isinstance(entity, adsk.fusion.BRepFace):
        face: adsk.fusion.BRepFace = entity
        # Surface (face.geometry) classes:
        # Cone, Cylinder, EllipticalCone, EllipticalCylinder, NurbsSurface, Plane, Sphere, Torus
        if isinstance(face.geometry, adsk.core.Plane):
            plane: adsk.core.Plane = face.geometry
            normal = plane.normal
            # also: point where eye-target and plane intersects. Get that here or in later function?
        #elif isinstance(face.geometry, adsk.core.)
        else:
            ui_.messageBox('Cannot handle this geometry: {type(entity)}.\n\nPlease report to the developer.', 'View Normal')
    else:
        ui_.messageBox('Cannot handle this face: {type(entity)}.\n\nPlease report to the developer.', 'View Normal')

def activate_containing_component_handler(args: adsk.core.CommandCreatedEventArgs):
    args.command.isRepeatable = False
    if ui_.activeSelections.count == 1:
        selected = ui_.activeSelections[0].entity
        if selected.classType() not in ['adsk::fusion::Component', 'adsk::fusion::Occurrence']:
            # Component not selected. Select the component.
            ui_.activeSelections.clear()
            if selected.assemblyContext is None:
                # Root component
                ui_.activeSelections.add(app_.activeProduct.rootComponent)
            else:
                ui_.activeSelections.add(selected.assemblyContext)
        ui_.commandDefinitions.itemById('FusionActivateLocalCompCmd').execute()
        ui_.commandDefinitions.itemById('FindInBrowser').execute()

def repeat_command_handler(args: adsk.core.CommandCreatedEventArgs):
    # Avoid getting picked up and repeated into eternity
    args.command.isRepeatable = False
    args.command.isExecutedWhenPreEmpted = False
    ui_.commandDefinitions.itemById('RepeatCommand').execute()

def create_roll_history_handler(move_function_name):
    # Cannot use select + the native FusionRollCommand, due to this bug (2020-08-02):
    # https://forums.autodesk.com/t5/fusion-360-api-and-scripts/cannot-select-object-in-component-using-activeselections/m-p/9653216

    def execute_handler(args: adsk.core.CommandEventArgs):
        timeline_status, timeline = thomasa88lib.timeline.get_timeline()
        if timeline_status != thomasa88lib.timeline.TIMELINE_STATUS_OK:
            args.executeFailed = True
            args.executeFailedMessage = 'Failed to get the timeline'
            return
        move_function = getattr(timeline, move_function_name)
        move_function()

    def created_handler(args: adsk.core.CommandCreatedEventArgs):
        args.command.isRepeatable = False
        events_manager_.add_handler(args.command.execute,
                                    callback=execute_handler)

    return created_handler

def create_view_orientation_handler(view_orientation_name):
    def created_handler(args: adsk.core.CommandCreatedEventArgs):
        # We don't want undo history, so no execute handler
        
        # Avoid getting listed as a repeatable command.
        args.command.isRepeatable = False

        camera_copy = app_.activeViewport.camera
        camera_copy.cameraType = adsk.core.CameraTypes.OrthographicCameraType #?

        # Using viewOrientation always forces smooth animation?
        camera_copy.isSmoothTransition = False
        camera_copy.viewOrientation = getattr(adsk.core.ViewOrientations,
                                              view_orientation_name + 'ViewOrientation')
        app_.activeViewport.camera = camera_copy

        # Must set the up vector after the orient rotation has been performed,
        # with a delay, for it to work correctly.

        # def rotate_up():
        #     camera_copy = app_.activeViewport.camera
        #     # defaultModelingOrientation does not give us the orientation for
        #     # the current document.
        #     # ---> We don't know which direction is up!
        #     # Create duplicate sets of commands?
        #     modeling_orientation = app_.preferences.generalPreferences.defaultModelingOrientation

        #     # Z-Up orientation:
        #     if view_orientation_name in ['Top', 'Bottom']:
        #         up = adsk.core.Vector3D.create(0.0, 1.0, 0.0)
        #     else:
        #         up = adsk.core.Vector3D.create(0.0, 0.0, 1.0)
            
        #     if camera_copy.upVector.angleTo(up) > (math.pi / 4.0):
        #         camera_copy.upVector = up
        #         app_.activeViewport.camera = camera_copy
        #     #app_.activeViewport.refresh() Use this?
        
        # #adsk.doEvents()
        # #rotate_up()
        # events_manager_.delay(rotate_up, secs=1)
        # #app_.activeViewport.refresh()

    return created_handler

def on_command_terminate(command_id, termination_reason, func):
    global termination_handler_info_
    if not termination_handler_info_:
        termination_handler_info_ = events_manager_.add_handler(ui_.commandTerminated,
                                                                callback=command_terminated_handler)
    
    termination_funcs_.append((command_id, termination_reason, func))   

def command_terminated_handler(args):
    global termination_handler_info_

    args = adsk.core.ApplicationCommandEventArgs.cast(args)
    
    #print("TERM", args.commandId, args.terminationReason, app_.activeEditObject.classType())
    
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
    global builtin_dropdown_
    builtin_dropdown_ = parent.controls.itemById(BUILTIN_DROPDOWN_ID)
    if builtin_dropdown_:
            builtin_dropdown_.deleteMe()
    builtin_dropdown_ = parent.controls.addDropDown(f'Built-in Commands',
                                                    './resources/builtin',
                                                    BUILTIN_DROPDOWN_ID)

    def create(cmd_def_id, text, tooltip, resource_folder, handler):
        # The cmd_def_id must never change during development of the add-in
        # as users hotkeys will map to the command definition ID.

        cmd_def = ui_.commandDefinitions.itemById(cmd_def_id)
        if cmd_def:
            cmd_def.deleteMe()
        cmd_def = ui_.commandDefinitions.addButtonDefinition(
            cmd_def_id, text, tooltip, resource_folder)

        if not resource_folder:
            # Must have icon for the assign shortcut menu to appear
            cmd_def.resourceFolder = './resources/noicon'
        
        events_manager_.add_handler(cmd_def.commandCreated,
                                    callback=handler)
        return cmd_def

    c = create('thomasa88_anyShortcutListLookAtSketchCommand',
                'Look At Sketch',
                'Rotates the view to look at the sketch currently being edited. ' +
                'The view is centered on the origin.\n\n' +
                'No action is performed if a sketch is not being edited.',
                './resources/lookatsketch',
                look_at_sketch_handler)
    builtin_dropdown_.controls.addCommand(c)

    c = create('thomasa88_anyShortcutListLookAtSketchOrSelectedCommand',
                'Look At Selected or Sketch',
                'Rotates the view to look at, in priority order:\n' +
                ' 1. The selected object, if any\n' +
                ' 2. The sketch being edited\n\n' +
                'The view is centered on the origin, if a looking at a sketch.',
                './resources/lookatselectedorsketch',
                look_at_sketch_or_selected_handler)
    builtin_dropdown_.controls.addCommand(c)

    c = create('thomasa88_anyShortcutListNormalToSketchCommand',
                'View Normal to Sketch',
                'Rotates the view to look at the sketch being edited, ' +
                'without panning.',
                './resources/lookatsketch',
                view_normal_to_sketch_handler)
    builtin_dropdown_.controls.addCommand(c)

    c = create('thomasa88_anyShortcutListLookAtSelectedOrNormalToSketchCommand',
                'View Normal to Selected or Sketch',
                'Rotates the view to look at, in priority order:\n' +
                ' 1. The selected object, if any\n' +
                ' 2. The sketch being edited\n\n' +
                'The view does not pan, if a looking at a sketch.',
                './resources/lookatselectedorsketch',
                view_normal_to_selected_or_sketch_handler)
    builtin_dropdown_.controls.addCommand(c)

    c = create('thomasa88_anyShortcutListActivateContainingOrComponentCommand',
                'Activate (containing) Component',
                'Activates the selected component. If no component is selected, '
                + 'the component directly containing the selected object is activated.',
                './resources/activate',
                activate_containing_component_handler)
    builtin_dropdown_.controls.addCommand(c)

    # For some reason, repeat captured using the tracking only works when clicking,
    # not with a keyboard shortcut.
    c = create('thomasa88_anyShortcutBuiltinRepeatCommand',
                'Repeat Last Command',
                '',
                './resources/repeat',
                repeat_command_handler)
    builtin_dropdown_.controls.addCommand(c)

    timeline_dropdown = builtin_dropdown_.controls.addDropDown('Timeline', './resources/timeline',
                                                               'thomasa88_anyShortcutBuiltinTimelineList')

    c = create('thomasa88_anyShortcutListRollToBeginning',
                'Roll History Marker to Beginning',
                '',
                './resources/timelinebeginning',
                create_roll_history_handler('moveToBeginning'))
    timeline_dropdown.controls.addCommand(c)

    c = create('thomasa88_anyShortcutListRollBack',
                'Roll History Marker Back',
                '',
                './resources/timelineback',
                create_roll_history_handler('moveToPreviousStep'))
    timeline_dropdown.controls.addCommand(c)
    
    c = create('thomasa88_anyShortcutListRollForward',
                'Roll History Marker Forward',
                '',
                './resources/timelineforward',
                create_roll_history_handler('movetoNextStep'))
    timeline_dropdown.controls.addCommand(c)

    c = create('thomasa88_anyShortcutListRollToEnd',
               'Roll History Marker to End',
               '',
               './resources/timelineend',
               create_roll_history_handler('moveToEnd'))
    timeline_dropdown.controls.addCommand(c)

    # timeline.play() just seems to skip to the end. Disabled.
    # c = create('thomasa88_anyShortcutListHistoryPlay',
    #     'Play History from Current Position',
    #     '',
    #     './resources/timelineplay',
    #     create_roll_history_handler('play'))
    # timeline_dropdown.controls.addCommand(c)

    view_dropdown = builtin_dropdown_.controls.addDropDown('View Orientation', './resources/viewfront',
                                                           'thomasa88_anyShortcutBuiltinViewList')
    for view in ['Front', 'Back', 'Top', 'Bottom', 'Left', 'Right']:
        c = create('thomasa88_anyShortcutBuiltinView' + view,
            'View ' + view,
            '',
            './resources/view' + view.lower(),
            create_view_orientation_handler(view))
        view_dropdown.controls.addCommand(c)

def run(context):
    global app_
    global ui_
    global tracking_dropdown_
    global builtin_dropdown_
    global panel_
    with error_catcher_:
        app_ = adsk.core.Application.get()
        ui_ = app_.userInterface

        # Add the command to the tab.
        tab = ui_.allToolbarTabs.itemById('ToolsTab')

        panel_ = tab.toolbarPanels.itemById(PANEL_ID)
        if panel_:
            panel_.deleteMe()
        panel_ = tab.toolbarPanels.add(PANEL_ID, f'{NAME}')
        add_builtin_dropdown(panel_)

        tracking_dropdown_ = panel_.controls.itemById(TRACKING_DROPDOWN_ID)
        if tracking_dropdown_:
            tracking_dropdown_.deleteMe()
        
        tracking_dropdown_ = panel_.controls.addDropDown(f'Command Recorder',
                                                         './resources/tracker',
                                                         TRACKING_DROPDOWN_ID)

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
        
        enable_control = tracking_dropdown_.controls.addCommand(enable_cmd_def_)
        enable_control.isPromoted = True
        enable_control.isPromotedByDefault = True
        tracking_dropdown_.controls.addSeparator()

def stop(context):
    with error_catcher_:
        events_manager_.clean_up()

        tracking_dropdown_.deleteMe()
        builtin_dropdown_.deleteMe()
        panel_.deleteMe()

        # Need to delete children?

