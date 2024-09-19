from bpy.props import (StringProperty, BoolProperty, EnumProperty)

from ...rman_ui.rman_ui_base import CollectionPanel   
from ...rman_operators.rman_operators_collections import return_empty_list   
from ...rman_config import __RFB_CONFIG_DICT__ as rfb_config
from ...rfb_utils import scene_utils
from ... import rfb_icons
from ...rfb_utils.prefs_utils import using_qt, show_wip_qt
import bpy
import re
import sys

__VOL_AGGREGATE_WINDOW__ = None 
'''
if not bpy.app.background:
    try:
        from ...rman_ui import rfb_qt as rfb_qt
        from rman_utils.vendor.Qt import QtCore, QtWidgets, QtGui
    except:
        rfb_qt = None

    if rfb_qt:
        class VolAggregateQtAppTimed(rfb_qt.RfbBaseQtAppTimed):
            bl_idname = "wm.vol_aggregates_qt_app_timed"
            bl_label =  "RenderMan Volume Aggregates Editor"

            def __init__(self):
                super(VolAggregateQtAppTimed, self).__init__()

            def execute(self, context):
                self._window = VolAggregatesQtWrapper()
                return super(VolAggregateQtAppTimed, self).execute(context)

        class StandardItem(QtGui.QStandardItem):
            def __init__(self, txt=''):
                super().__init__()
                self.setEditable(False)
                self.setText(txt)

        class VolAggregatesQtWrapper(rfb_qt.RmanQtWrapper):
            def __init__(self) -> None:
                super(VolAggregatesQtWrapper, self).__init__()
            
                self.setWindowTitle('RenderMan Volume Aggregates')
                self.resize(620, 475)
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
                self.removeButton = QtWidgets.QPushButton(self)
                self.removeButton.setGeometry(QtCore.QRect(280, 50, 31, 26))
                self.removeButton.setObjectName("removeButton")
                self.removeButton.setText("-")

                self.volAggregateGroupObjects = QtWidgets.QTreeView(self)
                self.volAggregateGroupObjects.setHeaderHidden(True)
                self.treeModel = QtGui.QStandardItemModel(self)
                self.rootNode = self.treeModel.invisibleRootItem()
                self.volAggregateGroupObjects.setModel(self.treeModel)

                self.volAggregateGroupObjects.setGeometry(QtCore.QRect(30, 250, 441, 192))
                self.volAggregateGroupObjects.setObjectName("volAggregateGroupObjects")
                self.volAggregateGroupObjects.setSelectionMode(
                    QtWidgets.QAbstractItemView.MultiSelection
                )            

                self.volAggregateGroups = QtWidgets.QListWidget(self)
                self.volAggregateGroups.setGeometry(QtCore.QRect(30, 30, 256, 192))
                self.volAggregateGroups.setObjectName("volAggregateGroups")

                self.label = QtWidgets.QLabel(self)
                self.label.setGeometry(QtCore.QRect(40, 10, 91, 17))
                self.label.setText("Volume Aggregates")

                self.label_2 = QtWidgets.QLabel(self)
                self.label_2.setGeometry(QtCore.QRect(40, 230, 200, 17))
                self.label_2.setText("Objects")

                self.refresh_btn = QtWidgets.QPushButton(self)
                self.refresh_btn.setGeometry(QtCore.QRect(470, 250, 100, 26))
                self.refresh_btn.setText("Refresh")
                self.setToolTip("""Click this if the objects list is out of sync with the scene""" )

                QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("accepted()"), self.accept)
                QtCore.QObject.connect(self.buttonBox, QtCore.SIGNAL("rejected()"), self.reject)
                QtCore.QMetaObject.connectSlotsByName(self)

                self.addButton.clicked.connect(self.add_group)
                self.removeButton.clicked.connect(self.remove_group)
                self.refresh_btn.clicked.connect(self.refresh_group_objects)

                self.volAggregateGroups.itemChanged.connect(self.vol_aggregate_group_changed)
                self.volAggregateGroups.itemSelectionChanged.connect(self.vol_aggregate_groups_index_changed)
                self.volAggregateGroupObjects.selectionModel().selectionChanged.connect(self.vol_aggregate_group_objects_selection)

                self.refresh_groups()
                self.refresh_group_objects()
                self.checkvolAggregateGroups()

                self.volAggregateGroupObjects.expandAll()   

                self.add_handlers()

            def closeEvent(self, event):
                self.remove_handlers()
                super(VolAggregatesQtWrapper, self).closeEvent(event)

            def add_handlers(self):       
                if self.depsgraph_update_post not in bpy.app.handlers.depsgraph_update_post:
                    bpy.app.handlers.depsgraph_update_post.append(self.depsgraph_update_post)            

            def remove_handlers(self):
                if self.depsgraph_update_post in bpy.app.handlers.depsgraph_update_post:
                    bpy.app.handlers.depsgraph_update_post.remove(self.depsgraph_update_post)             

            def depsgraph_update_post(self, bl_scene, depsgraph):
                for dps_update in reversed(depsgraph.updates):
                    if isinstance(dps_update.id, bpy.types.Collection):
                        self.volAggregateGroups.setCurrentRow(-1)
                        self.refresh_group_objects()             

            def checkvolAggregateGroups(self):
                if self.volAggregateGroups.count() < 1:
                    self.volAggregateGroupObjects.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
                    self.vol_aggregate_group_objects(self.rootNode, enable=False)
                    self.removeButton.setEnabled(False)
                else:
                    self.volAggregateGroupObjects.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
                    self.removeButton.setEnabled(True)
                    self.vol_aggregate_group_objects(self.rootNode, enable=True)        

            def update(self):
                idx = int(self.volAggregateGroups.currentRow())
                self.addButton.setEnabled(True)

                self.checkvolAggregateGroups()
                super(VolAggregatesQtWrapper, self).update()

            def refresh_groups(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman
                self.volAggregateGroups.clear()
                for i, grp in enumerate(rm.vol_aggregates):
                    if i == 0:
                        continue
                    item = QtWidgets.QListWidgetItem(grp.name)
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                    self.volAggregateGroups.addItem(item)

                if self.volAggregateGroups.count() > 0:
                    self.volAggregateGroups.setCurrentRow(rm.vol_aggregates_index)
                    
            def add_group(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman    

                grp = rm.vol_aggregates.add()
                grp.name = 'VolumeAggreagte_%d' % (len(rm.vol_aggregates)-2)
                rm.vol_aggregates_index = len(rm.vol_aggregates)-1
                self.refresh_groups()

            def remove_group(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman    

                index = rm.vol_aggregates_index
                group = rm.vol_aggregates[index]            
                # get a list of all objects in this group
                ob_list = [member.ob_pointer for member in group.members]
                rm.vol_aggregates.remove(index)
                rm.vol_aggregates_index -= 1

                # now tell each object to update
                for ob in ob_list:
                    ob.update_tag(refresh={'DATA'})

                self.refresh_groups()       

            def vol_aggregate_group_changed(self, item):
                idx = int(self.volAggregateGroups.currentRow())

                context = bpy.context
                scene = context.scene
                rm = scene.renderman
                grp = rm.vol_aggregates[idx+1]
                grp.name = item.text()    
                self.label_2.setText("Objects (%s)" % item.text())
                for member in grp.members:
                    ob = member.ob_pointer
                    ob.update_tag(refresh={'DATA'})

            def find_item(self, standard_item, ob):       
                for i in range(0, standard_item.rowCount()):
                    item = standard_item.child(i)
                    if item.text() == ob.name:
                        return item                
                
                return None

            def vol_aggregate_group_objects(self, standard_item, enable=True):
                standard_item.setEnabled(enable)
                for i in range(0, standard_item.rowCount()):
                    item = standard_item.child(i)
                    item.setEnabled(enable)
                    if item.hasChildren():
                        return self.vol_aggregate_group_objects(item, enable=enable)
                
            def refresh_group_objects(self):
                idx = int(self.volAggregateGroups.currentRow())
                enabled = True
                if idx == -1:
                    enabled = False
                    self.label_2.setText("Objects (no group selected)")
                context = bpy.context
                scene = context.scene
                rm = scene.renderman
                
                self.treeModel.clear()
                self.rootNode = self.treeModel.invisibleRootItem()
                
                root_parents = scene_utils.get_all_volume_objects(scene)
                for ob in root_parents:
                    
                    item = self.find_item(self.rootNode, ob)
                    if not item:
                        item = StandardItem(txt=ob.name)
                    self.rootNode.appendRow(item)

                self.volAggregateGroupObjects.expandAll()
                if idx != -1:
                    self.vol_aggregate_groups_index_changed()

            def bl_select_objects(self, obs):
                context = bpy.context
                for ob in getattr(context, "selected_objects", list()):
                    ob.select_set(False)
                for ob in obs:
                    ob.select_set(True)
                    context.view_layer.objects.active = ob         

            def vol_aggregate_groups_index_changed(self):
                idx = int(self.volAggregateGroups.currentRow())
                current_item = self.volAggregateGroups.currentItem()
                self.checkvolAggregateGroups()
                if current_item:
                    self.label_2.setText("Objects (%s)" % current_item.text())
                else:
                    return
                context = bpy.context
                scene = context.scene
                rm = scene.renderman               
                rm.vol_aggregates_index = idx + 1  

                group_index = rm.vol_aggregates_index
                vol_aggregates = rm.vol_aggregates
                object_group = vol_aggregates[group_index]

                selected_items =  QtCore.QItemSelection()
                obs = []
                for member in object_group.members:
                    ob = member.ob_pointer
                    if ob is None:
                        continue
                    item = self.find_item(self.rootNode, ob)
                    if item:
                        idx = self.treeModel.indexFromItem(item)
                        selection_range = QtCore.QItemSelectionRange(idx)
                        selected_items.append(selection_range)
                        obs.append(ob)
                self.volAggregateGroupObjects.selectionModel().select(selected_items, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.NoUpdate)
                self.bl_select_objects(obs)
                        
            def vol_aggregate_group_objects_selection(self, selected, deselected):
                idx = int(self.volAggregateGroups.currentRow())
                current_item = self.volAggregateGroups.currentItem()
                if not current_item:
                    return

                context = bpy.context
                scene = context.scene
                rm = scene.renderman  

                group_index = rm.vol_aggregates_index
                vol_aggregates = rm.vol_aggregates
                if group_index not in range(0, len(vol_aggregates)):
                    return
                object_group = vol_aggregates[group_index]

                for i in deselected.indexes():
                    item = self.volAggregateGroupObjects.model().itemFromIndex(i)
                    ob = bpy.data.objects.get(item.text(), None)
                    if ob is None:
                        continue
                    for i, member in enumerate(object_group.members):
                        if ob == member.ob_pointer:
                            object_group.members.remove(i)
                            ob.update_tag(refresh={'DATA'}) 
                            break                    

                obs = []
                for i in selected.indexes():
                    item = self.volAggregateGroupObjects.model().itemFromIndex(i)
                    ob = bpy.data.objects.get(item.text(), None)
                    if ob is None:
                        continue
                    do_add = True
                    for member in object_group.members:            
                        if ob == member.ob_pointer:
                            do_add = False
                        obs.append(member.ob_pointer)                                    
                    if do_add:
                        obs.append(ob)                                    
                        ob_in_group = object_group.members.add()
                        ob_in_group.name = ob.name
                        ob_in_group.ob_pointer = ob      
                        ob.update_tag(refresh={'DATA'})       
                self.bl_select_objects(obs)
'''
class RENDERMAN_UL_Volume_Aggregates_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):
        rman_vol_agg = rfb_icons.get_icon("rman_vol_aggregates").icon_id
        if index == 0:
            layout.label(text=item.name, icon_value=rman_vol_agg)
        else:
            layout.prop(item, 'name', text='', emboss=False, icon_value=rman_vol_agg) 
        

class RENDERMAN_UL_Volume_Aggregates_Objects_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        custom_icon = 'OUTLINER_OB_VOLUME'
        layout.context_pointer_set("selected_obj", item.ob_pointer)
        op = layout.operator('renderman.remove_from_vol_aggregate', text='', icon='REMOVE')     
        label = item.ob_pointer.name
        layout.label(text=label, icon=custom_icon)         

class PRMAN_OT_Renderman_Open_Volume_Aggregates_Editor(CollectionPanel, bpy.types.Operator):

    bl_idname = "scene.rman_open_vol_aggregates_editor"
    bl_label = "RenderMan Volume Aggregates Editor"
    bl_description = "Volume Aggregates Editor"

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

        group = rm.vol_aggregates[rm.vol_aggregates_index]
        objs_in_group = []
        for member in group.members:
            objs_in_group.append(member.ob_pointer.name)               

        items = []

        for ob in scene_utils.get_all_volume_objects(scene):
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

    do_object_filter: BoolProperty(name="Object Filter", 
                                description="Search and add multiple objects",
                                default=False,
                                update=update_do_object_filter)    
    object_search_filter: StringProperty(name="Object Filter Search", default="")       
    selected_obj_name: EnumProperty(name="", items=obj_list_items, update=updated_object_selected_name)       

    def execute(self, context):
        self.check_aggregates(context)
        return{'FINISHED'}         

    def draw(self, context):
        layout = self.layout
        scene = context.scene   
        rm = scene.renderman
        layout.separator()
        self._draw_collection(context, layout, rm, "Volume Aggregates",
                            "renderman.add_remove_volume_aggregates",
                            "scene.renderman",
                            "vol_aggregates", "vol_aggregates_index",
                            default_name='VolumeAggreagte_%d' % (len(rm.vol_aggregates)-2),
                            ui_list_class="RENDERMAN_UL_Volume_Aggregates_List",
                            enable_remove_func=self.enable_remove_func)

    def enable_remove_func(self, context):
        scene = context.scene
        rm = scene.renderman
        return (rm.vol_aggregates_index != 0)

    def draw_objects_item(self, layout, context, item):
        row = layout.row()
        scene = context.scene
        rm = scene.renderman
        vol_aggregate = rm.vol_aggregates[rm.vol_aggregates_index]

        if rm.vol_aggregates_index == 0:
            # we're viewing the global volume aggregate
            # just display what volumes are in the global aggregate
            # and don't allow the user to edit the list
            box = layout.box()
            box.use_property_split = True
            box.use_property_decorate = False

            # Loop over all of volume objects in the scene.
            # Check if they already belong to aggregate. If they do, they
            # are not the global aggregate.
            for ob in scene_utils.get_all_volume_objects(scene):
                if not ob.renderman.volume_global_aggregate:
                    # volume is should not be in the global aggregate
                    continue
                do_draw = True
                for lg in rm.vol_aggregates:
                    for member in lg.members:
                        if member.ob_pointer == ob:
                            do_draw = False
                            break
                    if not do_draw:
                        break
                if do_draw:
                    row = box.row(align=True)
                    custom_icon = 'OUTLINER_OB_VOLUME'
                    row.label(text=ob.name, icon=custom_icon)
            return

        row = layout.row()
        row.separator()   

        row.prop(self, 'do_object_filter', text='', icon='FILTER', icon_only=True)
        if not self.do_object_filter:
            row.prop(self, 'selected_obj_name', text='')
            col = row.column()
            if self.selected_obj_name == '0' or self.selected_obj_name == '':
                col.enabled = False
                op = col.operator("renderman.add_to_vol_aggregate", text='', icon='ADD')
                op.open_editor = False
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])
                op = col.operator("renderman.add_to_vol_aggregate", text='', icon='ADD')
                op.vol_aggregates_index = rm.vol_aggregates_index    
                op.do_scene_selected = False
                op.open_editor = False
        else:
            row.prop(self, 'object_search_filter', text='', icon='VIEWZOOM')
            row = layout.row()  
            row.prop(self, 'selected_obj_name')
            col = row.column()
            if self.selected_obj_name == '0' or self.selected_obj_name == '':
                col.enabled = False
                op = col.operator("renderman.add_to_vol_aggregate", text='', icon='ADD')
                op.open_editor = False
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])                
                op = col.operator("renderman.add_to_vol_aggregate", text='', icon='ADD')
                op.vol_aggregates_index = rm.vol_aggregates_index
                op.do_scene_selected = False
                op.open_editor = False

        row = layout.row()
        
        row.template_list('RENDERMAN_UL_Volume_Aggregates_Objects_List', "",
                        vol_aggregate, "members", vol_aggregate, 'members_index', rows=6)        

    def draw_item(self, layout, context, item):
        self.draw_objects_item(layout, context, item)

    def cancel(self, context):
        if self.event and self.event.type == 'LEFTMOUSE':
            bpy.ops.scene.rman_open_vol_aggregates_editor('INVOKE_DEFAULT')
        else:
            self.check_aggregates(context)
            
    def __init__(self):
        self.event = None      

    def check_aggregates(self, context):
        scene = context.scene
        rm = scene.renderman
        
        for lg in rm.vol_aggregates:
            delete_objs = []
            for j in range(len(lg.members)-1, -1, -1):
                member = lg.members[j]
                if member.ob_pointer is None or member.ob_pointer.name not in scene.objects:
                    delete_objs.insert(0, j)
            for j in delete_objs:
                lg.members.remove(j)
                lg.members_index -= 1              

    def invoke(self, context, event):
        '''
        if using_qt() and show_wip_qt():
            global __VOL_AGGREGATE_WINDOW__
            if sys.platform == "darwin":
                rfb_qt.run_with_timer(__VOL_AGGREGATE_WINDOW__, VolAggregatesQtWrapper)   
            else:
                bpy.ops.wm.vol_aggregates_qt_app_timed()     

            return {'FINISHED'}               
        '''

        wm = context.window_manager
        width = rfb_config['editor_preferences']['vol_aggregates_editor']['width']
        self.event = event
        self.check_aggregates(context)
        return wm.invoke_props_dialog(self, width=width) 

classes = [    
    PRMAN_OT_Renderman_Open_Volume_Aggregates_Editor,
    RENDERMAN_UL_Volume_Aggregates_List,
    RENDERMAN_UL_Volume_Aggregates_Objects_List,
]

# if not bpy.app.background and rfb_qt:
#    classes.append(VolAggregateQtAppTimed)

def register():
    from ...rfb_utils import register_utils

    register_utils.rman_register_classes(classes)

def unregister():
    from ...rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)                         