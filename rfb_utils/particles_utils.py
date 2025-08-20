from mathutils import Vector

def valid_particle(pa, valid_frames):
    return pa.die_time >= valid_frames[-1] and pa.birth_time <= valid_frames[0]

def get_particles(ob, psys, inv_mtx, frame, valid_frames=None, get_next_P=False, get_width=True):
    P = []
    next_P = []
    width = []

    valid_frames = (frame,
                    frame) if valid_frames is None else valid_frames
    
    rm = psys.settings.renderman

    for pa in [p for p in psys.particles if valid_particle(p, valid_frames)]:
        pt = inv_mtx @ pa.location
        P.append(pt)
        
        if get_next_P:
            # calculate the point for the next frame using velocity
            vel = Vector(pa.velocity / pa.lifetime ) * rm.scale_velocity_blur
            next_P.append( inv_mtx @ (Vector(pa.location) + vel))

        if get_width:
            if pa.alive_state != 'ALIVE':
                width.append(0.0)
            else:
                width.append(pa.size)
    return (P, next_P, width)    

def get_primvars_particle(primvar, frame, psys, subframes, sample):
    rm = psys.settings.renderman

    for p in rm.prim_vars:
        pvars = []

        if p.data_source in ('VELOCITY', 'ANGULAR_VELOCITY'):
            if p.data_source == 'VELOCITY':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, subframes)]:
                    pvars.append(pa.velocity)
            elif p.data_source == 'ANGULAR_VELOCITY':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, subframes)]:
                    pvars.append(pa.angular_velocity)

            primvar.SetVectorDetail(p.name, pvars, "vertex", sample)

        elif p.data_source in \
                ('SIZE', 'AGE', 'BIRTH_TIME', 'DIE_TIME', 'LIFE_TIME', 'ID'):
            if p.data_source == 'SIZE':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, subframes)]:
                    pvars.append(pa.size)
            elif p.data_source == 'AGE':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, subframes)]:
                    pvars.append((frame - pa.birth_time) / pa.lifetime)
            elif p.data_source == 'BIRTH_TIME':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, subframes)]:
                    pvars.append(pa.birth_time)
            elif p.data_source == 'DIE_TIME':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, subframes)]:
                    pvars.append(pa.die_time)
            elif p.data_source == 'LIFE_TIME':
                for pa in \
                        [p for p in psys.particles if valid_particle(p, subframes)]:
                    pvars.append(pa.lifetime)
            elif p.data_source == 'ID':
                pvars = [id for id, p in psys.particles.items(
                ) if valid_particle(p, subframes)]
            
            primvar.SetFloatDetail(p.name, pvars, "vertex", sample)  