from bpy.props import (StringProperty, BoolProperty, EnumProperty)

from ...rman_ui.rman_ui_base import CollectionPanel   
from ...rman_operators.rman_operators_collections import return_empty_list   
from ...rman_config import __RFB_CONFIG_DICT__ as rfb_config
from ...rfb_utils.prefs_utils import using_qt, show_wip_qt
import bpy
import re
import sys

__TRACE_GROUPS_WINDOW__ = None 

if not bpy.app.background:
    try:
        from ...rman_ui import rfb_qt as rfb_qt
        from PySide2 import QtCore, QtWidgets, QtGui 
    except:
        rfb_qt = None

    if rfb_qt:
        class TraceGroupsQtAppTimed(rfb_qt.RfbBaseQtAppTimed):
            bl_idname = "wm.trace_groups_qt_app_timed"
            bl_label =  "RenderMan Trace Sets Editor"

            def __init__(self):
                super(TraceGroupsQtAppTimed, self).__init__()

            def execute(self, context):
                self._window = TraceGroupsQtWrapper()
                return super(TraceGroupsQtAppTimed, self).execute(context)

        class StandardItem(QtGui.QStandardItem):
            def __init__(self, txt=''):
                super().__init__()
                self.setEditable(False)
                self.setText(txt)

        class TraceGroupsQtWrapper(rfb_qt.RmanQtWrapper):
            def __init__(self) -> None:
                super(TraceGroupsQtWrapper, self).__init__()
            
                self.setWindowTitle('RenderMan Trace Groups')
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

                self.traceGroupObjects = QtWidgets.QTreeView(self)
                self.traceGroupObjects.setHeaderHidden(True)
                self.treeModel = QtGui.QStandardItemModel(self)
                self.rootNode = self.treeModel.invisibleRootItem()
                self.traceGroupObjects.setModel(self.treeModel)

                self.traceGroupObjects.setGeometry(QtCore.QRect(30, 250, 441, 192))
                self.traceGroupObjects.setObjectName("traceGroupObjects")
                self.traceGroupObjects.setSelectionMode(
                    QtWidgets.QAbstractItemView.MultiSelection
                )            

                self.traceGroups = QtWidgets.QListWidget(self)
                self.traceGroups.setGeometry(QtCore.QRect(30, 30, 256, 192))
                self.traceGroups.setObjectName("traceGroups")

                self.label = QtWidgets.QLabel(self)
                self.label.setGeometry(QtCore.QRect(40, 10, 91, 17))
                self.label.setText("Trace Groups")

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

                self.traceGroups.itemChanged.connect(self.trace_group_changed)
                self.traceGroups.itemSelectionChanged.connect(self.trace_groups_index_changed)
                self.traceGroupObjects.selectionModel().selectionChanged.connect(self.trace_group_objects_selection)

                self.refresh_groups()
                self.refresh_group_objects()
                self.checkTraceGroups()

                self.traceGroupObjects.expandAll()   

                self.add_handlers()

            def closeEvent(self, event):
                self.remove_handlers()
                super(TraceGroupsQtWrapper, self).closeEvent(event)

            def add_handlers(self):       
                if self.depsgraph_update_post not in bpy.app.handlers.depsgraph_update_post:
                    bpy.app.handlers.depsgraph_update_post.append(self.depsgraph_update_post)            

            def remove_handlers(self):
                if self.depsgraph_update_post in bpy.app.handlers.depsgraph_update_post:
                    bpy.app.handlers.depsgraph_update_post.remove(self.depsgraph_update_post)             

            def depsgraph_update_post(self, bl_scene, depsgraph):
                for dps_update in reversed(depsgraph.updates):
                    if isinstance(dps_update.id, bpy.types.Collection):
                        #self.refresh_groups()
                        self.traceGroups.setCurrentRow(-1)
                        self.refresh_group_objects()             
                    #elif isinstance(dps_update.id, bpy.types.Scene): 
                    #    self.trace_groups_index_changed()

            def checkTraceGroups(self):
                if self.traceGroups.count() < 1:
                    self.traceGroupObjects.setSelectionMode(QtWidgets.QAbstractItemView.NoSelection)
                    self.enable_trace_group_objects(self.rootNode, enable=False)
                    self.removeButton.setEnabled(False)
                else:
                    self.traceGroupObjects.setSelectionMode(QtWidgets.QAbstractItemView.MultiSelection)
                    self.removeButton.setEnabled(True)
                    self.enable_trace_group_objects(self.rootNode, enable=True)        

            def update(self):
                idx = int(self.traceGroups.currentRow())
                self.addButton.setEnabled(True)

                self.checkTraceGroups()
                super(TraceGroupsQtWrapper, self).update()

            def refresh_groups(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman
                self.traceGroups.clear()
                for grp in rm.object_groups:
                    item = QtWidgets.QListWidgetItem(grp.name)
                    item.setFlags(item.flags() | QtCore.Qt.ItemIsEditable)
                    self.traceGroups.addItem(item)

                if self.traceGroups.count() > 0:
                    self.traceGroups.setCurrentRow(rm.object_groups_index)
                    
            def add_group(self):
                context = bpy.context
                scene = context.scene
                rm = scene.renderman    

                grp = rm.object_groups.add()
                grp.name = 'traceGroup_%d' % len(rm.object_groups)
                rm.object_groups_index = len(rm.object_groups)-1
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
                    ob.update_tag(refresh={'DATA'})

                self.refresh_groups()       

            def trace_group_changed(self, item):
                idx = int(self.traceGroups.currentRow())

                context = bpy.context
                scene = context.scene
                rm = scene.renderman
                grp = rm.object_groups[idx]
                grp.name = item.text()    
                self.label_2.setText("Objects (%s)" % item.text())
                for member in grp.members:
                    ob = member.ob_pointer
                    ob.update_tag(refresh={'DATA'})        

            def find_item(self, standard_item, ob):
                '''
                if standard_item.text() == ob.name:
                    return standard_item
                
                for i in range(0, standard_item.rowCount()):
                    item = standard_item.child(i)
                    if item.text() == ob.name:
                        return item
                    if item.hasChildren():
                        return self.find_item(item, ob)
                '''            
                for i in range(0, standard_item.rowCount()):
                    item = standard_item.child(i)
                    if item.text() == ob.name:
                        return item                
                
                return None

            def enable_trace_group_objects(self, standard_item, enable=True):
                standard_item.setEnabled(enable)
                for i in range(0, standard_item.rowCount()):
                    item = standard_item.child(i)
                    item.setEnabled(enable)
                    if item.hasChildren():
                        return self.enable_trace_group_objects(item, enable=enable)
                
            def refresh_group_objects(self):
                idx = int(self.traceGroups.currentRow())
                enabled = True
                if idx == -1:
                    enabled = False
                    self.label_2.setText("Objects (no group selected)")
                context = bpy.context
                scene = context.scene
                rm = scene.renderman
                
                self.treeModel.clear()
                self.rootNode = self.treeModel.invisibleRootItem()

                def add_children(root_item, ob):
                    for child in ob.children:
                        if child.type in ['CAMERA', 'ARMATURE']:
                            continue                
                        item = self.find_item(root_item, child)
                        if not item:
                            item = StandardItem(txt=child.name)
                        root_item.appendRow(item)
                        if len(child.children) > 0:
                            add_children(item, child)
                
                root_parents = [ob for ob in scene.objects if ob.parent is None]            
                for ob in root_parents:
                    if ob.type in ('ARMATURE', 'CAMERA'):
                        continue  
                    
                    item = self.find_item(self.rootNode, ob)
                    if not item:
                        item = StandardItem(txt=ob.name)
                    self.rootNode.appendRow(item)
                    if len(ob.children) > 0:
                        add_children(item, ob)

                self.traceGroupObjects.expandAll()
                if idx != -1:
                    self.trace_groups_index_changed()

            def bl_select_objects(self, obs):
                context = bpy.context
                for ob in getattr(context, "selected_objects", list()):
                    ob.select_set(False)
                for ob in obs:
                    ob.select_set(True)
                    context.view_layer.objects.active = ob                

            def trace_groups_index_changed(self):
                idx = int(self.traceGroups.currentRow())
                current_item = self.traceGroups.currentItem()
                self.checkTraceGroups()
                if current_item:
                    self.label_2.setText("Objects (%s)" % current_item.text())
                else:
                    return
                context = bpy.context
                scene = context.scene
                rm = scene.renderman               
                rm.object_groups_index = idx   

                group_index = rm.object_groups_index
                object_groups = rm.object_groups
                object_group = object_groups[group_index]

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
                self.traceGroupObjects.selectionModel().select(selected_items, QtCore.QItemSelectionModel.ClearAndSelect | QtCore.QItemSelectionModel.NoUpdate)
                self.bl_select_objects(obs)
                        
            def trace_group_objects_selection(self, selected, deselected):
                idx = int(self.traceGroups.currentRow())
                current_item = self.traceGroups.currentItem()
                if not current_item:
                    return

                context = bpy.context
                scene = context.scene
                rm = scene.renderman  

                group_index = rm.object_groups_index
                object_groups = rm.object_groups
                if group_index not in range(0, len(object_groups)):
                    return
                object_group = object_groups[group_index]

                for i in deselected.indexes():
                    item = self.traceGroupObjects.model().itemFromIndex(i)
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
                    item = self.traceGroupObjects.model().itemFromIndex(i)
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
                
class RENDERMAN_UL_Object_Group_List(bpy.types.UIList):

    def draw_item(self, context, layout, data, item, icon, active_data, active_propname, index):

        custom_icon = 'OBJECT_DATAMODE'
        layout.context_pointer_set("selected_obj", item.ob_pointer)
        op = layout.operator('renderman.remove_from_group', text='', icon='REMOVE')     
        label = item.ob_pointer.name
        layout.label(text=label, icon=custom_icon) 



class PRMAN_OT_Renderman_Open_Groups_Editor(CollectionPanel, bpy.types.Operator):

    bl_idname = "scene.rman_open_groups_editor"
    bl_label = "RenderMan Trace Sets Editor"

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

        group = rm.object_groups[rm.object_groups_index]
        objs_in_group = []
        for member in group.members:
            objs_in_group.append(member.ob_pointer.name)

        items = []
        for ob_name in [ob.name for ob in context.scene.objects if ob.type not in ['LIGHT', 'CAMERA']]:
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
        self.check_tracegroups(context)
        return{'FINISHED'}         

    def draw(self, context):
        layout = self.layout
        scene = context.scene   
        rm = scene.renderman
        layout.separator()
        self._draw_collection(context, layout, rm, "Trace Sets",
                            "renderman.add_remove_object_groups",
                            "scene.renderman",
                            "object_groups", "object_groups_index",
                            default_name='traceSet_%d' % len(rm.object_groups))          

    def draw_objects_item(self, layout, context, item):
        row = layout.row()
        scene = context.scene
        rm = scene.renderman
        group = rm.object_groups[rm.object_groups_index]

        row = layout.row()
        row.separator()   

        row.prop(self, 'do_object_filter', text='', icon='FILTER', icon_only=True)
        if not self.do_object_filter:
            row.prop(self, 'selected_obj_name', text='')
            col = row.column()
            if self.selected_obj_name == '0' or self.selected_obj_name == '':
                col.enabled = False
                op = col.operator("renderman.add_to_group", text='', icon='ADD')
                op.open_editor = False
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])
                op = col.operator("renderman.add_to_group", text='', icon='ADD')
                op.group_index = rm.object_groups_index    
                op.do_scene_selected = False
                op.open_editor = False
        else:
            row.prop(self, 'object_search_filter', text='', icon='VIEWZOOM')
            row = layout.row()  
            row.prop(self, 'selected_obj_name')
            col = row.column()
            if self.selected_obj_name == '0' or self.selected_obj_name == '':
                col.enabled = False
                op = col.operator("renderman.add_to_group", text='', icon='ADD')
                op.open_editor = False
            else:
                col.context_pointer_set('op_ptr', self) 
                col.context_pointer_set('selected_obj', scene.objects[self.selected_obj_name])                
                op = col.operator("renderman.add_to_group", text='', icon='ADD')
                op.group_index = rm.object_groups_index
                op.do_scene_selected = False
                op.open_editor = False

        row = layout.row()
        
        row.template_list('RENDERMAN_UL_Object_Group_List', "",
                        group, "members", group, 'members_index', rows=6)        

    def draw_item(self, layout, context, item):
        self.draw_objects_item(layout, context, item)

    def cancel(self, context):
        if self.event and self.event.type == 'LEFTMOUSE':
            bpy.ops.scene.rman_open_groups_editor('INVOKE_DEFAULT')
        else:
            self.check_tracegroups(context)
            
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.event = None

    def check_tracegroups(self, context):
        scene = context.scene
        rm = scene.renderman
        
        for lg in rm.object_groups:
            delete_objs = []
            for j in range(len(lg.members)-1, -1, -1):
                member = lg.members[j]
                if member.ob_pointer is None or member.ob_pointer.name not in scene.objects:
                    delete_objs.insert(0, j)
            for j in delete_objs:
                lg.members.remove(j)
                lg.members_index -= 1                        

    def invoke(self, context, event):

        if using_qt() and show_wip_qt():
            global __TRACE_GROUPS_WINDOW__
            if sys.platform == "darwin":
                rfb_qt.run_with_timer(__TRACE_GROUPS_WINDOW__, TraceGroupsQtWrapper)   
            else:
                bpy.ops.wm.trace_groups_qt_app_timed()     

            return {'FINISHED'}       

        wm = context.window_manager
        width = rfb_config['editor_preferences']['tracesets_editor']['width']
        self.event = event
        self.check_tracegroups(context)
        return wm.invoke_props_dialog(self, width=width) 

classes = [    
    PRMAN_OT_Renderman_Open_Groups_Editor,
    RENDERMAN_UL_Object_Group_List,
]

if not bpy.app.background and rfb_qt:
    classes.append(TraceGroupsQtAppTimed)

def register():
    from ...rfb_utils import register_utils

    register_utils.rman_register_classes(classes)

def unregister():
    from ...rfb_utils import register_utils

    register_utils.rman_unregister_classes(classes)                       