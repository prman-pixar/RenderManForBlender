from bpy.props import (StringProperty, BoolProperty, EnumProperty)

from ...rman_ui.rman_ui_base import CollectionPanel   
from ...rfb_utils import scene_utils
from ...rfb_utils import shadergraph_utils
from ...rfb_logger import rfb_log
from ... import rfb_icons
from ...rman_constants import RFB_PLATFORM
from ...rfb_utils.prefs_utils import using_qt, show_wip_qt
from ...rman_operators.rman_operators_collections import return_empty_list   
from ...rman_config import __RFB_CONFIG_DICT__ as rfb_config
import bpy
import re
import sys

__LIGHT_MIXER_WINDOW__ = None 
'''
if not bpy.app.background:
    try:
        from ...rman_ui import rfb_qt as rfb_qt
        from rman_utils.vendor.Qt import QtCore, QtWidgets, QtGui 
    except:
        rfb_qt = None

    if rfb_qt:
        class LightMixerQtAppTimed(rfb_qt.RfbBaseQtAppTimed):
            bl_idname = "wm.light_mixer_qt_app_timed"
            bl_label =  "RenderMan Trace Sets Editor"

            def __init__(self):
                super(LightMixerQtAppTimed, self).__init__()

            def execute(self, context):
                self._window = LightMixerQtWrapper()
                return super(LightMixerQtAppTimed, self).execute(context)

        class StandardItem(QtGui.QStandardItem):
            def __init__(self, txt=''):
                super().__init__()
                self.setEditable(False)
                self.setText(txt)

        class ParamLabel(QtWidgets.QLabel):
            def __init__(self, *args, **kwargs):
                super(ParamLabel, self).__init__(*args, **kwargs)
                #self.setAlignment(QtCore.Qt.AlignRight | QtCore.Qt.AlignVCenter)        

        class VBoxLayout(QtWidgets.QVBoxLayout):
            def __init__(self, m=1, s=1):
                super(VBoxLayout, self).__init__()
                self.setContentsMargins(m, m, m, m)
                self.setSpacing(s)


        class HBoxLayout(QtWidgets.QHBoxLayout):
            def __init__(self, m=5, s=10):
                super(HBoxLayout, self).__init__()
                self.setContentsMargins(m, m, m, m)
                self.setSpacing(s)

        class SliderParam(QtWidgets.QWidget):
            def __init__(self, *args, **kwargs):
                super(SliderParam, self).__init__(parent=kwargs.get("parent", None))    
                self.light_shader = None

                # build ui
                self._lyt = HBoxLayout()
                self.light_shader = kwargs.get("light_shader", None)
                self.param = kwargs.get("param", "")
                self.param_label = ParamLabel(kwargs.get("label", "label"))
                self._lyt.addWidget(self.param_label)
                self.sl = QtWidgets.QSlider(QtCore.Qt.Horizontal, self)
                self.sl.setMinimum(kwargs.get("min", 0.0))
                self.sl.setMaximum(kwargs.get("max", 10.0))
                self.sl.setValue(kwargs.get("value", 0.0))
                self.sl.setTickPosition(QtWidgets.QSlider.TicksBothSides)
                self.sl.setTickInterval(1.0)
                self.sl.setSingleStep(kwargs.get("step", 0.1))
                self.sl.valueChanged.connect(self.slider_changed)
                self._lyt.addWidget(self.sl)

                self._field = QtWidgets.QDoubleSpinBox()
                self._field.setMinimum(0.0)
                self._field.setMaximum(100000.0)
                self._field.setSingleStep(kwargs.get("step", 0.1))
                self._field.setValue(kwargs.get("value", 0.0))
                self._field.valueChanged.connect(self.value_changed)
                #self.setToolTip(kwargs.get("tooltip", ""))
                self._lyt.addWidget(self._field)
                self.setLayout(self._lyt)  

            def value_changed(self, val):
                val = self._field.value()
                #self.sl.setValue(val)
                self.update_shader(val)

            def slider_changed(self):
                val = self.sl.value()
                self._field.setValue(val)
                self.update_shader(val)

            def update_shader(self, val):
                if self.light_shader:
                    setattr(self.light_shader, self.param, val) 

        class FloatParam(QtWidgets.QWidget):
            def __init__(self, *args, **kwargs):
                super(FloatParam, self).__init__(parent=kwargs.get("parent", None))
                # build ui
                self._lyt = HBoxLayout()
                self.light_shader = kwargs.get("light_shader", None)
                self.param = kwargs.get("param", "")
                self.param_label = ParamLabel(kwargs.get("label", "label"))
                self._lyt.addWidget(self.param_label)
                self._field = QtWidgets.QDoubleSpinBox()
                self._field.setMinimum(kwargs.get("min", 0.0))
                self._field.setMaximum(kwargs.get("max", 1.0))
                self._field.setSingleStep(kwargs.get("step", 0.1))
                self._field.setValue(kwargs.get("value", 0.0))
                self.setToolTip(kwargs.get("tooltip", ""))
                self._lyt.addWidget(self._field)
                self.setLayout(self._lyt)
                # change cb
                self._field.valueChanged.connect(self.on_change)

            @property
            def value(self):
                return self._field.value

            def on_change(self, val):
                setattr(self.light_shader, self.param, val)        

        class BoolParam(QtWidgets.QWidget):
            def __init__(self, *args, **kwargs):
                super(BoolParam, self).__init__(parent=kwargs.get("parent", None))
                self.light_shader = kwargs.get("light_shader", None)
                self.param = kwargs.get("param", "")
                self.param_label = ParamLabel(kwargs.get("label", "label")) 
                self._lyt = HBoxLayout(m=1, s=1)
                self._lyt.addWidget(self.param_label)
                self._cb = QtWidgets.QCheckBox()
                self._cb.setTristate(False)
                self._cb.setChecked(kwargs.get("value", False))
                self.setToolTip(kwargs.get("tooltip", ""))
                self._lyt.addWidget(self._cb)
                self.setLayout(self._lyt)
                # change cb
                self._cb.stateChanged.connect(self.on_change)

            @property
            def value(self):
                return self._cb.isChecked()

            def setChecked(self, v):
                self._cb.setChecked(v)

            def on_change(self, val):                
                setattr(self.light_shader, self.param, bool(val))

        class ColorButton(QtWidgets.QWidget):
            colorChanged = QtCore.Signal(object)

            def __init__(self, *args, **kwargs):
                super(ColorButton, self).__init__(parent=kwargs.get("parent", None))

                self._lyt = HBoxLayout()
                self.light_shader = kwargs.get("light_shader", None)
                self.param = kwargs.get("param", "")
                self.param_label = ParamLabel(kwargs.get("label", "label"))        
                self._lyt.addWidget(self.param_label)
                self._color = None
                clr = kwargs.get("color", (0.0, 0.0, 0.0))
                self._default = QtGui.QColor.fromRgbF(clr[0], clr[1], clr[2])
                self.color_btn = QtWidgets.QPushButton()
                self.color_btn.pressed.connect(self.onColorPicker)
                self._lyt.addWidget(self.color_btn)
                self.dlg = None

                self.setLayout(self._lyt)  

                self._color = self._default
                self.color_btn.setStyleSheet("background-color: %s;" % self._color.name())

            def setColor(self, qcolor):
                if qcolor != self._color:
                    self._color = qcolor
                    self.colorChanged.emit(qcolor)

                if self._color:
                    self.color_btn.setStyleSheet("background-color: %s;" % qcolor.name())
                else:
                    self.color_btn.setStyleSheet("")

                if self.light_shader:            
                    setattr(self.light_shader, self.param, (qcolor.redF(), qcolor.greenF(), qcolor.blueF()))            

            def color(self):
                return self._color

            def onColorPicker(self):
                if self.dlg is None:
                    self.dlg = QtWidgets.QColorDialog(self)
                    self.dlg.setOption(QtWidgets.QColorDialog.DontUseNativeDialog)
                    self.dlg.currentColorChanged.connect(self.currentColorChanged)
                    self.dlg.accepted.connect(self.dlg_accept)
                    self.dlg.rejected.connect(self.dlg_rejected)

                self.dlg.setCurrentColor(self._color)
                self.dlg.open()
        
            def dlg_accept(self):
                self.setColor(self.dlg.currentColor())

            def dlg_rejected(self):
                self.setColor(self._color)        

            def currentColorChanged(self, qcolor):
                if self.light_shader:
                    setattr(self.light_shader, self.param, (qcolor.redF(), qcolor.greenF(), qcolor.blueF()))

            def mousePressEvent(self, e):
                if e.button() == QtCore.Qt.RightButton:
                    self.setColor(self._default)

                return super(ColorButton, self).mousePressEvent(e)        
            
        class LightMixerWidget(QtWidgets.QWidget):
            def __init__(self, *args, **kwargs):
                super(LightMixerWidget, self).__init__(parent=kwargs.get("parent", None))

                self._lyt = VBoxLayout(m=5)
                self._lyt.setAlignment(QtCore.Qt.AlignTop)
                self._lbl = QtWidgets.QLabel()
                self._lbl.setAlignment(QtCore.Qt.AlignHCenter)
                lbl = kwargs.get("name", "Light")
                self._lbl.setText(lbl)
                self._lyt.addWidget(self._lbl)
                self.setLayout(self._lyt)  

            def __del__(self):
                self.remove_widgets()

            def add_widget(self, wgt):
                self._lyt.addWidget(wgt)

            def remove_widgets(self):
                for i in reversed(range(self._lyt.count())):
                    w = self._lyt.takeAt(i).widget()
                    if w is not None: 
                        w.setParent(None)
                        w.deleteLater()         

        class LightMixerLayout(QtWidgets.QWidget):
            def __init__(self, *args, **kwargs):
                super(LightMixerLayout, self).__init__(parent=kwargs.get("parent", None))

                self.groupbox = QtWidgets.QGroupBox('')
                self._gb_lyt = VBoxLayout()
                self.groupbox.setLayout(self._gb_lyt)
                scroll = QtWidgets.QScrollArea()
                scroll.setWidget(self.groupbox)
                scroll.setWidgetResizable(True)
                self._lyt = VBoxLayout()
                self._lyt.addWidget(scroll)
                self.setLayout(self._lyt)

            def add_widget(self, wgt):
                self._gb_lyt.addWidget(wgt)

            def remove_widgets(self):
                for i in reversed(range(self._gb_lyt.count())):
                    w = self._gb_lyt.takeAt(i).widget()
                    if w is not None: 
                        w.setParent(None)
                        w.deleteLater()        

        class LightMixerQtWrapper(rfb_qt.RmanQtWrapper):
            def __init__(self) -> None:
                super(LightMixerQtWrapper, self).__init__()
            
                self.setWindowTitle('RenderMan Light Mixer')
                self.resize(1100, 500)
                self.buttonBox = QtWidgets.QDialogButtonBox(self)
                self.buttonBox.setGeometry(QtCore.QRect(260, 440, 341, 32))
                self.buttonBox.setOrientation(QtCore.Qt.Horizontal)
                
                # hide OK and cancel buttons
                #self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
                
                self.buttonBox.setObjectName("buttonBox")
                self.addButton = QtWidgets.QPushButton(self)
                self.addButton.setGeometry(QtCore.QRect(280, 30, 31, 26))
                self.addButton.setObjectName("addButton")
                self.addButton.setText("+")
                self.addButton.setAutoDefault(False)
                self.removeButton = QtWidgets.QPushButton(self)
                self.removeButton.setGeometry(QtCore.QRect(280, 50, 31, 26))
                self.removeButton.setObjectName("removeButton")
                self.removeButton.setText("-")
                self.removeButton.setAutoDefault(False)

                self.mixerGroupObjects = QtWidgets.QTreeView(self)
                self.mixerGroupObjects.setHeaderHidden(True)
                self.treeModel = QtGui.QStandardItemModel(self)
                self.rootNode = self.treeModel.invisibleRootItem()
                self.mixerGroupObjects.setModel(self.treeModel)

                self.mixerGroupObjects.setGeometry(QtCore.QRect(30, 140, 250, 350))
                self.mixerGroupObjects.setObjectName("mixerGroupObjects")
                self.mixerGroupObjects.setSelectionMode(
                    QtWidgets.QAbstractItemView.SingleSelection
                )            

                self.mixerGroups = QtWidgets.QListWidget(self)
                self.mixerGroups.setGeometry(QtCore.QRect(30, 30, 256, 80))
                self.mixerGroups.setObjectName("mixerGroups")

                self.label = QtWidgets.QLabel(self)
                self.label.setGeometry(QtCore.QRect(40, 10, 200, 17))
                self.label.setText("Light Mixer Groups")

                self.label_2 = QtWidgets.QLabel(self)
                self.label_2.setGeometry(QtCore.QRect(40, 120, 200, 17))
                self.label_2.setText("Lights")

                self.add_light_btn = QtWidgets.QPushButton(self)
                self.add_light_btn.setGeometry(QtCore.QRect(279, 140, 31, 26))
                self.add_light_btn.setText("+")
                self.add_light_btn.setToolTip("""Add selected lights to this mixer group""" )      
                self.add_light_btn.setEnabled(False) 
                self.add_light_btn.setAutoDefault(False)

                self.remove_light_btn = QtWidgets.QPushButton(self)
                self.remove_light_btn.setGeometry(QtCore.QRect(279, 160, 31, 26))
                self.remove_light_btn.setText("-")
                self.remove_light_btn.setToolTip("""Remove selected lights""" )  
                self.remove_light_btn.setEnabled(False)
                self.remove_light_btn.setAutoDefault(False)     

                self.addButton.clicked.connect(self.add_group)
                self.removeButton.clicked.connect(self.remove_group)
                self.add_light_btn.clicked.connect(self.add_light)
                self.remove_light_btn.clicked.connect(self.remove_light)

                self.mixerGroups.itemChanged.connect(self.mixer_group_changed)
                self.mixerGroups.itemSelectionChanged.connect(self.mixer_groups_index_changed)
                self.mixerGroupObjects.selectionModel().selectionChanged.connect(self.mixer_group_objects_selection)

                self.light_mixer_wgt = LightMixerLayout(parent=self)
                self.light_mixer_wgt.setGeometry(QtCore.QRect(340, 30, 600, 400))

                self.refresh_groups()
                self.mixerGroupObjects.expandAll() 
                self.enableAddLightButton()  

                self.add_handlers()

            def closeEvent(self, event):
                self.remove_handlers()
                super(LightMixerQtWrapper, self).closeEvent(event)

            def add_handlers(self):       
                if self.depsgraph_update_post not in bpy.app.handlers.depsgraph_update_post:
                    bpy.app.handlers.depsgraph_update_post.append(self.depsgraph_update_post)            

            def remove_handlers(self):
                if self.depsgraph_update_post in bpy.app.handlers.depsgraph_update_post:
                    bpy.app.handlers.depsgraph_update_post.remove(self.depsgraph_update_post)             

            def depsgraph_update_post(self, bl_scene, depsgraph):
                for dps_update in reversed(depsgraph.updates):
                    if isinstance(dps_update.id, bpy.types.Collection):
                        self.refresh_group_objects()             
                    elif isinstance(dps_update.id, bpy.types.Scene): 
                        self.enableAddLightButton()

            def enableAddLightButton(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman      
                obs = getattr(context, 'selected_objects', None)
                if obs is None:
                    obs = context.view_layer.objects.selected  
                lights = [ob for ob in obs if ob.type == "LIGHT"]
                if len(lights) > 0:
                    any_lights = []
                    if rm.light_mixer_groups_index > 0:
                        grp = rm.light_mixer_groups[rm.light_mixer_groups_index]
                        for ob in lights:
                            do_add = True
                            for member in grp.members:
                                if member.light_ob == ob:
                                    do_add = False
                                    break
                            if do_add:
                                any_lights.append(ob)

                        self.add_light_btn.setEnabled(len(any_lights) > 0)
                        return
                    self.add_light_btn.setEnabled(True)    
                    return
                self.add_light_btn.setEnabled(False)

            def add_light(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman    

                grp = rm.light_mixer_groups[rm.light_mixer_groups_index]
                obs = getattr(context, 'selected_objects', None)
                if obs is None:
                    obs = context.view_layer.objects.selected              
                for ob in obs:
                    do_add = True
                    for member in grp.members:
                        if member.light_ob == ob:
                            do_add = False
                            break
                    if do_add:
                        ob_in_group = grp.members.add()
                        ob_in_group.name = ob.name
                        ob_in_group.light_ob = ob  

                self.refresh_group_objects()     

            def remove_light(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman
                grp = rm.light_mixer_groups[rm.light_mixer_groups_index]    

                index = self.mixerGroupObjects.selectedIndexes()[0]
                item = index.model().itemFromIndex(index)       
                light_nm = item.text() 
                ob = context.scene.objects.get(light_nm, None)       
                if not ob:
                    return
                
                do_remove = False
                idx = -1
                for i, member in enumerate(grp.members):
                    if ob == member.light_ob:
                        do_remove = True
                        idx = i
                        break         
                if do_remove:            
                    member = grp.members.remove(idx)  

                self.refresh_group_objects()                           
                

            def update(self):
                idx = int(self.mixerGroups.currentRow())
                self.addButton.setEnabled(True)

                super(LightMixerQtWrapper, self).update()

            def refresh_groups(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman
                self.mixerGroups.clear()
                for grp in rm.light_mixer_groups:
                    item = QtWidgets.QListWidgetItem(grp.name)
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                    self.mixerGroups.addItem(item)

                if self.mixerGroups.count() > 0:
                    self.mixerGroups.setCurrentRow(rm.light_mixer_groups_index)
                    
            def add_group(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman    

                grp = rm.light_mixer_groups.add()
                grp.name = 'mixerGroup_%d' % len(rm.light_mixer_groups)
                rm.light_mixer_groups_index = len(rm.light_mixer_groups)-1
                self.refresh_groups()

            def remove_group(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman    

                index = rm.object_groups_index
                group = rm.object_groups[index]            
                # get a list of all objects in this group
                ob_list = [member.ob_pointer for member in group.members]
                rm.object_groups.remove(index)
                rm.object_groups_index -= 1

                # now tell each object to update
                for ob in ob_list:
                    ob.update_tag(refresh={'OBJECT'})

                self.refresh_groups()       

            def mixer_group_changed(self, item):
                idx = int(self.mixerGroups.currentRow())

                context = bpy.context
                scene = context.scene
                rm = scene.renderman
                grp = rm.light_mixer_groups[idx]
                grp.name = item.text()    
                self.label_2.setText("Objects (%s)" % item.text())
                for member in grp.members:
                    ob = member.light_ob
                    ob.update_tag(refresh={'OBJECT'})        

            def find_item(self, standard_item, ob):           
                for i in range(0, standard_item.rowCount()):
                    item = standard_item.child(i)
                    if item.text() == ob.name:
                        return item                
                
                return None
                
            def refresh_group_objects(self):
                self.light_mixer_wgt.remove_widgets()        
                idx = int(self.mixerGroups.currentRow())
                if idx == -1:
                    self.label_2.setText("Objects (no group selected)")
                    

                context = bpy.context
                scene = context.scene
                rm = scene.renderman    

                grp = rm.light_mixer_groups[rm.light_mixer_groups_index]
                
                self.treeModel.clear()
                self.rootNode = self.treeModel.invisibleRootItem()

                for member in grp.members:
                    ob = member.light_ob
                    
                    light_shader = shadergraph_utils.get_light_node(ob) 
                    item = StandardItem(txt=ob.name)            
                    self.rootNode.appendRow(item)

                    lgt_mixer_wgt = LightMixerWidget(parent=self, name=ob.name)

                    if light_shader.bl_label == 'PxrPortalLight':
                        enableTemperature = BoolParam(parent=self,
                                                param="enableTemperature",
                                                label="Enable Temperature",
                                                value=light_shader.enableTemperature,
                                                light_shader=light_shader
                                                )
                        lgt_mixer_wgt.add_widget(enableTemperature)

                        temperature = FloatParam(parent=self,
                                                param="temperature",
                                                label="Temperature",
                                                min=1000.0,
                                                max=50000.0,
                                                value=light_shader.temperature,
                                                light_shader=light_shader
                                                )
                        lgt_mixer_wgt.add_widget(temperature)      

                        wgt = SliderParam(parent=self, 
                                    light_shader=light_shader,
                                    value=light_shader.intensityMult,
                                    min=0.0,
                                    max=10.0,
                                    param="intensityMult", 
                                    label="Intensity Mult")
                        lgt_mixer_wgt.add_widget(wgt)
                                                            

                    else:
                        exposure_wgt = SliderParam(parent=self, 
                                    light_shader=light_shader,
                                    value=light_shader.exposure,
                                    min=0.0,
                                    max=10.0,
                                    param="exposure", 
                                    label="Exposure")
                        lgt_mixer_wgt.add_widget(exposure_wgt)                
                    
                        wgt = SliderParam(parent=self, 
                                    light_shader=light_shader,
                                    value=light_shader.intensity,
                                    min=0.0,
                                    max=10.0,
                                    param="intensity", 
                                    label="Intensity")
                        lgt_mixer_wgt.add_widget(wgt)
                                        
                        if light_shader.bl_label == 'PxrEnvDayLight':
                            color_picker = ColorButton(parent=self, 
                                                    color=light_shader.skyTint,
                                                    param="skyTint",
                                                    label="Sky Tint",
                                                    light_shader=light_shader
                                                    )
                            lgt_mixer_wgt.add_widget(color_picker)
                        else:
                            enableTemperature = BoolParam(parent=self,
                                                    param="enableTemperature",
                                                    label="Enable Temperature",
                                                    value=light_shader.enableTemperature,
                                                    light_shader=light_shader
                                                    )
                            lgt_mixer_wgt.add_widget(enableTemperature)

                            temperature = FloatParam(parent=self,
                                                    param="temperature",
                                                    label="Temperature",
                                                    min=1000.0,
                                                    max=50000.0,
                                                    value=light_shader.temperature,
                                                    light_shader=light_shader
                                                    )
                            lgt_mixer_wgt.add_widget(temperature)                    

                            color_picker = ColorButton(parent=self, 
                                                    color=light_shader.lightColor,
                                                    param="lightColor",
                                                    label="Light Color",
                                                    light_shader=light_shader
                                                    )
                            
                            lgt_mixer_wgt.add_widget(color_picker)

                    self.light_mixer_wgt.add_widget(lgt_mixer_wgt)    

                self.mixerGroupObjects.expandAll()                                     

            def mixer_groups_index_changed(self):
                idx = int(self.mixerGroups.currentRow())
                current_item = self.mixerGroups.currentItem()
                if current_item:
                    self.label_2.setText("Lights (%s)" % current_item.text())
                else:
                    return
                context = bpy.context
                scene = context.scene
                rm = scene.renderman               
                rm.light_mixer_groups_index = idx   

                self.refresh_group_objects()
                        
            def mixer_group_objects_selection(self, selected, deselected):
                idx = int(self.mixerGroups.currentRow())
                current_item = self.mixerGroups.currentItem()
                if not current_item:
                    self.remove_light_btn.setEnabled(False)
                    return
                self.remove_light_btn.setEnabled(True)
'''
class RENDERMAN_UL_LightMixer_Group_Members_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        light = item.light_ob
        layout.context_pointer_set("selected_light", light)        
        op = layout.operator('renderman.remove_light_from_light_mixer_group', text='', icon='REMOVE')
   
        light_shader = shadergraph_utils.get_light_node(light)
        if not light_shader:
            layout.label(text=light.name)
            layout.label(text='NO LIGHT SHADER')
            return 

        icon = rfb_icons.get_light_icon(light_shader.bl_label)
        op.group_index = rm.light_mixer_groups_index
        layout.label(text=light.name, icon_value=icon.icon_id)

        light_rm = shadergraph_utils.get_rman_light_properties_group(light)
        if light_shader.bl_label == 'PxrPortalLight':
            layout.prop(light_shader, 'enableTemperature', text='Temp')
            if light_shader.enableTemperature:
                layout.prop(light_shader, 'temperature', text='', slider=True)
            else:
                layout.prop(light_shader, 'tint', text='')        
            layout.prop(light_shader, 'intensityMult', slider=True)                
        else:
            if light_shader.bl_label == 'PxrEnvDayLight':
                layout.prop(light_shader, 'skyTint', text='')
            else:
                layout.prop(light_shader, 'enableTemperature', text='Temp')
                if light_shader.enableTemperature:
                    layout.prop(light_shader, 'temperature', text='', slider=True)
                else:
                    layout.prop(light_shader, 'lightColor', text='')
            layout.prop(light_shader, 'intensity', slider=True)
            layout.prop(light_shader, 'exposure', slider=True)        
        solo_icon = 'LIGHT'        
        if light.renderman.solo:
            solo_icon = 'OUTLINER_OB_LIGHT'
        layout.prop(light.renderman, 'solo', text='', icon=solo_icon, icon_only=True, emboss=False )
        mute_icon = 'HIDE_OFF'
        if light.renderman.mute:
            mute_icon = 'HIDE_ON'
        layout.prop(light.renderman, 'mute', text='', icon=mute_icon, icon_only=True, emboss=False)

class PRMAN_OT_Renderman_Open_Light_Mixer_Editor(CollectionPanel, bpy.types.Operator):

    bl_idname = "scene.rman_open_light_mixer_editor"
    bl_label = "RenderMan Light Mixer Editor"

    def updated_light_selected_name(self, context):
        light_ob = context.scene.objects.get(self.selected_light_name, None)
        if not light_ob:
            return
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        light_ob.select_set(True)
        context.view_layer.objects.active = light_ob   

    def light_list_items(self, context):
        pattern = re.compile(self.light_search_filter)   
        scene = context.scene
        rm = scene.renderman

        if self.do_light_filter and self.light_search_filter == '':
            return return_empty_list(label='No Lights Found')

        group_index = rm.light_mixer_groups_index
        lights_in_group = []
        object_groups = rm.light_mixer_groups
        object_group = object_groups[group_index]
        lights_in_group = [member.light_ob.name for member in object_group.members]        

        items = []
        for light in scene_utils.get_all_lights(context.scene, include_light_filters=False):
            if light.name not in lights_in_group:
                if self.do_light_filter and not re.match(pattern, light.name):
                    continue
                items.append((light.name, light.name, ''))
        if not items:
            return return_empty_list(label='No Lights Found') 
        elif self.do_light_filter:
            items.insert(0, ('0', 'Results (%d)' % len(items), '', '', 0))
        else:
            items.insert(0, ('0', 'Select Light', '', '', 0))                  
        return items

    def update_do_light_filter(self, context):
        self.selected_light_name = '0'

    selected_light_name: EnumProperty(name="Light", items=light_list_items, update=updated_light_selected_name)
    light_search_filter: StringProperty(name="Light Filter Search", default="")
    do_light_filter: BoolProperty(name="Filter", 
                                description="Search and add multiple lights",
                                default=False,
                                update=update_do_light_filter)    

    def check_light_mixer_links(self, context):
        scene = context.scene
        rm = scene.renderman
        
        for lg in rm.light_mixer_groups:
            delete_objs = []
            for j in range(len(lg.members)-1, -1, -1):
                member = lg.members[j]
                if member.light_ob is None or member.light_ob.name not in scene.objects:
                    delete_objs.insert(0, j)
            for j in delete_objs:
                lg.members.remove(j)
                lg.members_index -= 1                             

    def execute(self, context):
        self.check_light_mixer_links(context)
        return{'FINISHED'}         

    def cancel(self, context):
        if self.event and self.event.type == 'LEFTMOUSE':
            bpy.ops.scene.rman_open_light_mixer_editor('INVOKE_DEFAULT')
        else:
            self.check_light_mixer_links(context)
            
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = None         

    def invoke(self, context, event):
        '''
        if using_qt() and show_wip_qt():
            global __LIGHT_MIXER_WINDOW__
            if RFB_PLATFORM == "macOS":
                rfb_qt.run_with_timer(__LIGHT_MIXER_WINDOW__, LightMixerQtWrapper)   
            else:
                bpy.ops.wm.light_mixer_qt_app_timed()     

            return {'FINISHED'}       
        '''

        wm = context.window_manager
        width = rfb_config['editor_preferences']['lightmixer_editor']['width']
        self.event = event
        self.check_light_mixer_links(context)
        return wm.invoke_props_dialog(self, width=width)         

    def draw(self, context):
        layout = self.layout
        scene = context.scene
        rm = scene.renderman
        self._draw_collection(context, layout, rm, "Light Mixer Groups",
                              "collection.add_remove",
                              "scene.renderman",
                              "light_mixer_groups", "light_mixer_groups_index", 
                              default_name='mixerGroup_%d' % len(rm.light_mixer_groups))

    def draw_item(self, layout, context, item):
        scene = context.scene
        rm = scene.renderman
        light_group = rm.light_mixer_groups[rm.light_mixer_groups_index]

        lights = [member.light_ob for member in light_group.members]
        row = layout.row(align=True)
        row.separator()        

        box = layout.box()
        row = box.row()
        split = row.split(factor=0.25)
        row = split.row()
        row.prop(self, 'do_light_filter', text='', icon='FILTER', icon_only=True)
        if not self.do_light_filter:
            row.prop(self, 'selected_light_name', text='')
            col = row.column()            
            if self.selected_light_name == '0' or self.selected_light_name == '':
                col.enabled = False
                op = col.operator("renderman.add_light_to_light_mixer_group", text='', icon='ADD')
                op.open_editor = False
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_light', bpy.data.objects[self.selected_light_name])
                op = col.operator("renderman.add_light_to_light_mixer_group", text='', icon='ADD')
                op.do_scene_selected = False
                op.open_editor = False
        else:
            row.prop(self, 'light_search_filter', text='', icon='VIEWZOOM')
            row = box.row()
            split = row.split(factor=0.25)
            row = split.row()
            row.prop(self, 'selected_light_name', text='')
            col = row.column()
            if self.selected_light_name == '0' or self.selected_light_name == '':
                col.enabled = False
                op = col.operator("renderman.add_light_to_light_mixer_group", text='', icon='ADD')
                op.open_editor = False
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_light', bpy.data.objects[self.selected_light_name])
                op = col.operator("renderman.add_light_to_light_mixer_group", text='', icon='ADD')
                op.do_scene_selected = False
                op.open_editor = False
        row = layout.row()
        split = row.split(factor=0.25)
        op = split.operator('renderman.convert_mixer_group_to_light_group', text='Convert to Light Group')
        op.group_index = rm.light_mixer_groups_index

        layout.template_list("RENDERMAN_UL_LightMixer_Group_Members_List", "Renderman_light_mixer_list",
                            light_group, "members", light_group, 'members_index', rows=6)

classes = [
    PRMAN_OT_Renderman_Open_Light_Mixer_Editor, 
    RENDERMAN_UL_LightMixer_Group_Members_List
]

# if not bpy.app.background and rfb_qt:
#    classes.append(LightMixerQtAppTimed)

def register():
    from ...rfb_utils import register_utils

    register_utils.rman_register_classes(classes)

def unregister():
    from ...rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)                                 