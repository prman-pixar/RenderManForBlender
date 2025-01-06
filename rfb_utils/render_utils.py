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
    
    '''
    k_stopped = 0
    
    k_render_running = 1
    k_interactive_running = k_render_running << 1
    k_viewport_rendering = k_interactive_running << 1
    k_swatch_rendering = k_viewport_rendering << 1
    k_is_xpu = k_swatch_rendering << 1
    k_is_live_rendering = k_is_xpu << 1
    k_is_refining = k_is_live_rendering << 1
    k_for_background = k_is_refining << 1
    k_is_external = k_for_background << 1
    k_is_bake_mode = k_is_external << 1
    k_is_rib_mode = k_is_bake_mode << 1

    # not
    k_not_render_running = 0
    k_not_interactive_running = 0b11111111101
    k_not_viewport_rendering =  0b11111111011
    k_not_swatch_rendering =    0b11111110111
    k_not_is_live_rendering =   0b11111011111
    k_not_is_refining =         0b11110111111
    k_not_for_background =      0b11101111111

    k_render_state_exporting = 1
    k_render_state_rendering = 2
    k_render_state_denoising = 3   

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

    def is_exporting_state(self):
        return self.render_state == RmanRenderContext.k_render_state_exporting

    def is_rendering_state(self):
        return self.render_state == RmanRenderContext.k_render_state_rendering