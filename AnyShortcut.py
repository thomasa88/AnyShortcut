#Author-Thomas Axelsson
#Description-Shows a menu that let's you assign shortcuts to your last run commands.

import adsk.core, adsk.fusion, adsk.cam, traceback

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

app_ = None
ui_ = None
events_manager_ = thomasa88lib.events.EventsManager(NAME)
error_catcher_ = thomasa88lib.error.ErrorCatcher()
manifest_ = thomasa88lib.manifest.read()
settings_ = thomasa88lib.settings.SettingsManager({})

def run(context):
    global app_
    global ui_
    with error_catcher_:
        app_ = adsk.core.Application.get()
        ui_ = app_.userInterface

def stop(context):
    with error_catcher_:
        pass
