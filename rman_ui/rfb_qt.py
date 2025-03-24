'''
try: 
    from rman_utils.vendor.Qt import QtCore, QtWidgets 
    import functools
except ModuleNotFoundError:
    raise    
except ImportError:
    raise
'''
    
import bpy
import sys
from ..rman_constants import RFB_PLATFORM

"""
-------------------------------------------------
Code from:
https://gitlab.com/-/snippets/1881226

Code modified by ihsieh@pixar.com (Jan 5, 2021)
Original comments below.
-------------------------------------------------
Test for running a Qt app in Blender.

Warning:
    Do not use `app.exec_()`, this will block the Blender UI! And possibly also
    cause threading issues.

In this example there are 4 approaches:
    - Using a timed modal operator (this should also work in Blender 2.79). On
      Windows the `bpy.context` is almost empty and on macOS Blender and the UI
      of the app are blocked. So far this only seems to work on Linux.
    - Using a timed modal operator to keep the Qt GUI alive and communicate via
      `queue.Queue`. So far this seems to work fine on Linux and Windows (macOS
      is untested at the moment).
    - Using a 'normal' modal operator (this should also work in Blender 2.79).
      This doesn't seem to work very well. Because the modal operator is only
      triggered once, the `processEvents()` is also only called once. This
      means after showing, the UI will never be updated again without manually
      calling `processEvents()` again. For me the UI doens't even show up
      properly, because it needs more 'loops' to do this (on Linux).
    - Using `bpy.app.timers` wich was introduced in Blender 2.80. This also
      doesn't work reliably. If you try to get `bpy.context` from within the Qt
      App, it's almost empty. Seems like we run into the 'Blender threading
      issue' again.

TLDR: Use `run_timed_modal_operator_queue`. :)

isort:skip_file

"""

## CSS copied from $RMANTREE/bin/rman_utils/rman_assets/common/ui_style.py
__rmanPltF__ = {'bg': (68, 68, 68),
                'darkbg': (43, 43, 43),
                'alternatebg': (53, 53, 53),
                'lightbg': (78, 78, 78),
                'tipbg': (58, 58, 58),
                'tiptext': (192, 192, 192),
                'text': (200, 200, 200),
                'textselected': (225, 225, 225),
                'orange': (229, 154, 0),
                'blue': (118, 149, 229),
                'bluehover': (81, 95, 125),
                'handle': (93, 93, 93)}

__BASE_CSS__ = '''
    QWidget {
        background: %(bg)s;
    } 
    QPushButton {
        border-radius: 2px;
        color: %(text)s;
        background-color: #5D5D5D;
        min-height: 18px;
        margin-left: 5px;
        margin-right: 5px;
        margin-top: 1px;
        padding-left: 3px;
        padding-right: 3px;
    }
    QPushButton:hover {
        background-color: #5D5D5D;
        color: %(textselected)s;
    }    
    QPushButton:pressed {
        background-color: rgba(32, 64, 128, 255);
        color: %(textselected)s;
    }     
    QFrame {
        background-color: %(darkbg)s;
        border-width: 2px;
        border-radius: 4px;
        margin: 0px;
    }    
    QLabel {
        background: %(bg)s;
        color: %(text)s;
    }    
    QGroupBox {
        background: %(bg)s;
        color: %(text)s;
    }        
    QSplitter {
        border-style: none;
        background-color: %(bg)s;
    }
    QSplitter::handle {
        background-color: %(bg)s;
    }
    QSplitter::handle:hover {
        background-color: %(bluehover)s;
    }    
    QMenuBar {
        border-width: 0px;
        border-image: none;
        color: %(text)s;
    }
    QMenuBar::item {
        color: %(text)s;
        background-color: %(bg)s;
    }   
    QMenuBar::item::selected {
        background-color: %(bg)s;
        color: %(textselected)s;
    }
    QMenu {
        background-color: %(bg)s;
        color: %(text)s;
    }
    QMenu::item::selected {
        background-color: %(bg)s;
        color: %(textselected)s;
    }    
    QToolTip {
        background-color: %(tipbg)s;
        color: %(tiptext)s;
        border: 3px solid %(bluehover)s;
        border-radius: 3px;
        padding: 4px;
    }
    QProgressBar {
        border: 1px solid %(bg)s;
    }
    QProgressBar::chunk {
        background-color: %(blue)s;
    }    
    QLineEdit {
        background-color: %(darkbg)s;
        background-image: none;
        color: %(text)s;
    }    
    QHeaderView {
        background-color: %(darkbg)s;
        border-color: %(darkbg)s;
    }
    QHeaderView::section {
        background-color: %(darkbg)s;
        background-image: none;
        border-image: none;
        border-color:  %(darkbg)s;
        color: %(blue)s;
        font-weight: bold;
    }       
    QTreeWidget {
        margin: 0px;
        padding: 0px;
        border-width: 2px;
        border-radius: 4px;
        border-color: %(darkbg)s;
        color: %(text)s;
        background-color: %(darkbg)s;
        alternate-background-color: %(alternatebg)s;        
        min-width: 138px;
    }
    QTreeView {
        margin: 0px;
        padding: 0px;
        border-width: 2px;
        border-radius: 4px;
        border-color: %(darkbg)s;
        color: %(text)s;
        background-color: %(darkbg)s;
        alternate-background-color: %(alternatebg)s;
        min-width: 138px;
    }    
    QListWidget {
        margin: 0px;
        padding: 0px;
        border-width: 2px;
        border-radius: 4px;
        border-color: %(darkbg)s;
        color: %(text)s;
        background-color: %(darkbg)s;
        alternate-background-color: %(alternatebg)s;        
        min-width: 138px;
    }     
    QDoubleSpinBox {
        color: %(text)s;   
    }
'''

class RfbBaseQtAppTimed(bpy.types.Operator):
    """Run a Qt app inside of Blender, without blocking Blender."""

    _app = None
    _window = None
    _timer = None

    def __init__(self, *args, **kwargs):
        from rman_utils.vendor.Qt import QtWidgets
        super().__init__(*args, **kwargs)
        self._app = (QtWidgets.QApplication.instance()
                     or QtWidgets.QApplication(sys.argv))
        
        # always use the Fusion style
        self._app.setStyle("Fusion")

    def modal(self, context, event):
        """Run modal."""
        if event.type == 'TIMER':
            if self._window and not self._window.isVisible():
                self.cancel(context)
                return {'FINISHED'}

            self._app.processEvents()
        return {'PASS_THROUGH'}

    def execute(self, context):
        """Process the event loop of the Qt app."""

        # explicitly set the style sheet
        # we don't seem to be inheriting the style sheet correctly
        # from the children widgets
        sh = self._window.styleSheet()
        plt = dict(__rmanPltF__)
        for nm, rgb in plt.items():
            plt[nm] = 'rgb(%d, %d, %d)' %  (rgb[0], rgb[1], rgb[2])
        css = __BASE_CSS__ % plt
        sh += css        
        self._app.setStyleSheet(sh)    
        
        self._window.show()
        wm = context.window_manager
        # Run every 0.01 seconds
        self._timer = wm.event_timer_add(0.01, window=context.window)
        wm.modal_handler_add(self)

        return {'RUNNING_MODAL'}

    def cancel(self, context):
        """Remove event timer when stopping the operator."""
        self._window.close()
        wm = context.window_manager
        wm.event_timer_remove(self._timer)

def get_rman_qt_wrapper():
    try:
        from rman_utils.vendor.Qt import QtWidgets, QtCore
        class RmanQtWrapper(QtWidgets.QDialog):

            def __init__(self):
                super().__init__()        
                if RFB_PLATFORM == "macOS":
                    self.setWindowFlags(QtCore.Qt.WindowStaysOnTopHint)
                else:
                    self.setWindowState(self.windowState() & ~QtCore.Qt.WindowMinimized | QtCore.Qt.WindowActive)         

                bg_role = self.backgroundRole()
                plt = self.palette()
                bg_color = plt.color(bg_role)  
                bg_color.setRgb(__rmanPltF__['bg'][0], __rmanPltF__['bg'][1], __rmanPltF__['bg'][2])
                plt.setColor(bg_role, bg_color)                  
                self.setPalette(plt)               

            def closeEvent(self, event):
                event.accept()

        return RmanQtWrapper
    except ModuleNotFoundError:
        return None    
    except ImportError:
        return

def process_qt_events(app, window):
    """Run `processEvents()` on the Qt app."""
    if window and not window.isVisible():
        return None
    app.processEvents()
    window.update()
    return 0.01  # Run again after 0.001 seconds
        
def run_with_timer(window, cls):
    from rman_utils.vendor.Qt import QtWidgets
    import functools

    """Run the app with the new `bpy.app.timers` in Blender 2.80."""
    app = QtWidgets.QApplication.instance() or QtWidgets.QApplication(sys.argv)
    if not window:
        window = cls()
    window.show()
    bpy.app.timers.register(functools.partial(process_qt_events, app, window))
    return window