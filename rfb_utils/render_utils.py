from ..rfb_logger import rfb_log
from . import prefs_utils
from .envconfig_utils import envconfig
from ..rman_constants import RFB_PLATFORM
import bpy

class RmanRenderState(object):
    k_stopped = -1
    k_exporting = 0
    k_rendering = 1
    k_denoising = 2

class RmanRenderContext(object):
    '''
    A class to represent what the state of rendering we are in.
    It should be able to answer things like:
    
    * is a render running?
    * are we rendering in the viewport?
    * are we exporting to RIB?
    
    '''
    k_stopped = 0
    
    k_render_running = 1                                     # is a render runnnig
    k_interactive_running = k_render_running << 1            # are we in interative (live) rendering 
    k_viewport_rendering = k_interactive_running << 1        # are we rendering into the blender viewport
    k_swatch_rendering = k_viewport_rendering << 1           # are we doing a swatch render (currently not used/enabled)
    k_is_xpu = k_swatch_rendering << 1                       # is this an XPU render
    k_is_live_rendering = k_is_xpu << 1                      # are we "live" rendering, this is just a flag to let us know we are using the -live flag, even in preview renders
    k_is_refining = k_is_live_rendering << 1                 # are we in the middle refining the image, or has the renderer finished/waiting for the next edit
    k_for_background = k_is_refining << 1                    # whether the blender background flag was used i.e.: we are rendering via blender batch mode
    k_is_external = k_for_background << 1                    # is this an external render, can either be blender batch or RIB renders
    k_is_bake_mode = k_is_external << 1                      # are we in baking mode
    k_is_rib_mode = k_is_bake_mode << 1                      # are we in RIB mode/writing to RIB

    # not
    k_not_render_running = 0
    k_not_interactive_running = 0b11111111101
    k_not_viewport_rendering =  0b11111111011
    k_not_swatch_rendering =    0b11111110111
    k_not_is_live_rendering =   0b11111011111
    k_not_is_refining =         0b11110111111
    k_not_for_background =      0b11101111111

    # render states
    k_render_state_exporting = 1                             # we are exporting/parsing the scene
    k_render_state_rendering = 2                             # we are rendering
    k_render_state_denoising = 3                             # we are denoising

    def __init__(self):
        self.mode = 0
        self.render_state = 0

    def get_mode(self):
        return self.mode

    def set_mode(self, mode):
        self.mode = mode

    def set_mode_append(self, mode):
        self.mode = self.mode | mode

    def set_mode_and(self, mode):
        self.mode = self.mode & mode

    def set_render_state(self, render_state):
        self.render_state = render_state    

    def set_not_live_rendering(self):
        self.mode = self.mode & RmanRenderContext.k_not_is_live_rendering

    def stop(self):
        self.set_mode(RmanRenderContext.k_stopped)
        self.set_render_state(RmanRenderContext.k_stopped)

    def set_is_refining(self):
        self.mode = self.mode | RmanRenderContext.k_is_refining

    def set_is_not_refining(self):
        self.mode = self.mode & RmanRenderContext.k_not_is_refining

    def is_render_running(self):
        return bool(self.mode & RmanRenderContext.k_render_running)

    def is_regular_rendering(self):
        return (self.is_rendering_state() and not self.is_interactive_running())

    def is_interactive_running(self):
        return bool(self.mode & RmanRenderContext.k_interactive_running)
    
    def is_viewport_rendering(self):
        return bool(self.mode & RmanRenderContext.k_viewport_rendering)    

    def is_swatch_rendering(self):
        return bool(self.mode & RmanRenderContext.k_swatch_rendering)
    
    def is_live_rendering(self):
        return bool(self.mode & RmanRenderContext.k_is_live_rendering)

    def is_refining(self):
        return bool(self.mode & RmanRenderContext.k_is_refining)
    
    def is_external(self):
        return bool(self.mode & RmanRenderContext.k_is_external)
    
    def is_bake_mode(self):
        return bool(self.mode & RmanRenderContext.k_is_bake_mode)
    
    def is_rib_mode(self):
        return bool(self.mode & RmanRenderContext.k_is_rib_mode)
    
    def is_xpu(self):
        return bool(self.mode & RmanRenderContext.k_is_xpu)

    def is_exporting_state(self):
        return self.render_state == RmanRenderContext.k_render_state_exporting

    def is_rendering_state(self):
        return self.render_state == RmanRenderContext.k_render_state_rendering
    
def get_render_variant(bl_scene):
    if not bl_scene.renderman.has_xpu_license and bl_scene.renderman.renderVariant != 'ris':
        rfb_log().warning("Your RenderMan license does not include XPU. Reverting to RIS.")
        return 'ris'

    if RFB_PLATFORM == "macOS" and bl_scene.renderman.renderVariant != 'ris':
        rfb_log().warning("XPU is not implemented on macOS: using RIS...")
        return 'ris'

    return bl_scene.renderman.renderVariant    

def set_render_variant_config(bl_scene, config, render_config):
    variant = get_render_variant(bl_scene)
    if variant.startswith('xpu'):
        variant = 'xpu'
    config.SetString('rendervariant', variant)

    if variant == 'xpu':

        xpu_mode_env = envconfig().getenv('RFB_XPU_MODE', '').lower()

        if bpy.app.background and xpu_mode_env in ['xpu', 'xpucpu', 'xpugpu']:
            # override the prefs value
            if xpu_mode_env in ['xpu', 'xpucpu']:
                render_config.SetInteger('xpu:cpuconfig', 1)
            
            if xpu_mode_env in ['xpu', 'xpugpu']:
                import rman
                
                count = rman.pxrcore.GetGpgpuCount(rman.pxrcore.k_cuda)
                gpus = list()
                for i in range(count):
                    desc = rman.pxrcore.GpgpuDescriptor()
                    rman.pxrcore.GetGpgpuDescriptor(rman.pxrcore.k_cuda, i, desc)      
                    gpus.append(i)                          
                if gpus:
                    render_config.SetIntegerArray('xpu:gpuconfig', gpus, len(gpus))     
        else:   
            xpu_gpu_devices = prefs_utils.get_pref('rman_xpu_gpu_devices')
            gpus = list()
            for device in xpu_gpu_devices:
                if device.use:
                    gpus.append(device.id)
            if gpus:
                render_config.SetIntegerArray('xpu:gpuconfig', gpus, len(gpus))    

            # For now, there is only one CPU
            xpu_cpu_devices = prefs_utils.get_pref('rman_xpu_cpu_devices')
            if len(xpu_cpu_devices) > 0:
                device = xpu_cpu_devices[0]
                render_config.SetInteger('xpu:cpuconfig', int(device.use))

                if not gpus and not device.use:
                    # Nothing was selected, we should at least use the cpu.
                    print("No devices were selected for XPU. Defaulting to CPU.")
                    render_config.SetInteger('xpu:cpuconfig', 1)
            else:                
                render_config.SetInteger('xpu:cpuconfig', 1) 
        '''
        ## OLD: single GPU device support code path
        xpu_gpu_device = int(prefs_utils.get_pref('rman_xpu_gpu_selection'))
        if xpu_gpu_device > -1:
            render_config.SetIntegerArray('xpu:gpuconfig', [xpu_gpu_device], 1)

        # For now, there is only one CPU
        xpu_cpu_devices = prefs_utils.get_pref('rman_xpu_cpu_devices')
        if len(xpu_cpu_devices) > 0:
            device = xpu_cpu_devices[0]
            render_config.SetInteger('xpu:cpuconfig', int(device.use))    

            if xpu_gpu_device == -1 and not device.use:
                # Nothing was selected, we should at least use the cpu.
                print("No devices were selected for XPU. Defaulting to CPU.")
                render_config.SetInteger('xpu:cpuconfig', 1)                         
        else:
            render_config.SetInteger('xpu:cpuconfig', 1)         
        '''

def set_render_variant_spool(bl_scene, args, is_tractor=False):
    variant = get_render_variant(bl_scene)
    if variant.startswith('xpu'):
        variant = 'xpu'
    args.append('-variant')
    args.append(variant)

    if variant == 'xpu':
        device_list = list()
        if not is_tractor:
            
            xpu_gpu_devices = prefs_utils.get_pref('rman_xpu_gpu_devices')
            for device in xpu_gpu_devices:
                if device.use:
                    device_list.append('gpu%d' % device.id)

            xpu_cpu_devices = prefs_utils.get_pref('rman_xpu_cpu_devices')
            if len(xpu_cpu_devices) > 0:
                device = xpu_cpu_devices[0]
                if device.use or not device_list:
                    device_list.append('cpu')
            else:
                device_list.append('cpu')
                            
            '''
            ## OLD: single GPU device support code path 
            xpu_gpu_device = int(prefs_utils.get_pref('rman_xpu_gpu_selection'))
            if xpu_gpu_device > -1:
                device_list.append('gpu%d' % xpu_gpu_device)

            xpu_cpu_devices = prefs_utils.get_pref('rman_xpu_cpu_devices')
            if len(xpu_cpu_devices) > 0:
                device = xpu_cpu_devices[0]

                if device.use or xpu_gpu_device < 0:
                    device_list.append('cpu')            
            else:
                device_list.append('cpu')     
            '''     

        else:
            # Don't add the gpu list if we are spooling to Tractor
            # There is no way for us to know what is available on the blade,
            # so just ask for CPU for now.
            device_list.append('cpu')

        if device_list:
            device_list = ','.join(device_list)
            args.append('-xpudevices:%s' % device_list)  

def refresh_viewport(context):
    '''
    Stop the current viewport and then restart it again
    '''

    import time 
    from ..rman_render import RmanRender

    scene = context.scene
    rm = scene.renderman
    if not rm.is_rman_running or not rm.is_rman_interactive_running:
        return
    
    rr = RmanRender.get_rman_render()
    render_to_it = rr.rman_scene.ipr_render_into == 'it'
    
    if render_to_it:            
        rr.stop_render(stop_draw_thread=False)
        time.sleep(2.0) # add a little bit of a delay before we start IPR again    
        depsgraph = context.evaluated_depsgraph_get()
        rr.start_interactive_render(context, depsgraph)        
    else:    
        # first, look for the viewport that's rendering and stop it
        viewport = None
        for window in context.window_manager.windows:
            for area in window.screen.areas:
                if area.type == 'VIEW_3D':
                    for space in area.spaces:
                        if space.type == 'VIEW_3D':
                            if space.shading.type == 'RENDERED':    
                                space.shading.type = 'SOLID'  
                                viewport = space

        if viewport is None:
            return
        rr.stop_render(stop_draw_thread=True)
        time.sleep(2.0) # add a little bit of a delay before we start IPR again
        if viewport.shading.type != 'RENDERED':        
            rr = RmanRender.get_rman_render()
            viewport.shading.type = 'RENDERED'                