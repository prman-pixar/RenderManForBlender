
import os
from gpu_extras.batch import batch_for_shader
from ...rfb_utils import string_utils
from ...rfb_utils import prefs_utils
from ...rfb_utils import transform_utils
from ...rfb_logger import rfb_log
from ...rman_constants import RMAN_AREA_LIGHT_TYPES, BLENDER_41
from .barn_light_filter_draw_helper import BarnLightFilterDrawHelper
from .frustrum_draw_helper import FrustumDrawHelper
from mathutils import Vector, Matrix, Quaternion
import mathutils
import math
import ice
import bpy
import gpu

if not bpy.app.background:
    from gpu_extras.batch import batch_for_shader

_DRAW_HANDLER_ = None
_FRUSTUM_DRAW_HELPER_ = None
_BARN_LIGHT_DRAW_HELPER_ = None
_PI0_5_ = 1.570796327
_PRMAN_TEX_CACHE_ = dict()
_RMAN_TEXTURED_LIGHTS_ = ['PxrRectLight', 'PxrDomeLight', 'PxrGoboLightFilter', 'PxrCookieLightFilter']
DOME_LIGHT_UVS = list()

s_rmanLightLogo = dict()
s_rmanLightLogo['box'] = [
    (-0.5,0.5,0.0),
    (-0.5,-0.5,0.0),
    (0.5,-0.5,0.0),
    (0.5,0.5, 0.0)
]

s_rmanLightLogo['point'] = [
    (0.1739199623,0.2189011082,0.0),
    (0.2370826019,0.2241208805,0.0),
    (0.2889232079,0.180194478,0.0),
    (0.2945193948,0.1124769769,0.0),
    (0.2505929922,0.06063637093,0.0),
    (0.1828754911,0.05504018402,0.0),
    (0.1310348852,0.09896658655,0.0),
    (0.1254386983,0.1666840877,0.0)
]

s_rmanLightLogo['bouncing_r'] = [    
    (0.10014534,0.163975795,0.0),
    (0.02377454715,0.2079409584,0.0),
    (-0.0409057802,0.162414633,0.0),
    (-0.09261710117,-0.03967857045,0.0),
    (-0.1033546419,-0.3941421577,0.0),
    (-0.1714205988,-0.3935548906,0.0),
    (-0.1743695606,-0.2185861014,0.0),
    (-0.1934162612,-0.001801638764,0.0),
    (-0.2387964527,0.228222199,0.0),
    (-0.2945193948,0.388358659,0.0),
    (-0.2800665961,0.3941421577,0.0),
    (-0.1944135703,0.2262313617,0.0),
    (-0.1480375743,0.08022936015,0.0),
    (-0.09632135301,0.2812304287,0.0),
    (0.03260773708,0.3415349284,0.0),
    (0.1794274591,0.2497892755,0.0),
    (0.10014534,0.163975795,0.0)
]

s_rmanLightLogo['arrow'] = [
    (0.03316599252,-6.536167e-18,0.0294362),
    (0.03316599252,-7.856030e-17,0.3538041),
    (0.06810822842,-7.856030e-17,0.3538041),
    (0,-1.11022302e-16,0.5),
    (-0.0681082284,-7.85603e-17,0.353804),
    (-0.0331659925,-7.85603e-17,0.353804),
    (-0.0331659925,-6.53616e-18,0.029436)
]

s_rmanLightLogo['R_outside'] = [
    [0.265400, -0.291600, 0.000000],
    [0.065400, -0.291600, 0.000000],
    [0.065400, -0.125000, 0.000000],
    [0.025800, -0.125000, 0.000000],
    [0.024100, -0.125000, 0.000000],
    [-0.084800, -0.291600, 0.000000],
    [-0.305400, -0.291600, 0.000000],
    [-0.170600, -0.093300, 0.000000],
    [-0.217900, -0.062800, 0.000000],
    [-0.254000, -0.023300, 0.000000],
    [-0.276900, 0.025800, 0.000000],
    [-0.284500, 0.085000, 0.000000],
    [-0.284500, 0.086700, 0.000000],
    [-0.281200, 0.128700, 0.000000],
    [-0.271200, 0.164900, 0.000000],
    [-0.254500, 0.196600, 0.000000],
    [-0.231000, 0.224900, 0.000000],
    [-0.195200, 0.252600, 0.000000],
    [-0.149600, 0.273700, 0.000000],
    [-0.092000, 0.287100, 0.000000],
    [-0.020300, 0.291600, 0.000000],
    [0.265400, 0.291600, 0.000000],
    [0.265400, -0.291600, 0.000000]

]

s_rmanLightLogo['R_inside'] = [
    [0.065400, 0.019100, 0.000000],
    [0.065400, 0.133300, 0.000000],
    [-0.014600, 0.133300, 0.000000],
    [-0.043500, 0.129800, 0.000000],
    [-0.065700, 0.119500, 0.000000],
    [-0.079800, 0.102100, 0.000000],
    [-0.084500, 0.077400, 0.000000],
    [-0.084500, 0.075700, 0.000000],
    [-0.079800, 0.052000, 0.000000],
    [-0.065700, 0.034100, 0.000000],
    [-0.043300, 0.022800, 0.000000],
    [-0.013800, 0.019100, 0.000000],
    [0.065400, 0.019100, 0.000000]
]

s_envday = dict()
s_envday['west_rr_shape'] = [  
    [-1.9994, 0, -0.1652], [-2.0337, 0, 0.0939],
    [-2.0376, 0, 0.1154], [-2.0458, 0, 0.1159],
    [-2.046, 0, 0.0952], [-2.0688, 0, -0.2033],
    [-2.1958, 0, -0.203], [-2.1458, 0, 0.1705],
    [-2.1408, 0, 0.1874], [-2.1281, 0, 0.2],
    [-2.1116, 0, 0.2059], [-2.0941, 0, 0.2078],
    [-1.9891, 0, 0.2073], [-1.9719, 0, 0.2039],
    [-1.9573, 0, 0.1938], [-1.9483, 0, 0.1786],
    [-1.9447, 0, 0.1613], [-1.9146, 0, -0.1149],
    [-1.9049, 0, -0.1127], [-1.8721, 0, 0.1759],
    [-1.8652, 0, 0.1921], [-1.8507, 0, 0.2021],
    [-1.8339, 0, 0.2072], [-1.7112, 0, 0.207],
    [-1.6943, 0, 0.2024], [-1.6816, 0, 0.1901],
    [-1.6744, 0, 0.1742], [-1.6234, 0, -0.2037],
    [-1.751, 0, -0.2035], [-1.7748, 0, 0.1153],
    [-1.7812, 0, 0.1166], [-1.7861, 0, 0.1043],
    [-1.8188, 0, -0.1565], [-1.8218, 0, -0.1738],
    [-1.83, 0, -0.1894], [-1.8447, 0, -0.1995],
    [-1.8618, 0, -0.2034], [-1.9493, 0, -0.2037],
    [-1.967, 0, -0.2024], [-1.9824, 0, -0.1956],
    [-1.9943, 0, -0.1825]
]
s_envday['east_rr_shape'] = [              
    [1.8037, 0, 0.1094], [1.9542, 0, 0.1094],
    [1.9604, 0, 0.2004], [1.9175, 0, 0.2043],
    [1.8448, 0, 0.2069], [1.7493, 0, 0.2082],
    [1.7375, 0, 0.2079], [1.7258, 0, 0.2066],
    [1.7144, 0, 0.204], [1.7033, 0, 0.2],
    [1.6928, 0, 0.1947], [1.6831, 0, 0.188],
    [1.6743, 0, 0.1802], [1.6669, 0, 0.171],
    [1.6607, 0, 0.1611], [1.6559, 0, 0.1503],
    [1.6527, 0, 0.139], [1.6508, 0, 0.1274],
    [1.6502, 0, 0.1156], [1.6502, 0, -0.1122],
    [1.6505, 0, -0.1239], [1.6521, 0, -0.1356],
    [1.6551, 0, -0.147], [1.6597, 0, -0.1578],
    [1.6657, 0, -0.168], [1.6731, 0, -0.1771],
    [1.6816, 0, -0.1852], [1.6911, 0, -0.1922],
    [1.7014, 0, -0.1978], [1.7124, 0, -0.2021],
    [1.7238, 0, -0.205], [1.7354, 0, -0.2066],
    [1.7472, 0, -0.207], [1.8528, 0, -0.2058],
    [1.9177, 0, -0.2028], [1.9602, 0, -0.1993],
    [1.9541, 0, -0.1082], [1.8006, 0, -0.1084],
    [1.7892, 0, -0.1054], [1.7809, 0, -0.0968],
    [1.7789, 0, -0.0851], [1.7793, 0, -0.0471],
    [1.9329, 0, -0.0469], [1.933, 0, 0.0388],
    [1.7793, 0, 0.0384], [1.779, 0, 0.0895],
    [1.7825, 0, 0.1002], [1.792, 0, 0.1083]
]
s_envday['south_rr_shape'] = [
    [0.1585, 0, 1.654],   [0.1251, 0, 1.6444],
    [0.0918, 0, 1.6383],  [0.053, 0, 1.6345],
    [0.0091, 0, 1.6331],  [-0.0346, 0, 1.6347],
    [-0.0712, 0, 1.6397], [-0.1002, 0, 1.6475],
    [-0.1221, 0, 1.6587], [-0.142, 0, 1.6791],
    [-0.1537, 0, 1.7034], [-0.1579, 0, 1.7244],
    [-0.1599, 0, 1.7458], [-0.1593, 0, 1.7672],
    [-0.1566, 0, 1.7884], [-0.1499, 0, 1.8088],
    [-0.1392, 0, 1.8273], [-0.1249, 0, 1.8433],
    [-0.1079, 0, 1.8563], [-0.0894, 0, 1.8675],
    [-0.0707, 0, 1.8765], [-0.0139, 0, 1.9013],
    [0.0258, 0, 1.9185],  [0.041, 0, 1.9287],
    [0.0411, 0, 1.939],   [0.0366, 0, 1.9485],
    [0.0253, 0, 1.9525],  [-0.1485, 0, 1.95],
    [-0.1566, 0, 2.0398], [-0.1297, 0, 2.0462],
    [-0.0876, 0, 2.0538], [-0.0451, 0, 2.0585],
    [-0.0024, 0, 2.0603], [0.0403, 0, 2.0591],
    [0.0827, 0, 2.0534],  [0.1231, 0, 2.0397],
    [0.1537, 0, 2.0102],  [0.168, 0, 1.97],
    [0.1706, 0, 1.9273],  [0.1631, 0, 1.8852],
    [0.1404, 0, 1.8491],  [0.106, 0, 1.8236],
    [0.0875, 0, 1.8137],  [-0.0136, 0, 1.7711],
    [-0.0244, 0, 1.7643], [-0.0309, 0, 1.7558],
    [-0.031, 0, 1.7462],  [-0.0261, 0, 1.7393],
    [-0.0124, 0, 1.7353], [0.1505, 0, 1.7366]
]
s_envday['north_rr_shape'] = [ 
    [-0.144, 0, -2.034],   [-0.1584, 0, -2.0323],
    [-0.1719, 0, -2.0256], [-0.1804, 0, -2.0136],
    [-0.1848, 0, -1.9996], [-0.185, 0, -1.9849],
    [-0.185, 0, -1.6235],  [-0.0661, 0, -1.6236],
    [-0.0663, 0, -1.8158], [-0.0672, 0, -1.8303],
    [-0.0702, 0, -1.8594], [-0.0721, 0, -1.8739],
    [-0.0654, 0, -1.8569], [-0.048, 0, -1.8169],
    [-0.0415, 0, -1.8038], [0.0554, 0, -1.65],
    [0.0641, 0, -1.638],   [0.0747, 0, -1.6286],
    [0.0869, 0, -1.6244],  [0.0978, 0, -1.6235],
    [0.1541, 0, -1.6238],  [0.1677, 0, -1.6263],
    [0.1811, 0, -1.6341],  [0.1896, 0, -1.6477],
    [0.1926, 0, -1.6633],  [0.1927, 0, -1.6662],
    [0.1927, 0, -2.0339],  [0.0743, 0, -2.0341],
    [0.0743, 0, -1.8646],  [0.0759, 0, -1.8354],
    [0.0786, 0, -1.8062],  [0.0803, 0, -1.7917],
    [0.0735, 0, -1.8051],  [0.0605, 0, -1.8312],
    [0.0473, 0, -1.8573],  [0.0422, 0, -1.8659],
    [-0.0534, 0, -2.0154], [-0.0632, 0, -2.0261],
    [-0.0741, 0, -2.0322], [-0.0909, 0, -2.034]
]
s_envday['inner_circle_rr_shape'] = [ 
    [0, 0, -1],            [-0.1961, 0, -0.9819],
    [-0.3822, 0, -0.9202], [-0.5587, 0, -0.8291],
    [-0.7071, 0, -0.707],  [-0.8308, 0, -0.5588],
    [-0.9228, 0, -0.3822], [-0.9811, 0, -0.1961],
    [-1.0001, 0, 0],       [-0.9811, 0, 0.1961],
    [-0.9228, 0, 0.3822],  [-0.8361, 0, 0.5486],
    [-0.7071, 0, 0.7071],  [-0.5587, 0, 0.8311],
    [-0.3822, 0, 0.9228],  [-0.1961, 0, 0.9811],
    [0, 0, 1.0001],        [0.1961, 0, 0.981],
    [0.3822, 0, 0.9228],   [0.5587, 0, 0.8309],
    [0.7071, 0, 0.7071],   [0.8282, 0, 0.5587],
    [0.9228, 0, 0.3822],   [0.9811, 0, 0.1961],
    [1.0001, 0, 0],        [0.9811, 0, -0.1961],
    [0.9228, 0, -0.3822],  [0.831, 0, -0.5587],
    [0.7071, 0, -0.7071],  [0.5587, 0, -0.8308],
    [0.3822, 0, -0.9228],  [0.1961, 0, -0.981]
]

s_envday['outer_circle_rr_shape'] = [ 
    [0, 0, -1],            [-0.1961, 0, -0.9815],
    [-0.3822, 0, -0.9202], [-0.5587, 0, -0.8288],
    [-0.7071, 0, -0.707],  [-0.8282, 0, -0.5588],
    [-0.9228, 0, -0.3822], [-0.981, 0, -0.1961],
    [-1.0001, 0, 0],       [-0.981, 0, 0.1961],
    [-0.9228, 0, 0.3822],  [-0.8308, 0, 0.5538],
    [-0.7071, 0, 0.7071],  [-0.5587, 0, 0.8302],
    [-0.3822, 0, 0.9228],  [-0.1961, 0, 0.9811],
    [0, 0, 1.0001],        [0.1961, 0, 0.981],
    [0.3822, 0, 0.9228],   [0.5587, 0, 0.8279],
    [0.7071, 0, 0.7071],   [0.8308, 0, 0.5587],
    [0.9228, 0, 0.3822],   [0.981, 0, 0.1961],
    [1.0001, 0, 0],        [0.981, 0, -0.1961],
    [0.9228, 0, -0.3822],  [0.8308, 0, -0.5587],
    [0.7071, 0, -0.7071],  [0.5587, 0, -0.8308],
    [0.3822, 0, -0.9228],  [0.1961, 0, -0.9784]
]
s_envday['compass_shape'] = [             
    [0, 0, -0.9746], [-0.2163, 0, -0.0012],
    [0, 0, 0.9721], [0.2162, 0, -0.0012],
    [0, 0, -0.9746]
]

s_envday['east_arrow_shape'] = [ 
    [1.2978, 0, -0.2175], [1.2978, 0, 0.215],
    [1.5141, 0, -0.0012], [1.2978, 0, -0.2175]
]
s_envday['south_arrow_shape'] = [ 
    [-0.2163, 0, 1.2965], [0.2162, 0, 1.2965],
    [0, 0, 1.5128], [-0.2163, 0, 1.2965]
]
s_envday['west_arrow_shape'] = [ 
    [-1.2979, 0, -0.2175], [-1.2979, 0, 0.215],
    [-1.5142, 0, -0.0012], [-1.2979, 0, -0.2175]
]
s_envday['north_arrow_shape'] = [ 
    [-0.2163, 0, -1.2991], [0.2162, 0, -1.2991],
    [0, 0, -1.5154],       [-0.2163, 0, -1.2991]
]

s_diskLight = [
    [0.490300, 0.097500, 0.000000],
    [0.461900, 0.191300, 0.000000],
    [0.415700, 0.277700, 0.000000],
    [0.353500, 0.353500, 0.000000],
    [0.277700, 0.415700, 0.000000],
    [0.191300, 0.461900, 0.000000],
    [0.097500, 0.490300, 0.000000],
    [0.000000, 0.499900, 0.000000],
    [-0.097500, 0.490300, 0.000000],
    [-0.191300, 0.461900, 0.000000],
    [-0.277700, 0.415700, 0.000000],
    [-0.353500, 0.353500, 0.000000],
    [-0.415700, 0.277700, 0.000000],
    [-0.461900, 0.191300, 0.000000],
    [-0.490300, 0.097500, 0.000000],
    [-0.499900, 0.000000, 0.000000],
    [-0.490300, -0.097500, 0.000000],
    [-0.461900, -0.191300, 0.000000],
    [-0.415700, -0.277700, 0.000000],
    [-0.353500, -0.353500, 0.000000],
    [-0.277700, -0.415700, 0.000000],
    [-0.191300, -0.461900, 0.000000],
    [-0.097500, -0.490300, 0.000000],
    [0.000000, -0.499900, 0.000000],
    [0.097500, -0.490300, 0.000000],
    [0.191300, -0.461900, 0.000000],
    [0.277700, -0.415700, 0.000000],
    [0.353500, -0.353500, 0.000000],
    [0.415700, -0.277700, 0.000000],
    [0.461900, -0.191300, 0.000000],
    [0.490300, -0.097500, 0.000000],
    [0.500000, 0.000000, 0.000000],
    [0.490300, 0.097500, 0.000000]
]

s_distantLight = dict()
s_distantLight['arrow1'] =  [
    (0.03316599252,-6.536167e-18,0.0294362),
    (0.03316599252,-7.856030e-17,0.5),
    (0.06810822842,-7.856030e-17,0.5),
    (0,-1.11022302e-16, 1.0),
    (-0.0681082284,-7.85603e-17,0.5),
    (-0.0331659925,-7.85603e-17,0.5),
    (-0.0331659925,-6.53616e-18,0.029436)
]

s_distantLight['arrow2'] =  [
    (0.03316599252,-0.5,0.0294362),
    (0.03316599252,-0.5,0.5),
    (0.06810822842,-0.5,0.5),
    (0,-0.5, 1.0),
    (-0.0681082284,-0.5,0.5),
    (-0.0331659925,-0.5,0.5),
    (-0.0331659925,-0.5,0.029436)
]

s_distantLight['arrow3'] =  [
    (0.03316599252,0.5,0.0294362),
    (0.03316599252,0.5,0.5),
    (0.06810822842,0.5,0.5),
    (0,0.5, 1.0),
    (-0.0681082284,0.5,0.5),
    (-0.0331659925,0.5,0.5),
    (-0.0331659925,0.5,0.029436)
]

s_portalRays = [
    (-1, 0,  0),
    (-2, 0,  0),
    (-1, 0,  0),
    (-1, 0, -1),    
    (-2, 0, -2),
    (-1, 0, -1),
    ( 0, 0, -1),
    ( 0, 0, -2),    
    ( 0, 0, -1),
    ( 1, 0, -1),
    ( 2, 0, -2),
    ( 1, 0, -1),    
    ( 1, 0,  0),
    ( 2, 0,  0),
    ( 1, 0,  0),
    ( 1, 0,  1),    
    ( 2, 0,  2),
    ( 1, 0,  1),
    ( 0, 0,  1),
    ( 0, 0,  2),    
    ( 0, 0,  1),
    (-1, 0,  1),
    (-2, 0,  2),
    (-1, 0,  1),    
    (-1, 0,  0)
]

s_cylinderLight = dict()
s_cylinderLight['vtx'] = [
    [-0.5, -0.4045, -0.2938],
    [-0.5, -0.1545, -0.4755],
    [-0.5, 0.1545, -0.4755],
    [-0.5, 0.4045, -0.2938],
    [-0.5, 0.5, 0],
    [-0.5, 0.4045, 0.2938],
    [-0.5, 0.1545, 0.4755],
    [-0.5, -0.1545, 0.4755],
    [-0.5, -0.4045, 0.2938],
    [-0.5, -0.5, 0],
    [-0.5, -0.4045, -0.2938],

    [0.5, -0.4045, -0.2938],
    [0.5, -0.1545, -0.4755],
    [0.5, 0.1545, -0.4755],
    [0.5, 0.4045, -0.2938],
    [0.5, 0.5, 0],
    [0.5, 0.4045, 0.2938],
    [0.5, 0.1545, 0.4755],
    [0.5, -0.1545, 0.4755],
    [0.5, -0.4045, 0.2938],
    [0.5, -0.5, 0],
    [0.5, -0.4045, -0.2938]
]

s_cylinderLight['indices'] = [
    (0, 1),
    (1, 2),
    (2, 3),
    (3, 4),
    (4, 5),
    (5, 6),
    (6, 7),
    (7, 8),
    (8, 9),
    (9, 10),
    (11, 12),
    (12, 13),
    (13, 14),
    (14, 15),
    (15, 16),
    (16, 17),
    (17, 18),
    (18, 19),
    (19, 20),
    (20, 21),
    (0, 11),
    (2, 13),
    (4, 15),
    (6, 17),
    (8, 19)
]

s_cylinderLight['indices_tris'] = [
    (0, 1, 11),
    (1, 11, 12),    
    (1, 2, 12),
    (2, 12, 13),
    (2, 3, 13),
    (3, 13, 14),
    (3, 4, 14),
    (4, 14, 15),
    (4, 5, 15),
    (5, 15, 16),
    (5, 6, 16),
    (6, 16, 17),
    (6, 7, 17),
    (7, 17, 18),
    (7, 8, 18),
    (8, 18, 19),
    (8, 9, 19),
    (9, 19, 20),
    (9, 10, 20),
    (10, 20, 21)
]

__MTX_Y_180__ = Matrix.Rotation(math.radians(180.0), 4, 'Y')
__MTX_X_90__ = Matrix.Rotation(math.radians(90.0), 4, 'X')
__MTX_Y_90__ = Matrix.Rotation(math.radians(90.0), 4, 'Y')

__MTX_ENVDAYLIGHT_ORIENT__ = transform_utils.convert_to_blmatrix([ 
            1.0000, -0.0000,  0.0000, 0.0000,
            -0.0000, -0.0000,  1.0000, 0.0000,
            -0.0000,  1.0000, -0.0000, 0.0000,
            0.0000,  0.0000,  0.0000, 1.0000])

if not bpy.app.background:
    # Code reference: https://projects.blender.org/blender/blender/src/branch/main/doc/python_api/examples/gpu.7.py

    vert_out = gpu.types.GPUStageInterfaceInfo("image_interface")
    vert_out.smooth('VEC2', "uvInterp")

    _SHADER_IMAGE_INFO_ = gpu.types.GPUShaderCreateInfo()

    _SHADER_IMAGE_INFO_.push_constant('MAT4', "viewProjectionMatrix")
    _SHADER_IMAGE_INFO_.sampler(0, 'FLOAT_2D', "image")
    _SHADER_IMAGE_INFO_.vertex_in(0, 'VEC3', "position")
    _SHADER_IMAGE_INFO_.vertex_in(1, 'VEC2', "uv")
    _SHADER_IMAGE_INFO_.vertex_out(vert_out)
    _SHADER_IMAGE_INFO_.fragment_out(0, 'VEC4', "FragColor")

    _SHADER_IMAGE_INFO_.vertex_source(
        '''
        void main()
        {
            gl_Position = viewProjectionMatrix * vec4(position, 1.0f);
            uvInterp = uv;
        }
        ''')    
    _SHADER_IMAGE_INFO_.fragment_source(
        '''
        void main()
        {
            FragColor = texture(image, uvInterp);
        }

        ''')

    _SHADER_COLOR_INFO_ = gpu.types.GPUShaderCreateInfo()
    _SHADER_COLOR_INFO_.vertex_in(0, 'VEC3', "position")
    _SHADER_COLOR_INFO_.push_constant('MAT4', "viewProjectionMatrix")
    _SHADER_COLOR_INFO_.push_constant('VEC4', 'lightColor')
    _SHADER_COLOR_INFO_.fragment_out(0, 'VEC4', 'FragColor')

    _SHADER_COLOR_INFO_.vertex_source(
        '''
        void main()
        {
            gl_Position = viewProjectionMatrix * vec4(position, 1.0f);
        }
        ''')    
    _SHADER_COLOR_INFO_.fragment_source(
        '''
        void main()
        {
            FragColor = lightColor;
        }

        ''') 
    
_SHADER_ = None
SHADER_SOLID_IMAGE = None
SHADER_SOLID_COLOR = None
if not bpy.app.background:
    uniform_color =  '3D_UNIFORM_COLOR'
    if BLENDER_41:
        uniform_color = 'UNIFORM_COLOR'
    _SHADER_ = gpu.shader.from_builtin(uniform_color)

    SHADER_SOLID_IMAGE = gpu.shader.create_from_info(_SHADER_IMAGE_INFO_)
    SHADER_SOLID_COLOR = gpu.shader.create_from_info(_SHADER_COLOR_INFO_)

_SELECTED_COLOR_ = (1, 1, 1)
_WIRE_COLOR_ = (0, 0, 0)
if 'Default' in bpy.context.preferences.themes:
    _SELECTED_COLOR_ = bpy.context.preferences.themes['Default'].view_3d.object_active
    _WIRE_COLOR_ = bpy.context.preferences.themes['Default'].view_3d.wire

def set_selection_color(ob, opacity=1.0):
    global _SELECTED_COLOR_, _WIRE_COLOR_
    if ob in bpy.context.selected_objects:
        col = (_SELECTED_COLOR_[0], _SELECTED_COLOR_[1], _SELECTED_COLOR_[2], opacity)
    else:
        col = (_WIRE_COLOR_[0], _WIRE_COLOR_[1], _WIRE_COLOR_[2], opacity)
       
    _SHADER_.uniform_float("color", col)

def _get_indices(l):
    indices = []
    for i in range(0, len(l)):
        if i == len(l)-1:
            indices.append((i, 0))
        else:
            indices.append((i, i+1)) 

    return indices   

def _get_indices_tris(l):
    indices = []
    for i in range(0, len(l)):
        if i == len(l)-1:
            indices.append((i-1, i, 0))
        else:
            indices.append((i, i+1, i+2)) 

    return indices 

def _get_sun_direction(ob):
    light = ob.data
    rm = light.renderman.get_light_node()

    m = __MTX_ENVDAYLIGHT_ORIENT__

    month = float(rm.month)
    day = float(rm.day)
    year = float(rm.year)
    hour = float(rm.hour)
    zone = rm.zone
    latitude = rm.latitude
    longitude = rm.longitude

    sunDirection = Vector([rm.sunDirection[0], rm.sunDirection[1], rm.sunDirection[2]])
    
    if month == 0.0:
        return sunDirection

    if month == 1.0:
        dayNumber = day
    elif month == 2.0:
        dayNumber = day + 31.0
    else:
        year_mod = 0.0
        if math.fmod(year, 4.0) != 0.0:
            year_mod = 0.0
        elif math.fmod(year, 100.0) != 0.0:
            year_mod = 1.0
        elif math.fmod(year, 400.0) != 0.0:
            year_mod = 0.0
        else:
            year_mod = 1.0

        dayNumber = math.floor(30.6 * month - 91.4) + day + 59.0 + year_mod

    dayAngle = 2.0 * math.pi * float(dayNumber - 81.0 + (hour - zone) / 24.0) / 365.0
    timeCorrection = 4.0 * (longitude - 15.0 * zone) + 9.87 * math.sin(2.0 * dayAngle) - 7.53 * math.cos(1.0 * dayAngle) - 1.50 * math.sin(1.0 * dayAngle)
    hourAngle = math.radians(15.0) * (hour + timeCorrection / 60.0 - 12.0)
    declination = math.asin(math.sin(math.radians(23.45)) * math.sin(dayAngle))
    elevation = math.asin(math.sin(declination) * math.sin(math.radians(latitude)) + math.cos(declination) * math.cos(math.radians(latitude)) * math.cos(hourAngle))
    azimuth = math.acos((math.sin(declination) * math.cos(math.radians(latitude)) - math.cos(declination) * math.sin(math.radians(latitude)) * math.cos(hourAngle)) / math.cos(elevation))
    if hourAngle > 0.0:
        azimuth = 2.0 * math.pi - azimuth
    sunDirection[0] = math.cos(elevation) * math.sin(azimuth)
    sunDirection[1] = max(math.sin(elevation), 0)
    sunDirection[2] = math.cos(elevation) * math.cos(azimuth)
    
    return m @ sunDirection

def load_gl_texture(tex):
    global _PRMAN_TEX_CACHE_
    real_path = string_utils.expand_string(tex)

    ice._registry.Mark() 
    iceimg = ice.Load(real_path)
    iceimg = iceimg.TypeConvert(ice.constants.FLOAT)

    x1, x2, y1, y2 = iceimg.DataBox()
    width = (x2 - x1) + 1
    height = (y2 - y1) + 1 

    # Resize image to be max 2k
    maxRes = 2048
    largestDim = height 
    if width > height:
        largestDim = width
    scaledImg = None
    if largestDim > maxRes:
        scale = (maxRes/largestDim, maxRes/largestDim)
        scaledImg = iceimg.Resize(scale)
    
    # if the image was scaled, then get values for the scaled version
    if scaledImg:
        iceimg = scaledImg
        x1, x2, y1, y2 = scaledImg.DataBox()
        width = (x2 - x1) + 1
        height = (y2 - y1) + 1 

    numChannels = iceimg.Ply() 
    iFormat = 'RGBA32F'
    if numChannels != 4:
        # if this is not a 4-channel image, we create a card with an alpha
        # and composite the image over the card
        bg = ice.Card(ice.constants.FLOAT, [0,0,0,1])
        iceimg = bg.Over(iceimg)

    # Generate texture
    buffer = iceimg.AsByteArray()
    pixels = gpu.types.Buffer('FLOAT', len(buffer), buffer)
    texture = gpu.types.GPUTexture((width, height), format=iFormat, data=pixels)
    _PRMAN_TEX_CACHE_[tex] = texture

    ice._registry.RemoveToMark()
    del iceimg   

    return texture  

def make_sphere():
    """
    Return a list of vertices (list) in local space.
    a 4x4 sphere looks like so:
        0  1  2  3  - 0
        4  5  6  7  - 4
        8  9  10 11 - 8
        12 13 14 15 - 12
    i.e., we repeat the first and last vertex in each column so they may have
    different uv coords. The first vertex has u=0.0 and the repeated first
    vertex has u=1.0.
    The top and bottom rows are the poles and all vertice have the same position.
    """    
    cols = 32
    rows = 32
    radius = 1.0

    last_vtx_idx_in_col = cols - 1
    vtxs = []

    phi_step = math.pi / float(rows - 1)
    theta_step = 2.0 * math.pi / float(cols)
    for i in range(rows):
        phi = float(i) * phi_step
        for j in range(cols):
            theta = float(j) * theta_step
            p = [radius * math.sin(phi) * math.cos(theta),
                    radius * math.cos(phi),
                    radius * math.sin(phi) * math.sin(theta)]
            vtxs.append(p)
            if j == last_vtx_idx_in_col:
                vtxs.append(vtxs[-cols])

    return vtxs    

def make_sphere_idx_buffer():
    """
    Fill the provided index buffer to draw the shape.
    This is a 4x4 sphere
    0  1  2  3- 4     0  1  2  3  4
                    |/ |/ |/ |/ |    [0, 5, 1, 6, 2, 7, 3, 8, 4, 9, 9,
    5  6  7  8- 9     5  6  7  8  9     5, 5, 10, 6, 11, 7, 12, 8, 13, 9, 14, 14
                    |/ |/ |/ |/ |     10, 10, 15, 11, 16, 12, 17, 13, 18, 14, 19, 19]
    10 11 12 13-14    10 11 12 13 14
                    |/ |/ |/ |/ |
    15 16 17 18-19    15  16 17 18 19
    """
    cols = 32
    rows = 32
    num_vtx = rows * cols + rows

    ncols = cols + 1

    idxs = []
    ofst = [0]
    base_idx = 0                   # index of first vtx of the strip
    last_idx = num_vtx - 1

    for i in range(0, rows - 1):
        for j in range(ncols):
            if j == 0:
                # repeat first index
                idxs.append(base_idx + j)

            idxs.append(base_idx + j)
            idxs.append(min(base_idx + j + ncols, last_idx))

            # loop to base_idx and repeat last index
            if j == ncols - 1:
                idxs.append(idxs[-1])

        base_idx += ncols
        ofst.append(len(idxs))

    num_idxs = len(idxs)
    return idxs

def make_sphere_uvs(uv_offsets=[0.0, 0.0]):
    uvs = []
    cols = 32
    rows = 32

    ncols = cols + 1

    cstep = (1.0 / cols)
    rstep = 1.0 / (rows - 1)
    for i in range(rows):
        for j in range(ncols):
            uv = [j * cstep, i * rstep]
            uv[0] += uv_offsets[0]
            uv[1] += uv_offsets[1]
            uvs.append(uv)

    return uvs   

def make_dome_light_uvs(uv_offsets=[0.25, 0.0]):
    global DOME_LIGHT_UVS
    if DOME_LIGHT_UVS:
        return DOME_LIGHT_UVS
    
    DOME_LIGHT_UVS = make_sphere_uvs(uv_offsets=uv_offsets)
    return DOME_LIGHT_UVS

def draw_solid(ob, pts, mtx, uvs=list(), indices=None, tex='', col=None):
    global _PRMAN_TEX_CACHE_

    scene = bpy.context.scene
    rm = scene.renderman

    if bpy.context.space_data.shading.type in ['WIREFRAME', 'RENDERED']:
        return

    if rm.is_rman_viewport_rendering:
        return    

    if not prefs_utils.get_pref('rman_viewport_draw_lights_textured'):
        return
    
    if not ob.data.renderman.rman_vp_draw_texture:
        return
    
    real_path = string_utils.expand_string(tex)
    if os.path.exists(real_path):              
        batch = batch_for_shader(SHADER_SOLID_IMAGE, 'TRIS', {"position": pts, "uv": uvs}, indices=indices)               

        texture = _PRMAN_TEX_CACHE_.get(tex, None)
        if not texture:
            texture = load_gl_texture(tex)

        SHADER_SOLID_IMAGE.bind()
        matrix = bpy.context.region_data.perspective_matrix
        SHADER_SOLID_IMAGE.uniform_float("viewProjectionMatrix", matrix @ mtx)
        SHADER_SOLID_IMAGE.uniform_sampler("image", texture)
        gpu.state.blend_set("ALPHA")
        gpu.state.depth_test_set("LESS")
        batch.draw(SHADER_SOLID_IMAGE)           
        gpu.state.depth_test_set("NONE")
        gpu.state.blend_set("NONE")
    

    elif col:
        batch = batch_for_shader(SHADER_SOLID_COLOR, 'TRIS', {"position": pts}, indices=indices)  

        lightColor = (col[0], col[1], col[2], 1.0)
        SHADER_SOLID_COLOR.bind()
        SHADER_SOLID_COLOR.uniform_float("lightColor", lightColor)
        matrix = bpy.context.region_data.perspective_matrix   
        SHADER_SOLID_COLOR.uniform_float("viewProjectionMatrix", matrix @ mtx)
        gpu.state.depth_test_set("LESS")
        gpu.state.blend_set("ALPHA")
        batch.draw(SHADER_SOLID_COLOR)
        gpu.state.blend_set("NONE")
        gpu.state.depth_test_set("NONE")            

def draw_line_shape(ob, shader, pts, indices):  
    do_draw = ((ob in bpy.context.selected_objects) or (prefs_utils.get_pref('rman_viewport_lights_draw_wireframe')))
    if do_draw:
        batch = batch_for_shader(shader, 'LINES', {"pos": pts}, indices=indices)    
        gpu.state.depth_test_set("LESS")
        gpu.state.blend_set("ALPHA")
        batch.draw(shader)
        gpu.state.depth_test_set("NONE")
        gpu.state.blend_set("NONE")

def draw_rect_light(ob):
    global _FRUSTUM_DRAW_HELPER_
    _SHADER_.bind()

    set_selection_color(ob)

    ob_matrix = Matrix(ob.matrix_world)    
    scale = Matrix.Scale(ob.data.renderman.get_vp_scale(), 4)
    ob_matrix = ob_matrix @ scale        
    m = ob_matrix @ __MTX_Y_180__ 

    box = [m @ Vector(pt) for pt in s_rmanLightLogo['box']]
    box_indices = _get_indices(s_rmanLightLogo['box'])
    draw_line_shape(ob, _SHADER_, box, box_indices)

    arrow = [m @ Vector(pt) for pt in s_rmanLightLogo['arrow']]
    arrow_indices = _get_indices(s_rmanLightLogo['arrow'])
    draw_line_shape(ob, _SHADER_, arrow, arrow_indices)

    m = ob_matrix
    R_outside = [m @ Vector(pt) for pt in s_rmanLightLogo['R_outside']]
    R_outside_indices = _get_indices(s_rmanLightLogo['R_outside'])
    draw_line_shape(ob, _SHADER_, R_outside, R_outside_indices)
  
    R_inside = [m @ Vector(pt) for pt in s_rmanLightLogo['R_inside']]
    R_inside_indices = _get_indices(s_rmanLightLogo['R_inside'])
    draw_line_shape(ob, _SHADER_, R_inside, R_inside_indices)

    rm = ob.data.renderman
    light_shader = rm.get_light_node()
    light_shader_name = rm.get_light_node_name()  

    m = ob_matrix
    coneAngle = getattr(light_shader, 'coneAngle', 90.0)
    if coneAngle < 90.0:
        softness = getattr(light_shader, 'coneSoftness', 0.0)
        depth = getattr(rm, 'rman_coneAngleDepth', 5.0)
        opacity = getattr(rm, 'rman_coneAngleOpacity', 0.5)
        set_selection_color(ob, opacity=opacity)
        _FRUSTUM_DRAW_HELPER_.update_input_params(method='rect',    
                                                coneAngle=coneAngle, 
                                                coneSoftness=softness,
                                                rman_coneAngleDepth=depth
                                                )
        vtx_buffer = _FRUSTUM_DRAW_HELPER_.vtx_buffer()

        pts = [m @ Vector(pt) for pt in vtx_buffer ]
        indices = _FRUSTUM_DRAW_HELPER_.idx_buffer(len(pts), 0, 0)   
        draw_line_shape(ob, _SHADER_, pts, indices)          

    if light_shader_name == 'PxrRectLight':
        m = ob_matrix @ __MTX_Y_180__ 
        tex = light_shader.lightColorMap
        col = light_shader.lightColor
        
        pts = ((0.5, -0.5, 0.0), (-0.5, -0.5, 0.0), (-0.5, 0.5, 0.0), (0.5, 0.5, 0.0))
        uvs = ((1, 1), (0, 1), (0, 0), (1, 0))
        indices = _get_indices_tris(pts)
        draw_solid(ob, pts, m, uvs=uvs, indices=indices, tex=tex, col=col)  

def draw_sphere_light(ob):
    global _FRUSTUM_DRAW_HELPER_
    
    _SHADER_.bind()

    set_selection_color(ob)

    ob_matrix = Matrix(ob.matrix_world)    
    scale = Matrix.Scale(ob.data.renderman.get_vp_scale(), 4)
    ob_matrix = ob_matrix @ scale    
    m = ob_matrix @ __MTX_Y_180__ 

    disk = [m @ Vector(pt) for pt in s_diskLight]
    disk_indices = _get_indices(s_diskLight)
    draw_line_shape(ob, _SHADER_, disk, disk_indices)

    m2 = m @ __MTX_Y_90__ 
    disk = [m2 @ Vector(pt) for pt in s_diskLight]
    disk_indices = _get_indices(s_diskLight)
    draw_line_shape(ob, _SHADER_, disk, disk_indices)

    m3 = m @ __MTX_X_90__ 
    disk = [m3 @ Vector(pt) for pt in s_diskLight]
    disk_indices = _get_indices(s_diskLight)
    draw_line_shape(ob, _SHADER_, disk, disk_indices)

    m = ob_matrix
    R_outside = [m @ Vector(pt) for pt in s_rmanLightLogo['R_outside']]
    R_outside_indices = _get_indices(s_rmanLightLogo['R_outside'])
    draw_line_shape(ob, _SHADER_, R_outside, R_outside_indices)

    R_inside = [m @ Vector(pt) for pt in s_rmanLightLogo['R_inside']]
    R_inside_indices = _get_indices(s_rmanLightLogo['R_inside'])
    draw_line_shape(ob, _SHADER_, R_inside, R_inside_indices)

    rm = ob.data.renderman
    light_shader = rm.get_light_node()
    light_shader_name = rm.get_light_node_name()   

    m = ob_matrix
    coneAngle = getattr(light_shader, 'coneAngle', 90.0)
    if coneAngle < 90.0:
        softness = getattr(light_shader, 'coneSoftness', 0.0)
        depth = getattr(rm, 'rman_coneAngleDepth', 5.0)
        opacity = getattr(rm, 'rman_coneAngleOpacity', 0.5)
        set_selection_color(ob, opacity=opacity)        
        _FRUSTUM_DRAW_HELPER_.update_input_params(method='rect',    
                                                coneAngle=coneAngle, 
                                                coneSoftness=softness,
                                                rman_coneAngleDepth=depth
                                                )
        vtx_buffer = _FRUSTUM_DRAW_HELPER_.vtx_buffer()

        pts = [m @ Vector(pt) for pt in vtx_buffer ]
        indices = _FRUSTUM_DRAW_HELPER_.idx_buffer(len(pts), 0, 0)      
        draw_line_shape(ob, _SHADER_, pts, indices)         

    m = ob_matrix @ Matrix.Scale(0.5, 4) @ __MTX_X_90__ 
    idx_buffer = make_sphere_idx_buffer() 
    if light_shader_name in ['PxrSphereLight']:
        col = light_shader.lightColor
        sphere_indices = [(idx_buffer[i], idx_buffer[i+1], idx_buffer[i+2]) for i in range(0, len(idx_buffer)-2) ]
        draw_solid(ob, make_sphere(), m, col=col, indices=sphere_indices)               

def draw_envday_light(ob): 

    _SHADER_.bind()

    set_selection_color(ob)

    loc, rot, sca = Matrix(ob.matrix_world).decompose()
    axis,angle = rot.to_axis_angle()
    scale = ob.data.renderman.get_vp_scale() * max(sca) # take the max axis   
    m = Matrix.Translation(loc)
    m = m @ Matrix.Rotation(angle, 4, axis)
    m = m @ Matrix.Scale(scale, 4)

    ob_matrix = m
    
    m = Matrix(ob_matrix)
    m = m @ __MTX_X_90__ 

    west_rr_shape = [m @ Vector(pt) for pt in s_envday['west_rr_shape']]
    west_rr_indices = _get_indices(s_envday['west_rr_shape'])
    draw_line_shape(ob, _SHADER_, west_rr_shape, west_rr_indices)

    east_rr_shape = [m @ Vector(pt) for pt in s_envday['east_rr_shape']]
    east_rr_indices = _get_indices(s_envday['east_rr_shape'])
    draw_line_shape(ob, _SHADER_, east_rr_shape, east_rr_indices)

    south_rr_shape = [m @ Vector(pt) for pt in s_envday['south_rr_shape']]
    south_rr_indices = _get_indices(s_envday['south_rr_shape'])
    draw_line_shape(ob, _SHADER_, south_rr_shape, south_rr_indices)

    north_rr_shape = [m @ Vector(pt) for pt in s_envday['north_rr_shape']]
    north_rr_indices = _get_indices(s_envday['north_rr_shape'])
    draw_line_shape(ob, _SHADER_, north_rr_shape, north_rr_indices)

    inner_circle_rr_shape = [m @ Vector(pt) for pt in s_envday['inner_circle_rr_shape']]
    inner_circle_rr_shape_indices = _get_indices(s_envday['inner_circle_rr_shape'])
    draw_line_shape(ob, _SHADER_, inner_circle_rr_shape, inner_circle_rr_shape_indices)

    outer_circle_rr_shape = [m @ Vector(pt) for pt in s_envday['outer_circle_rr_shape']]
    outer_circle_rr_shape_indices = _get_indices(s_envday['outer_circle_rr_shape'])
    draw_line_shape(ob, _SHADER_, outer_circle_rr_shape, outer_circle_rr_shape_indices)

    compass_shape = [m @ Vector(pt) for pt in s_envday['compass_shape']]
    compass_shape_indices = _get_indices(s_envday['compass_shape'])
    draw_line_shape(ob, _SHADER_, compass_shape, compass_shape_indices)

    east_arrow_shape = [m @ Vector(pt) for pt in s_envday['east_arrow_shape']]
    east_arrow_shape_indices = _get_indices(s_envday['east_arrow_shape'])
    draw_line_shape(ob, _SHADER_, east_arrow_shape, east_arrow_shape_indices)

    west_arrow_shape = [m @ Vector(pt) for pt in s_envday['west_arrow_shape']]
    west_arrow_shape_indices = _get_indices(s_envday['west_arrow_shape'])
    draw_line_shape(ob, _SHADER_, west_arrow_shape, west_arrow_shape_indices)

    north_arrow_shape = [m @ Vector(pt) for pt in s_envday['north_arrow_shape']]
    north_arrow_shape_indices = _get_indices(s_envday['north_arrow_shape'])
    draw_line_shape(ob, _SHADER_, north_arrow_shape, north_arrow_shape_indices)

    south_arrow_shape = [m @ Vector(pt) for pt in s_envday['south_arrow_shape']]
    south_arrow_shape_indices = _get_indices(s_envday['south_arrow_shape'])
    draw_line_shape(ob, _SHADER_, south_arrow_shape, south_arrow_shape_indices)

    sunDirection = _get_sun_direction(ob)
    sunDirection =  Matrix(ob_matrix) @ Vector(sunDirection)
    origin = Matrix(ob_matrix) @ Vector([0,0,0])
    sunDirection_pts = [ origin, sunDirection]
    draw_line_shape(ob, _SHADER_, sunDirection_pts, indices=[(0,1)])

    # draw a sphere to represent the sun
    v = sunDirection - origin
    translate = Matrix.Translation(v)
    sphere_shape = []
    for p in make_sphere():
        mat = ob_matrix @ Matrix.Scale(0.10, 4)
        pt = mat @ Vector(p)
        pt = translate @ pt
        sphere_shape.append( pt )

    idx_buffer = make_sphere_idx_buffer()
    sphere_indices = [(idx_buffer[i], idx_buffer[i+1]) for i in range(0, len(idx_buffer)-1) ]
     
    draw_line_shape(ob, _SHADER_, sphere_shape, sphere_indices)

def draw_cheat_shadow_lightfilter(ob): 
                 
    _SHADER_.bind()

    set_selection_color(ob)

    ob_matrix = Matrix(ob.matrix_world)    
    scale = Matrix.Scale(ob.data.renderman.get_vp_scale(), 4)
    ob_matrix = ob_matrix @ scale        
    m = ob_matrix @ __MTX_Y_180__ 

    box = [m @ Vector(pt) for pt in s_rmanLightLogo['box']]
    box_indices = _get_indices(s_rmanLightLogo['box'])
    draw_line_shape(ob, _SHADER_, box, box_indices)

    arrow = [m @ Vector(pt) for pt in s_rmanLightLogo['arrow']]
    arrow_indices = _get_indices(s_rmanLightLogo['arrow'])
    draw_line_shape(ob, _SHADER_, arrow, arrow_indices)

def draw_disk_light(ob): 
    global _FRUSTUM_DRAW_HELPER_
                 
    _SHADER_.bind()

    set_selection_color(ob)

    ob_matrix = Matrix(ob.matrix_world)    
    scale = Matrix.Scale(ob.data.renderman.get_vp_scale(), 4)
    ob_matrix = ob_matrix @ scale    
    m = ob_matrix @ __MTX_Y_180__ 

    disk = [m @ Vector(pt) for pt in s_diskLight]
    disk_indices = _get_indices(s_diskLight)
    draw_line_shape(ob, _SHADER_, disk, disk_indices)

    arrow = [m @ Vector(pt) for pt in s_rmanLightLogo['arrow']]
    arrow_indices = _get_indices(s_rmanLightLogo['arrow'])
    draw_line_shape(ob, _SHADER_, arrow, arrow_indices)

    m = ob_matrix
    R_outside = [m @ Vector(pt) for pt in s_rmanLightLogo['R_outside']]
    R_outside_indices = _get_indices(s_rmanLightLogo['R_outside'])
    draw_line_shape(ob, _SHADER_, R_outside, R_outside_indices)
  
    R_inside = [m @ Vector(pt) for pt in s_rmanLightLogo['R_inside']]
    R_inside_indices = _get_indices(s_rmanLightLogo['R_inside'])
    draw_line_shape(ob, _SHADER_, R_inside, R_inside_indices)

    ob_matrix = Matrix(ob.matrix_world)   
    rm = ob.data.renderman
    light_shader = rm.get_light_node()    

    m = ob_matrix
    coneAngle = getattr(light_shader, 'coneAngle', 90.0)
    if coneAngle < 90.0:
        softness = getattr(light_shader, 'coneSoftness', 0.0)
        depth = getattr(rm, 'rman_coneAngleDepth', 5.0)
        opacity = getattr(rm, 'rman_coneAngleOpacity', 0.5)
        set_selection_color(ob, opacity=opacity)
        _FRUSTUM_DRAW_HELPER_.update_input_params(method='rect',    
                                                coneAngle=coneAngle, 
                                                coneSoftness=softness,
                                                rman_coneAngleDepth=depth
                                                )
        vtx_buffer = _FRUSTUM_DRAW_HELPER_.vtx_buffer()

        pts = [m @ Vector(pt) for pt in vtx_buffer ]
        indices = _FRUSTUM_DRAW_HELPER_.idx_buffer(len(pts), 0, 0)      
        draw_line_shape(ob, _SHADER_, pts, indices)      
 
    m = ob_matrix @ __MTX_Y_180__ 
    col = light_shader.lightColor    
    disk.insert(0, ob_matrix @ __MTX_Y_180__  @ Vector((0.0, 0.0, 0.0)))
    indices = []
    for i in range(1, len(disk)):
        indices.append((0, i, i+1))
    draw_solid(ob, s_diskLight, m, col=col, indices=indices)   

def draw_dist_light(ob):      
    
    _SHADER_.bind()

    set_selection_color(ob)

    ob_matrix = Matrix(ob.matrix_world)  
    loc, rot, sca = Matrix(ob.matrix_world).decompose()
    scale = ob.data.renderman.get_vp_scale() * max(sca) # take the max axis 
    scale = Matrix.Scale(scale, 4)
    ob_matrix = ob_matrix @ scale
    m = ob_matrix @ __MTX_Y_180__

    disk = [m @ Vector(pt) for pt in s_diskLight]
    disk_indices = _get_indices(s_diskLight)
    draw_line_shape(ob, _SHADER_, disk, disk_indices)    

    arrow1 = [m @ Vector(pt) for pt in s_distantLight['arrow1']]
    arrow1_indices = _get_indices(s_distantLight['arrow1'])
    draw_line_shape(ob, _SHADER_, arrow1, arrow1_indices)

    arrow2 = [m @ Vector(pt) for pt in s_distantLight['arrow2']]
    arrow2_indices = _get_indices(s_distantLight['arrow2'])
    draw_line_shape(ob, _SHADER_, arrow2, arrow2_indices)

    arrow3 = [m @ Vector(pt) for pt in s_distantLight['arrow3']]
    arrow3_indices = _get_indices(s_distantLight['arrow3'])
    draw_line_shape(ob, _SHADER_, arrow3, arrow3_indices)

    m = ob_matrix
    R_outside = [m @ Vector(pt) for pt in s_rmanLightLogo['R_outside']]
    R_outside_indices = _get_indices(s_rmanLightLogo['R_outside'])
    draw_line_shape(ob, _SHADER_, R_outside, R_outside_indices)
  
    R_inside = [m @ Vector(pt) for pt in s_rmanLightLogo['R_inside']]
    R_inside_indices = _get_indices(s_rmanLightLogo['R_inside'])
    draw_line_shape(ob, _SHADER_, R_inside, R_inside_indices)

def draw_portal_light(ob):
    _SHADER_.bind()

    set_selection_color(ob)

    ob_matrix = Matrix(ob.matrix_world)   
    scale = Matrix.Scale(ob.data.renderman.get_vp_scale(), 4)
    ob_matrix = ob_matrix @ scale
    m = ob_matrix

    R_outside = [m @ Vector(pt) for pt in s_rmanLightLogo['R_outside']]
    R_outside_indices = _get_indices(s_rmanLightLogo['R_outside'])
    draw_line_shape(ob, _SHADER_, R_outside, R_outside_indices)
  
    R_inside = [m @ Vector(pt) for pt in s_rmanLightLogo['R_inside']]
    R_inside_indices = _get_indices(s_rmanLightLogo['R_inside'])
    draw_line_shape(ob, _SHADER_, R_inside, R_inside_indices)

    m = ob_matrix @ __MTX_Y_180__ 
    arrow = [m @ Vector(pt) for pt in s_rmanLightLogo['arrow']]
    arrow_indices = _get_indices(s_rmanLightLogo['arrow'])
    draw_line_shape(ob, _SHADER_, arrow, arrow_indices)    

    m = ob_matrix @ __MTX_X_90__ 
    m = m @ Matrix.Scale(0.5, 4)
    rays = [m @ Vector(pt) for pt in s_portalRays]
    rays_indices = _get_indices(s_portalRays)
    draw_line_shape(ob, _SHADER_, rays, rays_indices)

def draw_dome_light(ob):
    _SHADER_.bind()

    set_selection_color(ob)

    loc, rot, sca = Matrix(ob.matrix_world).decompose()
    axis,angle = rot.to_axis_angle()
    scale = ob.data.renderman.get_vp_scale() * max(sca) # take the max axis   
    m = Matrix.Rotation(angle, 4, axis)
    m = m @ Matrix.Scale(scale, 4)
    m = m @ __MTX_X_90__ 

    # the GPU module doesn't seem to do any texture wrapping
    # when UVs go over the boundary. Reset the UV offsets
    # and rotate 90 degrees on the Y-axis
    uv_offsets = [0.0, 0.0]
    m = m @ __MTX_Y_90__ 

    sphere_pts = make_sphere()
    sphere = [m @ Vector(p) for p in sphere_pts]
    idx_buffer = make_sphere_idx_buffer() 
    sphere_indices = [(idx_buffer[i], idx_buffer[i+1]) for i in range(0, len(idx_buffer)-1) ]

    draw_line_shape(ob, _SHADER_, sphere, sphere_indices)

    rm = ob.data.renderman
    light_shader = rm.get_light_node()
    tex = light_shader.lightColorMap
    real_path = string_utils.expand_string(tex)
    if os.path.exists(real_path):
        sphere_indices = [(idx_buffer[i], idx_buffer[i+1], idx_buffer[i+2]) for i in range(0, len(idx_buffer)-2) ]
        draw_solid(ob, sphere_pts, m, uvs=make_dome_light_uvs(uv_offsets=uv_offsets), tex=tex, indices=sphere_indices)

def draw_cylinder_light(ob):
    global _FRUSTUM_DRAW_HELPER_

    _SHADER_.bind()

    set_selection_color(ob)

    ob_matrix = ob.matrix_world
    scale = Matrix.Scale(ob.data.renderman.get_vp_scale(), 4)
    ob_matrix = ob_matrix @ scale
    m = ob_matrix

    cylinder = [m @ Vector(pt) for pt in s_cylinderLight['vtx']]
    draw_line_shape(ob, _SHADER_, cylinder, s_cylinderLight['indices'])

    rm = ob.data.renderman
    light_shader = rm.get_light_node()
    coneAngle = getattr(light_shader, 'coneAngle', 90.0)
    if coneAngle < 90.0:
        softness = getattr(light_shader, 'coneSoftness', 0.0)
        depth = getattr(rm, 'rman_coneAngleDepth', 5.0)
        opacity = getattr(rm, 'rman_coneAngleOpacity', 0.5)
        set_selection_color(ob, opacity=opacity)        
        _FRUSTUM_DRAW_HELPER_.update_input_params(method='rect',    
                                                coneAngle=coneAngle, 
                                                coneSoftness=softness,
                                                rman_coneAngleDepth=depth
                                                )
        vtx_buffer = _FRUSTUM_DRAW_HELPER_.vtx_buffer()

        pts = [m @ Vector(pt) for pt in vtx_buffer ]
        indices = _FRUSTUM_DRAW_HELPER_.idx_buffer(len(pts), 0, 0)      
        draw_line_shape(ob, _SHADER_, pts, indices)      

    col = light_shader.lightColor
    draw_solid(ob, s_cylinderLight['vtx'], m, col=col, indices=s_cylinderLight['indices_tris'])  
      

def draw_arc(a, b, numSteps, quadrant, xOffset, yOffset, pts):
    stepAngle = float(_PI0_5_ / numSteps)
    for i in range(0, numSteps):

        angle = stepAngle*i + quadrant*_PI0_5_
        x = a * math.cos(angle)
        y = b * math.sin(angle)
        
        pts.append(Vector([x+xOffset, y+yOffset, 0.0]))
        #pts.append(Vector([x+xOffset, 0.0, y+yOffset]))

def draw_rounded_rectangles(ob, left, right,
                            top,  bottom,
                            radius,
                            leftEdge,  rightEdge,
                            topEdge,  bottomEdge,
                            zOffset1,  zOffset2, 
                            m):

    pts = []
    a = radius+rightEdge
    b = radius+topEdge
    draw_arc(a, b, 10, 0, right, top, pts)
    a = radius+leftEdge
    b = radius+topEdge
    draw_arc(a, b, 10, 1, -left, top, pts)
    a = radius+leftEdge
    b = radius+bottomEdge
    draw_arc(a, b, 10, 2, -left, -bottom, pts)
    
    a = radius+rightEdge
    b = radius+bottomEdge
    draw_arc(a, b, 10, 3, right, -bottom, pts)

    translate = m 
    shape_pts = [translate @ Vector(pt) for pt in pts]
    shape_pts_indices = _get_indices(shape_pts)

    draw_line_shape(ob, _SHADER_, shape_pts, shape_pts_indices)

    translate = m 
    shape_pts = [translate @ Vector(pt) for pt in pts]
    shape_pts_indices = _get_indices(shape_pts)

    draw_line_shape(ob, _SHADER_, shape_pts, shape_pts_indices)

def draw_rod(ob, leftEdge, rightEdge, topEdge,  bottomEdge,
            frontEdge,  backEdge,  scale, width,  radius, 
            left,  right,  top,  bottom,  front, back, world_mat):

    leftEdge *= scale
    rightEdge *= scale
    topEdge *= scale
    backEdge *= scale
    frontEdge *= scale
    bottomEdge *= scale
    
    m = world_mat
    
    # front and back
    draw_rounded_rectangles(ob, left, right, top, bottom, radius,
                          leftEdge, rightEdge,
                          topEdge, bottomEdge, front, -back, m)

 
    m = world_mat @ __MTX_X_90__ 
 
    
    # top and bottom
    
    draw_rounded_rectangles(ob, left, right, back, front, radius,
                          leftEdge, rightEdge,
                          backEdge, frontEdge, top, -bottom, m)
 
    m = world_mat  @ __MTX_Y_90__ 
    
    
    # left and right
    draw_rounded_rectangles(ob, front, back, top, bottom, radius,
                          frontEdge, backEdge,
                          topEdge, bottomEdge, -left, right, m)

def draw_rod_light_filter(ob):
    _SHADER_.bind()

    set_selection_color(ob)

    m = Matrix(ob.matrix_world)        
    scale = Matrix.Scale(ob.data.renderman.get_vp_scale(), 4)    
    m = m @ __MTX_Y_180__ @ scale

    light = ob.data
    rm = light.renderman.get_light_node()

    edge = rm.edge
    width = rm.width
    depth = rm.depth
    height = rm.height
    radius = rm.radius

    left_edge = edge
    right_edge = edge
    top_edge = edge
    bottom_edge = edge
    front_edge = edge
    back_edge = edge

    left = 0.0
    right = 0.0
    top = 0.0
    bottom = 0.0
    front = 0.0
    back = 0.0

    scale_width = 1.0
    scale_height = 1.0
    scale_depth = 1.0

    rod_scale = 0.0

    if light.renderman.get_light_node_name() == 'PxrRodLightFilter':
        left_edge *= rm.leftEdge
        right_edge *= rm.rightEdge
        top_edge *= rm.topEdge
        bottom_edge *= rm.bottomEdge
        front_edge *= rm.frontEdge
        back_edge *= rm.backEdge
        scale_width *= rm.scaleWidth
        scale_height *= rm.scaleHeight
        scale_depth *= rm.scaleDepth
        left = rm.left
        right = rm.right
        top = rm.top
        bottom = rm.bottom
        front = rm.front
        back = rm.back

    left += scale_width * width
    right += scale_width * width
    top += scale_height * height
    bottom += scale_height * height
    front += scale_depth * depth
    back += scale_depth * depth

    draw_rod(ob, left_edge, right_edge,
            top_edge, bottom_edge,
            front_edge, back_edge, rod_scale,
            width, radius,
            left, right, top, bottom, front,
            back, m)
        
    if edge > 0.0:
            
        # draw outside box
        rod_scale = 1.0
        draw_rod(ob, left_edge, right_edge,
            top_edge, bottom_edge,
            front_edge, back_edge, rod_scale,
            width, radius,
            left, right, top, bottom, front,
            back, m)           

def draw_ramp_light_filter(ob):
    _SHADER_.bind()

    set_selection_color(ob)

    light = ob.data
    rm = light.renderman.get_light_node()
    rampType = int(rm.rampType)

    begin = float(rm.beginDist)
    end = float(rm.endDist)    

    # distToLight
    if rampType in (0,2):
        _SHADER_.bind()

        set_selection_color(ob)

        m = Matrix(ob.matrix_world)        
        m = m @ __MTX_Y_180__ 

        # begin
        begin_m = m @ Matrix.Scale(begin, 4)      

        disk = [begin_m @ Vector(pt) for pt in s_diskLight]
        disk_indices = _get_indices(s_diskLight)
        draw_line_shape(ob, _SHADER_, disk, disk_indices)

        m2 = begin_m @ __MTX_Y_90__ 
        disk = [m2 @ Vector(pt) for pt in s_diskLight]
        draw_line_shape(ob, _SHADER_, disk, disk_indices)

        m3 = begin_m @ __MTX_X_90__ 
        disk = [m3 @ Vector(pt) for pt in s_diskLight]
        draw_line_shape(ob, _SHADER_, disk, disk_indices)

        # end
        end_m = m @ Matrix.Scale(end, 4)      

        disk = [end_m @ Vector(pt) for pt in s_diskLight]
        draw_line_shape(ob, _SHADER_, disk, disk_indices)

        m2 = end_m @ __MTX_Y_90__ 
        disk = [m2 @ Vector(pt) for pt in s_diskLight]
        draw_line_shape(ob, _SHADER_, disk, disk_indices)

        m3 = end_m @ __MTX_X_90__ 
        disk = [m3 @ Vector(pt) for pt in s_diskLight]
        draw_line_shape(ob, _SHADER_, disk, disk_indices)

    # linear
    elif rampType == 1:        

        m = Matrix(ob.matrix_world)        
        m = m @ __MTX_Y_180__ 

        box = [m @ Vector(pt) for pt in s_rmanLightLogo['box']]
        n = mathutils.geometry.normal(box)
        n.normalize()
        box1 = []
        for i,pt in enumerate(box):
            if begin > 0.0:
                box1.append(pt + (begin * n))
            else:
                box1.append(pt)

        box_indices = _get_indices(s_rmanLightLogo['box'])
        draw_line_shape(ob, _SHADER_, box, box_indices)

        box2 = [pt + (end * n) for pt in box]
        draw_line_shape(ob, _SHADER_, box2, box_indices)

    # radial
    elif rampType == 3:
        _SHADER_.bind()

        set_selection_color(ob)

        m = Matrix(ob.matrix_world)        
        m = m @ __MTX_Y_180__ 

        disk_indices = _get_indices(s_diskLight)
        if begin > 0.0:
            m1 = m @ Matrix.Scale(begin, 4)      

            disk = [m1 @ Vector(pt) for pt in s_diskLight]
            draw_line_shape(ob, _SHADER_, disk, disk_indices)

        m2 = m @ Matrix.Scale(end, 4)      
        disk = [m2 @ Vector(pt) for pt in s_diskLight]
        draw_line_shape(ob, _SHADER_, disk, disk_indices)

    else:
        pass

def draw_barn_light_filter(ob, light_shader, light_shader_name):
    global _BARN_LIGHT_DRAW_HELPER_

    _SHADER_.bind()

    m = Matrix(ob.matrix_world) 
    scale = Matrix.Scale(ob.data.renderman.get_vp_scale(), 4)    
    m = m @ __MTX_Y_180__ @ scale

    set_selection_color(ob) 

    radius = 1.0
    if light_shader_name in ['PxrGoboLightFilter', 'PxrCookieLightFilter']:
        radius = 0.0
    _BARN_LIGHT_DRAW_HELPER_.update_input_params(ob, radius)
    vtx_buffer = _BARN_LIGHT_DRAW_HELPER_.vtx_buffer()

    pts = [m @ Vector(pt) for pt in vtx_buffer ]
    indices = _BARN_LIGHT_DRAW_HELPER_.idx_buffer(len(pts), 0, 0)
    # blender wants a list of lists
    indices = [indices[i:i+2] for i in range(0, len(indices), 2) if indices[i] is not None]

    draw_line_shape(ob, _SHADER_, pts, indices)

    if light_shader_name in ['PxrGoboLightFilter', 'PxrCookieLightFilter']:  
        col = light_shader.fillColor
        tex = light_shader.map
        w = light_shader.width
        h = light_shader.height
        invertU = int(getattr(light_shader, 'invertU', False))
        invertV = int(getattr(light_shader, 'invertV', False))
        u = 1.0 - invertU
        v = 1.0 - invertV
        pts = ((0.5*w, -0.5*h, 0.0), (-0.5*w, -0.5*h, 0.0), (-0.5*w, 0.5*h, 0.0), (0.5*w, 0.5*h, 0.0))
        #uvs = ((0, 1), (1,1), (1, 0), (0,0))
        uvs = ((1.0-u, v), (u,v), (u, 1.0-v), (1.0-u, 1.0-v))
        indices = _get_indices_tris(pts) 
        draw_solid(ob, pts, m, uvs=uvs, tex=tex, col=col, indices=indices)  

def draw():
    global _PRMAN_TEX_CACHE_
    global _RMAN_TEXTURED_LIGHTS_

    if bpy.context.engine != 'PRMAN_RENDER':
        return    

    # check if overlays is disabled
    viewport = bpy.context.space_data
    if not viewport.overlay.show_overlays:
        return
     
    scene = bpy.context.scene
      
    lights_list = [x for x in bpy.context.view_layer.objects if x.type == 'LIGHT']
    for ob in lights_list:
        if ob.hide_get():
            continue
        # check the local view for this light
        if not ob.visible_in_viewport_get(bpy.context.space_data):
            continue        
        if not ob.data.renderman:
            continue
        rm = ob.data.renderman
        if not rm.use_renderman_node:
            continue

        light_shader = rm.get_light_node()
        if not light_shader:
            continue

        light_shader_name = rm.get_light_node_name()
        if light_shader_name == '':
            return

        if light_shader_name in RMAN_AREA_LIGHT_TYPES:
            if ob.data.type != 'AREA':
                if hasattr(ob.data, 'size'):
                    ob.data.size = 0.0
                ob.data.type = 'AREA'

        elif ob.data.type != 'POINT':
            if hasattr(ob.data, 'size'):
                ob.data.size = 0.0
            ob.data.type = 'POINT'

        if light_shader_name == 'PxrSphereLight': 
            draw_sphere_light(ob)
        elif light_shader_name == 'PxrEnvDayLight': 
            draw_envday_light(ob)
        elif light_shader_name == 'PxrDiskLight': 
            draw_disk_light(ob)
        elif light_shader_name == 'PxrDistantLight': 
            draw_dist_light(ob)       
        elif light_shader_name == 'PxrPortalLight': 
            draw_portal_light(ob)      
        elif light_shader_name == 'PxrDomeLight': 
            if viewport.region_3d.is_perspective:
                # only draw the dome light in perspective view
                draw_dome_light(ob)        
        elif light_shader_name == 'PxrCylinderLight':
            draw_cylinder_light(ob)     
        elif light_shader_name in ['PxrRectLight']:
             draw_rect_light(ob)             
        elif light_shader_name in ['PxrRodLightFilter', 'PxrBlockerLightFilter']:
            draw_rod_light_filter(ob)
        elif light_shader_name == 'PxrRampLightFilter':
            draw_ramp_light_filter(ob)
        elif light_shader_name == 'PxrCheatShadowLightFilter':
            draw_cheat_shadow_lightfilter(ob)
        elif light_shader_name in ['PxrGoboLightFilter', 'PxrCookieLightFilter', 'PxrBarnLightFilter']:
            # get all lights that the barn is attached to
            draw_barn_light_filter(ob, light_shader, light_shader_name)
        else:   
            draw_sphere_light(ob)

    # Clear out any textures not used
    remove_textures = list()
    for k, v in _PRMAN_TEX_CACHE_.items():
        still_exists = False
        for ob in lights_list:  
            rm = ob.data.renderman
            if not rm.use_renderman_node:
                continue
            light_shader = rm.get_light_node()
            if not light_shader:
                continue
            light_shader_name = rm.get_light_node_name()
            if light_shader_name == '':
                return            
            if light_shader_name not in _RMAN_TEXTURED_LIGHTS_:
                continue

            tex = None
            if light_shader_name in ['PxrGoboLightFilter', 'PxrCookieLightFilter']:
                tex = light_shader.map
            else:
                tex = light_shader.lightColorMap

            if tex == k:
                still_exists = True
                break

        if not still_exists:
            del v
            remove_textures.append(k)            

    for k in remove_textures:
        rfb_log().debug("Call glDeleteTextures for: %s" % k)
        del _PRMAN_TEX_CACHE_[k]

def clear_gl_tex_cache(bl_scene=None):
    global _PRMAN_TEX_CACHE_
    if _PRMAN_TEX_CACHE_:
        rfb_log().debug("Clearing _PRMAN_TEX_CACHE_.")
        for k, v in _PRMAN_TEX_CACHE_.items():
            del v

        _PRMAN_TEX_CACHE_.clear()    

def register():
    global _DRAW_HANDLER_
    global _FRUSTUM_DRAW_HELPER_
    global _BARN_LIGHT_DRAW_HELPER_

    if not _FRUSTUM_DRAW_HELPER_:
        _FRUSTUM_DRAW_HELPER_ = FrustumDrawHelper()

    if not _BARN_LIGHT_DRAW_HELPER_:
        _BARN_LIGHT_DRAW_HELPER_ = BarnLightFilterDrawHelper()       
    _DRAW_HANDLER_ = bpy.types.SpaceView3D.draw_handler_add(draw, (), 'WINDOW', 'POST_VIEW')

def unregister():
    global _DRAW_HANDLER_
    if _DRAW_HANDLER_:
        bpy.types.SpaceView3D.draw_handler_remove(_DRAW_HANDLER_, 'WINDOW')
