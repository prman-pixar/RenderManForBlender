from .rman_socket_utils import node_add_input

def node_add_array_elem(node, collection, collection_index, param_name, elem_type):

    collection = getattr(node, collection)
    index = getattr(node, collection_index)        
    meta = node.prop_meta[param_name]
    connectable = True
    if '__noconnection' in meta and meta['__noconnection']:
        connectable = False
    elem = collection.add()
    index = len(collection)-1
    setattr(node, collection_index, index)
    elem.name = '%s[%d]' % (param_name, len(collection)-1)  
    elem.type = elem_type
    if connectable:
        param_array_label = '%s[%d]' % (meta.get('label', param_name), len(collection)-1)
        node_add_input(node, elem_type, elem.name, meta, param_array_label)                

def node_remove_array_elem(node, collection, collection_index, param_name, elem_type):
    collection = getattr(node, collection)
    index = getattr(node, collection_index)        
    meta = node.prop_meta[param_name]
    connectable = True
    if '__noconnection' in meta and meta['__noconnection']:
        connectable = False
    idx = -1
    if connectable:
        # rename sockets
        def update_sockets(socket, name, label):
            link = None
            from_socket = None
            if socket.is_linked:                    
                link = socket.links[0]
                from_socket = link.from_socket       
            node.inputs.remove(socket)                                     
            new_socket = node_add_input(node, elem_type, name, meta, label)
            if not new_socket:
                return
            if link and from_socket:
                nt = node.id_data
                nt.links.new(from_socket, new_socket)
            
        idx = 0 
        elem = collection[index]
        node.inputs.remove(node.inputs[elem.name])
        for elem in collection:
            nm = elem.name
            new_name = '%s[%d]' % (param_name, idx)
            new_label = '%s[%d]' % (meta.get('label', param_name), idx)
            socket = node.inputs.get(nm, None)
            if socket:
                update_sockets(socket, new_name, new_label)
                idx += 1                    
            
    collection.remove(index)                    
    index -= 1
    setattr(node, collection_index, 0)
    for i in range(len(collection)):
        elem = collection[i]
        elem.name = '%s[%d]' % (param_name, i)