import bpy
import sys
from ..rfb_logger import rfb_log
from .. import rman_render
from ..rman_constants import RFB_PLATFORM

STATS_WINDOW = None 

RmanStatsWrapperImpl = None
if not bpy.app.background:
    try:
        from ..rman_ui import rfb_qt
    except:
        rfb_qt = None

    if rfb_qt:
        class LiveStatsQtAppTimed(rfb_qt.RfbBaseQtAppTimed):
            bl_idname = "wm.live_stats_qt_app_timed"
            bl_label = "Live Stats"

            def __init__(self):
                super(LiveStatsQtAppTimed, self).__init__()

            def execute(self, context):
                global RmanStatsWrapperImpl
                global STATS_WINDOW
                STATS_WINDOW = RmanStatsWrapperImpl()
                self._window = STATS_WINDOW
                return super(LiveStatsQtAppTimed, self).execute(context)
            
        class PRMAN_OT_Open_Stats(bpy.types.Operator):
            bl_idname = "renderman.rman_open_stats"
            bl_label = "Live Stats"

            def execute(self, context):
                global RmanStatsWrapperImpl
                RmanQtWrapper = rfb_qt.get_rman_qt_wrapper()    
                class RmanStatsWrapper(RmanQtWrapper):

                    def __init__(self):
                        super(RmanStatsWrapper, self).__init__()

                        # import here because we will crash Blender
                        # when we try to import it globally
                        try:
                            from stportal.ui.live.overview import LiveStatsOverviewUI
                            from stportal.core.datamanager import DataManager
                            from rman_utils.vendor.Qt import QtWidgets
                            
                            rr = rman_render.RmanRender.get_rman_render()
                                       
                            self.mgr = DataManager(                          
                                # sync live stats server ID betw UI (client) & plugin (server)
                                assign_server_id_func=rr.stats_mgr.assign_server_id_func)
                            __statsui__ = LiveStatsOverviewUI(parent=self, manager=self.mgr)
                            self.resize(950, 650)
                            self.setWindowTitle('RenderMan Live Stats')

                            self.lyt = QtWidgets.QVBoxLayout()
                            self.scroll = QtWidgets.QScrollArea()
                            self.scroll.setWidgetResizable(True)
                            self.lyt.addWidget(self.scroll)
                            self.setLayout(self.lyt)
                            self.setAcceptDrops(True)
                            # Set up manager and UI for stats configuration
                            self.ui = __statsui__
                            self.scroll.setWidget(self.ui)
                            if self.ui:
                                self.scroll.setWidget(self.ui)
                            else:
                                self.scroll.setWidget(QtWidgets.QLabel("Live Stats: Failed to initialize"))

                            self.show() # Show window   
                        except Exception as e:
                            rfb_log().warning('Live stats initialization failed: %r', e)

                    def show(self):            
                        super(RmanStatsWrapper, self).show()

                    def closeEvent(self, event):
                        event.accept()                            
                RmanStatsWrapperImpl = RmanStatsWrapper

                global STATS_WINDOW
                if STATS_WINDOW and STATS_WINDOW.isVisible():
                    return {'FINISHED'}

                if RFB_PLATFORM == "macOS":
                    STATS_WINDOW = rfb_qt.run_with_timer(STATS_WINDOW, RmanStatsWrapper)
                else:
                    bpy.ops.wm.live_stats_qt_app_timed()
                
                return {'FINISHED'}

classes = []           

if not bpy.app.background and rfb_qt:
    classes.append(PRMAN_OT_Open_Stats)
    classes.append(LiveStatsQtAppTimed)

def register():
    from ..rfb_utils import register_utils

    register_utils.rman_register_classes(classes) 
    
def unregister():
    from ..rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes) 