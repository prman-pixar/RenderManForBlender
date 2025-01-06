from ..rfb_logger import rfb_log

import os
import json
import bpy
import rman
import threading
import time
import getpass

from collections import OrderedDict
import rman_utils.stats_config.core as stcore
from ..rfb_utils import prefs_utils
from ..rfb_logger import rfb_log
from ..rfb_utils.scene_utils import RmanRenderContext

__oneK2__ = 1024.0*1024.0
__RFB_STATS_MANAGER__ = None

__LIVE_METRICS__ = [
    ["/system.processTime", "CPU%"],
    ["/system.processMemory", "Memory"],
    ["/rman/renderer@isRendering", None],
    ["/rman/renderer@progress", None],
    ['/rman@iterationComplete', None],
    ["/rman.timeToFirstRaytrace", "First Ray"],
    ["/rman.timeToFirstPixel", "First Pixel"],
    ["/rman.timeToFirstIteration", "First Iteration"],    
    ["/rman/raytracing.numRays", "Rays/Sec"],    
    [None, "Total Rays"],
    ['/rman/texturing/sampling:time.total', 'Texturing Time'],
    ['/rman/shading/hit/bxdf:time.total', 'Shading Time'],
    ['/rman/raytracing/intersection/allhits:time.total', 'Raytracing Time'],
    ['/rman/raytracing/camera.numRays', "Camera Rays"],
    ['/rman/raytracing/transmission.numRays', "Transmission Rays"],
    ['/rman/raytracing/light.numRays', "Light Rays"],
    ['/rman/raytracing/indirect.numRays', "Indirect Rays"],
    ['/rman/raytracing/photon.numRays', "Photon Rays"]
]

__TIMER_STATS__ = [
    '/rman/shading/hit/bxdf:time.total',
    "/rman.timeToFirstRaytrace",
    "/rman.timeToFirstPixel", 
    "/rman.timeToFirstIteration",
    '/rman/texturing/sampling:time.total',
    '/rman/shading/hit/bxdf:time.total',    
    '/rman/raytracing/intersection/allhits:time.total',
]

__BASIC_STATS__ = [
    "CPU%",
    "Memory",
    "Rays/Sec",
    "Total Rays"
]

__MODERATE_STATS__ = [
    "CPU%",
    "Memory",
    "Rays/Sec",
    "Total Rays",
    "Shading Time",
    "Texturing Time",
    "Raytracing Time",
    "Camera Rays",    
]

__MOST_STATS__ = [
    "CPU%",
    "Memory",
    "Rays/Sec",
    "Total Rays",
    "Shading Time",
    "Texturing Time",
    "Raytracing Time",
    "Camera Rays",
    "Transmission Rays",
    "Light Rays",
    "Indirect Rays",
    "Photon Rays"    
]

__ALL_STATS__ = [
    "CPU%",
    "Memory",
    "First Ray",
    "First Iteration",
    "First Iteration",
    "Rays/Sec",
    "Total Rays",
    "Shading Time",
    "Texturing Time",
    "Raytracing Time", 
    "Camera Rays",
    "Transmission Rays",
    "Light Rays",
    "Indirect Rays",
    "Photon Rays"        
]   
class RfBBaseMetric(object):

    def __init__(self, key, label):
        self.key = key
        self.label = label
class RfBStatsManager(object):

    def __init__(self, rman_render):
        global __RFB_STATS_MANAGER__
        global __LIVE_METRICS__

        self.mgr = None
        self.rman_render = rman_render
        self.create_stats_manager()        
        self.render_live_stats = OrderedDict()
        self.render_stats_names = OrderedDict()
        self._prevTotalRays = 0
        self._progress = 0
        self._prevTotalRaysValid = True
        self._isRendering = False

        for name,label in __LIVE_METRICS__:
            if name:
                self.render_stats_names[name] = label
            if label:
                self.render_live_stats[label] = '--'                

        self.export_stat_label = ''
        self.export_stat_progress = 0.0

        self._integrator = 'PxrPathTracer'
        self._maxSamples = 0
        self._iterations = 0
        self._decidither = 0
        self._res_mult = 0.0
        self.web_socket_enabled = False
        self.boot_strap_thread = None
        self.boot_strap_thread_kill = False   
        self.stats_to_draw = list()     

        # roz objects
        self.rman_stats_session_name = "RfB Stats Session"
        self.rman_stats_session = None
        self.rman_stats_session_config = None        

        self.init_stats_session()
        __RFB_STATS_MANAGER__ = self

    def __del__(self):
        if self.boot_strap_thread.is_alive():
            self.boot_strap_thread_kill = True
            self.boot_strap_thread.join()

    @classmethod
    def get_stats_manager(self):
        global __RFB_STATS_MANAGER__
        return __RFB_STATS_MANAGER__        

    def reset(self):
        for label in self.render_live_stats.keys():
            self.render_live_stats[label] = '--'
        self._prevTotalRays = 0
        self._progress = 0
        self._prevTotalRaysValid = True      
        self.export_stat_label = ''
        self.export_stat_progress = 0.0
        self._isRendering = True              

    def create_stats_manager(self): 
        if self.mgr:
            return

        try:
            self.mgr = stcore.StatsManager(                          
                        # sync live stats server ID betw UI (client) & plugin (server)
                        host_assign_server_id_func=self.assign_server_id_func)
            self.is_valid = self.mgr.is_valid
        except Exception as e:
            rfb_log().error(str(e))
            self.mgr = None
            self.is_valid = False          

    def init_stats_session(self):   

        self.rman_stats_session_config = rman.Stats.SessionConfig(self.rman_stats_session_name)

        # look for a custom stats.ini file
        rman_stats_config_path = os.environ.get('RMAN_STATS_CONFIG_PATH', None)
        if rman_stats_config_path:
            if os.path.exists(os.path.join(rman_stats_config_path, 'stats.ini')):
                self.rman_stats_session_config.LoadConfigFile(rman_stats_config_path, 'stats.ini')

        # add listener plugin path
        listenerPath = os.path.join(os.environ.get("RMANTREE"), "lib/plugins/listeners")
        rman.Stats.SetListenerPluginSearchPath(listenerPath)
                          
        # do this once at startup
        self.web_socket_server_id = 'rfb_' + getpass.getuser() + '_' + str(os.getpid())
        self.rman_stats_session_config.SetServerId(self.web_socket_server_id)

        # initialize session config with prefs, then add session
        self.update_session_config()     

    def stats_add_session(self):
        self.rman_stats_session = rman.Stats.AddSession(self.rman_stats_session_config)  

    def stats_remove_session(self):
        rman.Stats.RemoveSession(self.rman_stats_session)  

    def update_session_config(self, force_enabled=False):

        self.web_socket_enabled = True # we are always enabled
        self.web_socket_port = prefs_utils.get_pref('rman_roz_webSocketServer_Port', default=0)

        if force_enabled:
            self.web_socket_enabled = True

        config_dict = dict()
        config_dict["logLevel"] = int(prefs_utils.get_pref('rman_roz_logLevel', default='3'))
        config_dict["webSocketPort"] = self.web_socket_port
        config_dict["liveStatsEnabled"] = self.web_socket_enabled
        config_dict["processQueryInterval"] = 100   # 10Hz updates

        config_str = json.dumps(config_dict)
        self.rman_stats_session_config.Update(config_str)
        if self.rman_stats_session:
            self.rman_stats_session.Update(self.rman_stats_session_config)   

        # update stats manager config for connecting client to server
        self.mgr.config["webSocketPort"] = self.web_socket_port
        self.mgr.serverId = self.web_socket_server_id

        # update what stats to draw
        print_level = int(prefs_utils.get_pref('rman_roz_stats_print_level', default='1'))
        if print_level == 1:
            self.stats_to_draw = __BASIC_STATS__
        elif print_level == 2:
            self.stats_to_draw = __MODERATE_STATS__
        elif print_level == 3:
            self.stats_to_draw = __MOST_STATS__            
        elif print_level == 4:
            self.stats_to_draw = __ALL_STATS__
        else:
            self.stats_to_draw = list()        

        if self.web_socket_enabled:
            #self.attach()
            pass
        else:
            self.disconnect()

    def assign_server_id_func(self):
        """ If we have an active render get the serverId string that was used for the
            live stats server registration when the render started.
            Note: This is called by live stats UI polling method to determine current
            live stats server so it should be kept as simple as possible.

            Returns: Server ID string, or None if a render is not running or if
            the serverId is not found.
        """

        # No stats if no render
        #if not self.rman_render.rman_running:
        if not self.rman_render.rman_context.is_render_running():
            return None
        
        return self.web_socket_server_id            


    def boot_strap(self):
        while not self.mgr.clientConnected():
            time.sleep(0.01)
            if self.boot_strap_thread_kill:
                rfb_log().debug("Bootstrap thread killed")
                return
            if self.mgr.failedToConnect():
                rfb_log().debug('Failed to connect to stats server: %s' % self.mgr.connectionStatusString())
                self.mgr.connectToServer() # keep trying to connect
                continue

        if self.mgr.clientConnected():
            rfb_log().debug("Connected to stats server. Declare interest")
            for name,label in __LIVE_METRICS__:
                # Declare interest
                if name:
                    self.mgr.enableMetric(name, 100) 

    def kill_boostap_thread(self):
        # if the bootstrap thread is still running, kill it
        if self.boot_strap_thread:
            if self.boot_strap_thread.is_alive():
                self.boot_strap_thread_kill = True
                self.boot_strap_thread.join()
            self.boot_strap_thread_kill = False
            self.boot_strap_thread = False        
        
    def attach(self):

        if not self.mgr:
            return False

        if (self.mgr.clientConnected()):
            return True

        # Manager will connect based on given configuration & serverId
        self.mgr.connectToServer()

        # Check if the boostrapping thread is still running
        # Shouldn't really need this, but let's just be sure.
        self.kill_boostap_thread()

        self.boot_strap_thread = threading.Thread(target=self.boot_strap)
        self.boot_strap_thread.start()
        # wait 5 seconds
        if not self.boot_strap_thread.join(5.0):
            # boostrap thread didn't stop, abort
            self.kill_boostap_thread()
            if not self.mgr.clientConnected():  
                # if we still can't connect to the stats server, abort 
                rfb_log().debug("Giving up trying to connect to stats server: %s" % self.mgr.connectionStatusString())             
                return False
        return True

    def is_connected(self):
        return (self.web_socket_enabled and self.mgr and self.mgr.clientConnected())

    def disconnect(self):
        if self.is_connected():
            self.mgr.disconnectFromServer()

    def get_status(self):
        if self.is_connected():
            return 'Connected'
        elif self.mgr.failedToConnect():
            return 'Connection Failed'
        else:
            return 'Disconnected'

    def reset_progress(self):
        self._progress = 0

    def check_payload(self, jsonData, name):
        try:
            dat = jsonData[name]
            return dat
        except KeyError:
            # could not find the metric name in the JSON
            # try re-registering it again
            self.mgr.enableMetric(name, 100)
            return None

    def update_payloads(self):
        """ Get the latest payload data from Roz via the websocket client in the
            manager object. Data comes back as a JSON-formatted string which is
            then parsed to update the appropriate payload field widgets.
        """
        if not self.is_connected():
            self.draw_stats()
            return

        latest = self.mgr.getLatestData()

        if (latest):
            # Load JSON-formated string into JSON object
            try:
                jsonData = json.loads(latest)
            except json.decoder.JSONDecodeError:
                rfb_log().debug("Could not decode stats payload JSON.")
                jsonData = dict()
                pass

            for name, label in self.render_stats_names.items():
                dat = self.check_payload(jsonData, name)
                if not dat:
                    continue

                if name == "/system.processTime":
                    # Payload has 4 floats: user, sys, current%, avg%
                    timePayload = dat["payload"]
                    currentPerc = (float)(timePayload[2])
                    avgPerc = (float)(timePayload[3])

                    # Set consistent fixed point output in string
                    self.render_live_stats[label] = '{:,.2f}% (Avg {:,.2f}%)'.format(currentPerc, avgPerc)

                elif name == "/system.processMemory":
                    # Payload has 3 floats: max, resident, XXX
                    # Convert resident mem to MB : payload[1] / 1024*1024;
                    memPayload = dat["payload"]
                    maxresMB = ((float)(memPayload[1])) / __oneK2__
                    # Set consistent fixed point output in string
                    
                    self.render_live_stats[label] = "{:.2f} MB".format(maxresMB)
                    
                elif name == "/rman/raytracing.numRays":
                    currentTotalRays = int(dat['payload'])
                    if currentTotalRays <= self._prevTotalRays:
                        self._prevTotalRaysValid = False

                    # Synthesize into per second
                    if self._prevTotalRaysValid:                    
                        # The metric is sampled at 60Hz (1000/16-62.5)
                        diff = currentTotalRays - self._prevTotalRays
                        raysPerSecond = float(diff * 62.5)
                        if raysPerSecond > 1000000000.0:
                            self.render_live_stats[label] = "{:.3f}B".format(raysPerSecond / 1000000000.0)    
                        elif raysPerSecond > 1000000.0:
                            self.render_live_stats[label] = '{:.3f}M'.format(raysPerSecond / 1000000.0)    
                        elif raysPerSecond > 1000.0:
                            self.render_live_stats[label] = '{:.3f}K'.format(raysPerSecond / 1000.0)    
                        else:
                            self.render_live_stats[label] = '{:.3f}'.format(raysPerSecond)
                        
                    self.render_live_stats["Total Rays"] = currentTotalRays
                    self._prevTotalRaysValid = True
                    self._prevTotalRays = currentTotalRays    
                elif name == "/rman/renderer@isRendering":
                    is_rendering = dat['payload']
                    self._isRendering = is_rendering                    
                elif name == "/rman@iterationComplete":
                    itr = dat['payload'][0]
                    self._iterations = itr  
                    self.render_live_stats[label] = '%d / %d' % (itr, self._maxSamples)
                elif name == "/rman/renderer@progress":
                    progressVal = int(float(dat['payload']))
                    self._progress = progressVal                      
                elif name in __TIMER_STATS__:
                    fval = float(dat['payload'])
                    if fval >= 60.0:
                        txt = '%d min %.04f sec' % divmod(fval, 60.0)
                    else:
                        txt = '%.04f sec' % fval                                                
                    self.render_live_stats[label] = txt
                elif name in ['/rman/raytracing/camera.numRays',
                            '/rman/raytracing/transmission.numRays', 
                            '/rman/raytracing/photon.numRays',
                            '/rman/raytracing/light.numRays', 
                            '/rman/raytracing/indirect.numRays']:    
                    rays = int(dat['payload'])
                    pct = 0
                    if self._prevTotalRays > 0:
                        pct = int((rays / self._prevTotalRays) * 100)
                    self.render_live_stats[label] = '%d (%d%%)' % (rays, pct)            
                else:    
                    self.render_live_stats[label] = str(dat['payload'])

        self.draw_stats()

    def set_export_stats(self, label, progress):
        self.export_stat_label = label
        self.export_stat_progress = progress

    def draw_stats(self):
        if self.rman_render.rman_context.is_exporting_state():
            self.draw_export_stats()
        else:
            self.draw_render_stats()        

    def draw_message(self, msg):
        #if self.rman_render.rman_interactive_running:
        if self.rman_render.rman_context.is_interactive_running():
            pass
        else:
            message = ''
            if self.is_connected():                  
                message = msg                            
            else:
                message = '(no stats connection) '          

            try:
                self.rman_render.bl_engine.update_stats(message, "%d%%" % self._progress)  
                progress = float(self._progress) / 100.0  
                self.rman_render.bl_engine.update_progress(progress)
            except ReferenceError as e:
                rfb_log().error("Error calling update stats (%s). Aborting..." % str(e))
                return           

    def draw_export_stats(self):
        if self.rman_render.bl_engine:
            try:
                #if self.rman_render.rman_interactive_running:
                if self.rman_render.rman_context.is_interactive_running():
                    progress = int(self.export_stat_progress*100)
                    self.rman_render.bl_engine.update_stats('RenderMan (Stats)', "\n%s: %d%%" % (self.export_stat_label, progress))
                else:
                    progress = int(self.export_stat_progress*100)
                    self.rman_render.bl_engine.update_stats(self.export_stat_label, "%d%%" % progress)
                    progress = self.export_stat_progress
                    self.rman_render.bl_engine.update_progress(progress)
            except:
                rfb_log().debug("Cannot update progress")        

    def draw_render_stats(self):
        #if not self.rman_render.rman_running:
        if not self.rman_render.rman_context.is_render_running():
            return
           
        #if self.rman_render.rman_interactive_running:
        if self.rman_render.rman_context.is_interactive_running():
            message = '\n%s, %d, %d%%' % (self._integrator, self._decidither, self._res_mult)
            if self.is_connected():
                for label in self.stats_to_draw:
                    data = self.render_live_stats[label]
                    message = message + '\n%s: %s' % (label, data)
                # iterations
                message = message + '\nIterations: %d / %d' % (self._iterations, self._maxSamples)
            try:
                self.rman_render.bl_engine.update_stats('RenderMan (Stats)', message)
            except ReferenceError as e:
                #rfb_log().debug("Error calling update stats (%s). Aborting..." % str(e))
                return
        else:
            message = ''
            if self.is_connected():
                for label in __BASIC_STATS__:
                    data = self.render_live_stats[label]
                    message = message + '%s: %s ' % (label, data)       
                # iterations                    
                message = message + 'Iterations: %d / %d ' % (self._iterations, self._maxSamples)                             
            else:
                message = '(no stats connection) '          

            try:
                self.rman_render.bl_engine.update_stats(message, "%d%%" % self._progress)  
                progress = float(self._progress) / 100.0  
                self.rman_render.bl_engine.update_progress(progress)
            except ReferenceError as e:
                rfb_log().error("Error calling update stats (%s). Aborting..." % str(e))
                return                

def register():
    from . import operators
    operators.register()

def unregister():
    from . import operators
    operators.unregister()