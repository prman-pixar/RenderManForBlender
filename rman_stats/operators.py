import bpy
import sys
from ..rfb_logger import rfb_log
from .. import rman_render

__STATS_WINDOW__ = None 

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
                global __STATS_WINDOW__
                __STATS_WINDOW__ = RmanStatsWrapperImpl()
                self._window = __STATS_WINDOW__
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
                        import rman_utils.stats_config.ui as rui  

                        self.resize(512, 512)
                        self.setWindowTitle('RenderMan Live Stats')
                        
                        rr = rman_render.RmanRender.get_rman_render()
                        mgr = rr.stats_mgr.mgr
                        self.ui = rui.StatsManagerUI(self, manager=mgr, show_config=False)
                        self.setLayout(self.ui.topLayout)
                        self.show() # Show window   

                    def show(self):            
                        super(RmanStatsWrapper, self).show()

                    def closeEvent(self, event):
                        event.accept()                            
                RmanStatsWrapperImpl = RmanStatsWrapper

                global __STATS_WINDOW__
                if __STATS_WINDOW__ and __STATS_WINDOW__.isVisible():
                    return {'FINISHED'}

                if sys.platform == "darwin":
                    __STATS_WINDOW__ = rfb_qt.run_with_timer(__STATS_WINDOW__, RmanStatsWrapper)
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