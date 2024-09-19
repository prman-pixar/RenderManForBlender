from bpy.props import (StringProperty, BoolProperty, EnumProperty)

from ...rfb_utils import scene_utils
from ...rfb_utils import shadergraph_utils
from ...rfb_utils import string_utils
from ...rfb_utils import scenegraph_utils
from ...rfb_logger import rfb_log
from ...rfb_utils.prefs_utils import get_pref, using_qt, show_wip_qt
from ...rfb_utils import object_utils
from ...rfb_utils.envconfig_utils import envconfig
from ... import rfb_icons
from ...rman_operators.rman_operators_collections import return_empty_list   
from ...rman_config import __RFB_CONFIG_DICT__ as rfb_config
from ...rman_constants import RFB_ADDON_PATH
import bpy
import os
import re
import sys


__LIGHT_LINKING_WINDOW__ = None 
'''
if not bpy.app.background:
    try:
        from ...rman_ui import rfb_qt as rfb_qt
        from rman_utils.vendor.Qt import QtCore, QtWidgets, QtGui 
    except:
        rfb_qt = None

    if rfb_qt:
        class LightLinkingQtAppTimed(rfb_qt.RfbBaseQtAppTimed):
            bl_idname = "wm.light_linking_qt_app_timed"
            bl_label =  "Light Linking Editor"

            def __init__(self):
                super(LightLinkingQtAppTimed, self).__init__()

            def execute(self, context):
                self._window = LightLinkingQtWrapper()
                return super(LightLinkingQtAppTimed, self).execute(context)

        class StandardItem(QtGui.QStandardItem):
            def __init__(self, txt=''):
                super().__init__()
                self.setEditable(False)
                self.setText(txt)

        class LightLinkingQtWrapper(rfb_qt.RmanQtWrapper):
            def __init__(self) -> None:
                super(LightLinkingQtWrapper, self).__init__()
                self.setObjectName("Dialog")
                self.resize(825, 526)
                self.buttonBox = QtWidgets.QDialogButtonBox(self)
                self.buttonBox.setGeometry(QtCore.QRect(620, 450, 166, 24))
                
                # hide OK, and cancel buttons
                #self.buttonBox.setStandardButtons(QtWidgets.QDialogButtonBox.Cancel|QtWidgets.QDialogButtonBox.Ok)
                
                self.buttonBox.setObjectName("buttonBox")
                #self.invert_checkBox = QtWidgets.QCheckBox(self)
                #self.invert_checkBox.setGeometry(QtCore.QRect(730, 30, 85, 21))
                #self.invert_checkBox.setObjectName("invert_checkBox")
                self.widget = QtWidgets.QWidget(self)
                self.widget.setGeometry(QtCore.QRect(40, 70, 751, 361))
                self.widget.setObjectName("widget")
                self.gridLayout = QtWidgets.QGridLayout(self.widget)
                self.gridLayout.setContentsMargins(0, 0, 0, 0)
                self.gridLayout.setHorizontalSpacing(50)
                self.gridLayout.setObjectName("gridLayout")
                self.verticalLayout = QtWidgets.QVBoxLayout()
                self.verticalLayout.setObjectName("verticalLayout")
                self.lights_label = QtWidgets.QLabel(self.widget)
                self.lights_label.setObjectName("lights_label")
                self.verticalLayout.addWidget(self.lights_label)
                self.lights_treeView = QtWidgets.QListWidget(self)
                self.lights_treeView.setObjectName("lights_treeView")
                self.verticalLayout.addWidget(self.lights_treeView)
                self.gridLayout.addLayout(self.verticalLayout, 0, 0, 1, 1)
                self.verticalLayout_2 = QtWidgets.QVBoxLayout()
                self.verticalLayout_2.setObjectName("verticalLayout_2")
                self.objects_label = QtWidgets.QLabel(self.widget)
                self.objects_label.setObjectName("objects_label")
                self.verticalLayout_2.addWidget(self.objects_label)

                self.objects_treeView = QtWidgets.QTreeView(self.widget)
                self.objects_treeView.setSelectionMode(
                    QtWidgets.QAbstractItemView.MultiSelection
                )               
                self.objects_treeView.setObjectName("objects_treeView")
                self.objects_treeView.setHeaderHidden(True)
                self.treeModel = QtGui.QStandardItemModel(self)
                self.rootNode = self.treeModel.invisibleRootItem()
                self.objects_treeView.setModel(self.treeModel)

                self.verticalLayout_2.addWidget(self.objects_treeView)
                self.gridLayout.addLayout(self.verticalLayout_2, 0, 1, 1, 1)

                self.lights_treeView.itemSelectionChanged.connect(self.lights_index_changed)            

                self.objects_treeView.selectionModel().selectionChanged.connect(self.linked_objects_selection)            

                self.light_link_item = None
                self.total_objects = 0
                self.retranslateUi()
                self.refresh_lights()

                self.add_handlers()


            def retranslateUi(self):
                _translate = QtCore.QCoreApplication.translate
                self.setWindowTitle(_translate("Dialog", "Light Linking"))
                #self.invert_checkBox.setToolTip(_translate("Dialog", "Invert light linking"))
                #self.invert_checkBox.setText(_translate("Dialog", "Invert"))
                self.lights_label.setText(_translate("Dialog", "Lights"))
                self.objects_label.setText(_translate("Dialog", "Objects"))       

            def closeEvent(self, event):
                self.remove_handlers()
                super(LightLinkingQtWrapper, self).closeEvent(event)

            def add_handlers(self):       
                if self.depsgraph_update_post not in bpy.app.handlers.depsgraph_update_post:
                    bpy.app.handlers.depsgraph_update_post.append(self.depsgraph_update_post)            

            def remove_handlers(self):
                if self.depsgraph_update_post in bpy.app.handlers.depsgraph_update_post:
                    bpy.app.handlers.depsgraph_update_post.remove(self.depsgraph_update_post)             

            def depsgraph_update_post(self, bl_scene, depsgraph):
                for dps_update in reversed(depsgraph.updates):
                    if isinstance(dps_update.id, bpy.types.Collection):
                        self.refresh_lights()
                        self.refresh_linked_objects()
                        #self.lights_index_changed()
                    #elif isinstance(dps_update.id, bpy.types.Scene):
                    #    self.refresh_lights()                    
            
            def update(self):
                super(LightLinkingQtWrapper, self).update()


            def refresh_lights(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman
                
                all_lights = [l.name for l in scene_utils.get_all_lights(scene, include_light_filters=True)]
                remove_items = []

                for i in range(self.lights_treeView.count()):
                    item = self.lights_treeView.item(i)
                    name = item.text()
                    if name not in all_lights:
                        remove_items.append(item)
                    else:
                        all_lights.remove(name)

                for nm in all_lights:
                    item = QtWidgets.QListWidgetItem(nm)
                    ob = scene.objects[nm]
                    light_shader_name = ob.data.renderman.get_light_node_name()
                    icon_path = os.path.join(RFB_ADDON_PATH, 'rfb_icons/out_%s.png' % light_shader_name)
                    if os.path.exists(icon_path):
                        icon = QtGui.QIcon(icon_path)
                        item.setIcon(icon)
                    item.setFlags(item.flags())
                    self.lights_treeView.addItem(item)

                for item in remove_items:
                    self.lights_treeView.takeItem(self.lights_treeView.row(item))
                    del item

                if remove_items or len(all_lights) > 0:
                    self.lights_treeView.setCurrentRow(-1)   

            def find_light_link_item(self, light_nm=''):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman     
                light_link_item = None   
                for ll in rm.light_links:
                    if ll.light_ob.name == light_nm:
                        light_link_item = ll
                        break
                return light_link_item   

            def get_all_object_items(self, standard_item, items):
                for i in range(standard_item.rowCount()):
                    item = standard_item.child(i)
                    items.append(item)
                    if item.rowCount() > 0:
                        self.get_all_object_items(item, items)       

            def bl_select_objects(self, obs):
                context = bpy.context
                for ob in getattr(context, "selected_objects", list()):
                    ob.select_set(False)
                for ob in obs:
                    ob.select_set(True)
                    context.view_layer.objects.active = ob                     

            def lights_index_changed(self):
                idx = int(self.lights_treeView.currentRow())
                current_item = self.lights_treeView.currentItem()
                if not current_item:               
                    self.treeModel.clear()
                    self.objects_treeView.selectionModel().select(QtCore.QItemSelection(), QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.NoUpdate)
                    return
                self.rootNode = self.treeModel.invisibleRootItem()   
                if self.rootNode.rowCount() == 0:
                    self.refresh_linked_objects()
                context = bpy.context
                scene = context.scene
                rm = scene.renderman     
                rm.light_links_index = idx
                light_nm = current_item.text() 
                light_ob = context.scene.objects.get(light_nm, None)
                if light_ob:
                    self.bl_select_objects([light_ob])

                light_link_item = self.find_light_link_item(light_nm)   
                selected_items =  QtCore.QItemSelection()
                items = []
                self.get_all_object_items(self.rootNode, items)               

                if light_link_item is None:
                    
                    #if not object_utils.is_light_filter(light_ob):
                    #    light_link_item = scene.renderman.light_links.add()
                    #    light_link_item.name = light_ob.name
                    #    light_link_item.light_ob = light_ob
                                
                    for item in items:
                        idx = self.treeModel.indexFromItem(item)
                        selection_range = QtCore.QItemSelectionRange(idx)
                        selected_items.append(selection_range)
                else:            
                    for item in items:
                        idx = self.treeModel.indexFromItem(item)
                        ob_nm = item.text()
                        found = False
                        for member in light_link_item.members:
                            ob = member.ob_pointer
                            if ob is None:
                                continue
                            if ob.name == ob_nm:
                                found = True
                                break

                        if found:
                            continue

                        selection_range = QtCore.QItemSelectionRange(idx)
                        selected_items.append(selection_range)
                self.objects_treeView.selectionModel().select(selected_items, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.NoUpdate)

            def find_item(self, standard_item, ob):        
                for i in range(0, standard_item.rowCount()):
                    item = standard_item.child(i)
                    if not item:
                        continue
                    if item.text() == ob.name:
                        return item          
                    if item.rowCount() > 0:
                        return self.find_item(item, ob)      
                
                return None

            def get_all_removed_items(self, standard_item, scene, remove_items):
                for i in range(0, standard_item.rowCount()):
                    item = standard_item.child(i)
                    if not item:
                        continue
                    nm = item.text()
                    if nm not in scene.objects:
                        remove_items.append(item)
                    if item.rowCount() > 0:
                        self.get_all_removed_items(item, scene, remove_items)

                
            def refresh_linked_objects(self):
                context = bpy.context
                scene = context.scene
                self.rootNode = self.treeModel.invisibleRootItem()

                def add_children(root_item, ob):
                    for child in ob.children:
                        if child.type in ['CAMERA', 'LIGHT', 'ARMATURE']:
                            continue
                        item = self.find_item(root_item, child)
                        if not item:
                            item = StandardItem(txt=child.name)
                        self.total_objects += 1
                        root_item.appendRow(item)
                        if len(child.children) > 0:
                            add_children(item, child)

                remove_items = []
                self.get_all_removed_items(self.rootNode, scene, remove_items)

                for item in remove_items:
                    self.treeModel.takeRow(item.row())
                    self.total_objects -= 1
                    del item
                
                root_parents = [ob for ob in scene.objects if ob.parent is None]            
                for ob in root_parents:           
                    if ob.type in ['CAMERA', 'LIGHT', 'ARMATURE']:
                        continue     
                    item = self.find_item(self.rootNode, ob)
                    if not item:
                        item = StandardItem(txt=ob.name)
                        self.total_objects += 1
                        self.rootNode.appendRow(item)
                    if len(ob.children) > 0:
                        add_children(item, ob)

                self.objects_treeView.expandAll()

            def linked_objects_selection(self, selected, deselected):
                idx = int(self.lights_treeView.currentRow())
                current_item = self.lights_treeView.currentItem()
                if not current_item:
                    return
                context = bpy.context
                scene = context.scene
                rm = scene.renderman
                light_nm = current_item.text() 
                light_ob = context.scene.objects.get(light_nm, None)           
                light_props = shadergraph_utils.get_rman_light_properties_group(light_ob.original)
                is_light_filter =  light_props.renderman_light_role == 'RMAN_LIGHTFILTER'
                ll = self.find_light_link_item(light_nm)  

                if ll is None:
                    ll = scene.renderman.light_links.add()
                    ll.name = light_ob.name
                    ll.light_ob = light_ob          
                    rm.lights_link_index = len(rm.light_links)-1           

                if is_light_filter:
                    # linkingGroups should only be set if one of the items is deselected
                    total_selected_items = len(self.objects_treeView.selectionModel().selectedIndexes())
                    
                    if total_selected_items == self.total_objects and light_props.linkingGroups != "":
                        light_props.linkingGroups = ""
                        light_ob.update_tag(refresh={'DATA'})
                    elif total_selected_items != self.total_objects and light_props.linkingGroups == "":
                        light_props.linkingGroups = string_utils.sanitize_node_name(light_ob.name_full)
                        light_ob.update_tag(refresh={'DATA'})

                for i in deselected.indexes():
                    item = self.objects_treeView.model().itemFromIndex(i)
                    ob = bpy.data.objects.get(item.text(), None)
                    if ob is None:
                        continue
                    do_add = True
                    for member in ll.members:            
                        if ob == member.ob_pointer:
                            do_add = False
                            break         

                    if do_add:            
                        member = ll.members.add()
                        member.name = ob.name
                        member.ob_pointer = ob
                        member.illuminate = 'OFF'     
                        scene_utils.set_lightlinking_properties(ob, light_ob, member.illuminate)

                for i in selected.indexes():
                    item = self.objects_treeView.model().itemFromIndex(i)
                    ob = bpy.data.objects.get(item.text(), None)
                    if ob is None:
                        continue
                    do_remove = False
                    idx = -1
                    for i, member in enumerate(ll.members):
                        if ob == member.ob_pointer:
                            do_remove = True
                            idx = i
                            break         
                    if do_remove:            
                        member = ll.members.remove(idx)                                   
                        scene_utils.set_lightlinking_properties(ob, light_ob, '')
'''
class RENDERMAN_UL_LightLink_Light_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        scene = context.scene
        rm = scene.renderman
        op = layout.operator("renderman.remove_light_link", text='', icon='REMOVE') 
        op.group_index = index
        light = item.light_ob
        if light is None or light.name not in scene.objects:
            layout.label(text="%s no longer exists" % item.name)
            return
        light_shader = shadergraph_utils.get_light_node(light) 
        if light_shader:     
            icon = rfb_icons.get_light_icon(light_shader.bl_label)        
            label = light.name
            layout.label(text=label, icon_value=icon.icon_id)     
        else:
            label = light.name
            layout.label(text=label, icon='LIGHT')

class RENDERMAN_UL_LightLink_Object_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rm = context.scene.renderman
        custom_icon = 'OBJECT_DATAMODE'
        layout.context_pointer_set("selected_obj", item.ob_pointer)
        op = layout.operator('renderman.remove_light_link_object', text='', icon='REMOVE')    
        label = item.ob_pointer.name
        layout.label(text=label, icon=custom_icon)

class PRMAN_PT_Renderman_Open_Light_Linking(bpy.types.Operator):

    bl_idname = "scene.rman_open_light_linking"
    bl_label = "RenderMan Light Linking Editor"

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
        
        lights_in_group = []
        for lg in rm.light_links:
            if lg.light_ob and lg.light_ob.name in scene.objects:
                lights_in_group.append(lg.light_ob.name)

        items = []
        light_items = list()
        lightfilter_items = list()

        for light in scene_utils.get_all_lights(context.scene, include_light_filters=True):
            light_props = shadergraph_utils.get_rman_light_properties_group(light)            
            is_light = (light_props.renderman_light_role == 'RMAN_LIGHT')            
            if light.name not in lights_in_group:
                if self.do_light_filter and not re.match(pattern, light.name):
                    continue    
                if is_light:
                    light_items.append((light.name, light.name, '',))
                else:
                    lightfilter_items.append((light.name, light.name, ''))        
        if light_items:            
            items.extend(light_items)
        if lightfilter_items:           
            items.extend(lightfilter_items)
        if not items:
            return return_empty_list(label='No Lights Found') 
        elif self.do_light_filter:
            items.insert(0, ('0', 'Results (%d)' % len(items), '', '', 0))
        else:
            items.insert(0, ('0', 'Select Light', '', '', 0))                  
        return items    

    def update_do_light_filter(self, context):
        self.selected_light_name = '0'

    def updated_object_selected_name(self, context):
        ob = context.scene.objects.get(self.selected_obj_name, None)
        if not ob:
            return
                
        if context.view_layer.objects.active:
            context.view_layer.objects.active.select_set(False)
        ob.select_set(True)
        context.view_layer.objects.active = ob             

    def obj_list_items(self, context):
        pattern = re.compile(self.object_search_filter)
        scene = context.scene
        rm = scene.renderman

        if self.do_object_filter and self.object_search_filter == '':
            return return_empty_list(label='No Objects Found')        

        group = rm.light_links[rm.light_links_index]

        objs_in_group = []
        for member in group.members:
            objs_in_group.append(member.ob_pointer.name)

        items = []
        for ob in [ob for ob in context.scene.objects if ob.type not in ['LIGHT', 'CAMERA']]:   
            if shadergraph_utils.is_mesh_light(ob):
                continue
            ob_name = ob.name   
            if ob_name not in objs_in_group:
                if self.do_object_filter and not re.match(pattern, ob_name):
                    continue  
                items.append((ob_name, ob_name, ''))
        if not items:
            return return_empty_list(label='No Objects Found')               
        elif self.do_object_filter:
            items.insert(0, ('0', 'Results (%d)' % len(items), '', '', 0))
        else:
            items.insert(0, ('0', 'Select Object', '', '', 0))
        return items       

    def update_do_object_filter(self, context):
        self.selected_obj_name = '0'

    light_search_filter: StringProperty(name="Light Filter Search", default="")
    do_light_filter: BoolProperty(name="Filter", 
                                description="Search and add multiple lights",
                                default=False, update=update_do_light_filter)
    selected_light_name: EnumProperty(name="", items=light_list_items, update=updated_light_selected_name)
    do_object_filter: BoolProperty(name="Object Filter", 
                                description="Search and add multiple objects",
                                default=False,
                                update=update_do_object_filter)    

    object_search_filter: StringProperty(name="Object Filter Search", default="")        

    selected_obj_name: EnumProperty(name="", items=obj_list_items, update=updated_object_selected_name)                   

    def execute(self, context):
        self.check_light_links(context)
        return{'FINISHED'}         

    def draw(self, context):
        layout = self.layout        
        scene = context.scene
        rm = scene.renderman
        row = layout.row()

        flow = row.column_flow(columns=3)
        row = flow.row()
        row.prop(self, 'do_light_filter', text='', icon='FILTER', icon_only=True)
        if not self.do_light_filter:
            row.prop(self, 'selected_light_name', text='')
            col = row.column()            
            if self.selected_light_name == '0' or self.selected_light_name == '':
                col.enabled = False                
                op = col.operator("renderman.add_light_link", text='', icon='ADD')
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_light', bpy.data.objects[self.selected_light_name])
                op = col.operator("renderman.add_light_link", text='', icon='ADD')
        else:
            row.prop(self, 'light_search_filter', text='', icon='VIEWZOOM')  
            row = layout.row()             
            flow = row.column_flow(columns=3)
            row = flow.row()

            row.prop(self, 'selected_light_name', text='')
            col = row.column()
            if self.selected_light_name == '0' or self.selected_light_name == '':
                col.enabled= False
                op = col.operator("renderman.add_light_link", text='', icon='ADD')
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_light', bpy.data.objects[self.selected_light_name])
                op = col.operator("renderman.add_light_link", text='', icon='ADD')

        flow.label(text='')

        row = layout.row()
        if not rm.invert_light_linking:
            flow = row.column_flow(columns=3)
        else:
            flow = row.column_flow(columns=2)

        flow.label(text='Lights')
        flow.label(text='Objects')
        if not rm.invert_light_linking:
            flow.label(text='Illumination')

        row = layout.row()
        if not rm.invert_light_linking:
            flow = row.column_flow(columns=3)
        else:
            flow = row.column_flow(columns=2)

        flow.template_list("RENDERMAN_UL_LightLink_Light_List", "Renderman_light_link_list",
                            scene.renderman, "light_links", rm, 'light_links_index', rows=6)

        if rm.light_links_index != -1:
            light_link_item = scene.renderman.light_links[rm.light_links_index]  
            row = flow.row()   
            light_props = shadergraph_utils.get_rman_light_properties_group(light_link_item.light_ob)
            is_rman_light = (light_props.renderman_light_role in ['RMAN_LIGHT', 'RMAN_LIGHTFILTER'])
            row.prop(self, 'do_object_filter', text='', icon='FILTER', icon_only=True)
            if not self.do_object_filter:
                row.prop(self, 'selected_obj_name', text='')
                col = row.column()
                if self.selected_obj_name == '0' or self.selected_obj_name == '':
                    col.enabled = False
                    op = col.operator("renderman.add_light_link_object", text='', icon='ADD')                    
                else:
                    col.context_pointer_set('op_ptr', self) 
                    col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])
                    op = col.operator("renderman.add_light_link_object", text='', icon='ADD')
                    op.do_scene_selected = False

                flow.template_list("RENDERMAN_UL_LightLink_Object_List", "Renderman_light_link_list",
                                light_link_item, "members", light_link_item, 'members_index', rows=5)            
            else:
                row.prop(self, 'object_search_filter', text='', icon='VIEWZOOM')
                row = flow.row()  
                row.prop(self, 'selected_obj_name')
                col = row.column()                
                if self.selected_obj_name == '0' or self.selected_obj_name == '':
                    col.enabled = False                    
                    op = col.operator("renderman.add_light_link_object", text='', icon='ADD')                
                else:
                    col.context_pointer_set('op_ptr', self) 
                    col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])
                    op = col.operator("renderman.add_light_link_object", text='', icon='ADD')     
                    op.do_scene_selected = False           

                flow.template_list("RENDERMAN_UL_LightLink_Object_List", "Renderman_light_link_list",
                                light_link_item, "members", light_link_item, 'members_index', rows=4)                                          
      
            if not rm.invert_light_linking:
                col = flow.column()
                if is_rman_light and len(light_link_item.members) > 0:
                    member = light_link_item.members[light_link_item.members_index]
                    col.context_pointer_set('light_ob', light_link_item.light_ob) 
                    col.prop(member, 'illuminate', text='')        

    def cancel(self, context):
        if self.event and self.event.type == 'LEFTMOUSE':
            bpy.ops.scene.rman_open_light_linking('INVOKE_DEFAULT')
        else:
            self.check_light_links(context)
            
    def __init__(self):
        self.event = None     

    def check_light_links(self, context):
        scene = context.scene
        rm = scene.renderman
        delete_any = []
        for i in range(len(rm.light_links)-1, -1, -1):
            lg = rm.light_links[i]
            if lg.light_ob is None or lg.light_ob.name not in scene.objects:
                delete_any.insert(0, i)
                continue

            if object_utils.is_light_filter(lg.light_ob): 
                if lg.light_ob.data.renderman.linkingGroups == "":
                    lg.light_ob.data.renderman.linkingGroups = string_utils.sanitize_node_name(lg.light_ob.name_full)
                else:
                    lg.light_ob.data.renderman.linkingGroups = ""

            delete_objs = []
            for j in range(len(lg.members)-1, -1, -1):
                member = lg.members[j]
                if member.ob_pointer is None or member.ob_pointer.name not in scene.objects:
                    delete_objs.insert(0, j)
            for j in delete_objs:
                lg.members.remove(j)
                lg.members_index -= 1

        for i in delete_any:
            rm.light_links.remove(i)
            rm.light_links_index -= 1

    def invoke(self, context, event):
        '''
        if using_qt() and show_wip_qt():
            global __LIGHT_LINKING_WINDOW__
            if sys.platform == "darwin":
                rfb_qt.run_with_timer(__LIGHT_LINKING_WINDOW__, LightLinkingQtWrapper)   
            else:
                bpy.ops.wm.light_linking_qt_app_timed()     

            return {'FINISHED'}    
        '''

        wm = context.window_manager
        width = rfb_config['editor_preferences']['lightlink_editor']['width']
        self.event = event
        self.check_light_links(context)
        return wm.invoke_props_dialog(self, width=width)       

classes = [
    PRMAN_PT_Renderman_Open_Light_Linking,
    RENDERMAN_UL_LightLink_Light_List,
    RENDERMAN_UL_LightLink_Object_List,
]

#if not bpy.app.background and rfb_qt:
#    classes.append(LightLinkingQtAppTimed)

def register():
    from ...rfb_utils import register_utils

    register_utils.rman_register_classes(classes)

def unregister():
    from ...rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)            