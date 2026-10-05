"""Conservative two-layer grid routing of remaining DRC ratsnest connections.
KiCad DRC is authoritative after each application, never suppresses violations.
"""
import pathlib,json,heapq,math,itertools
import numpy as np
from shapely.geometry import Point,box,LineString,Polygon
from shapely.ops import unary_union,nearest_points
from shapely import contains_xy
R=pathlib.Path(__file__).resolve().parents[1];data=json.loads((R/'checks/geometry.json').read_text(encoding='utf-8'));report=json.loads((R/'checks/drc_routed.json').read_text(encoding='utf-8'));manifest=json.loads((R/'fabrication/design_manifest.json').read_text(encoding='utf-8'))
step=.15;W=int(110/step)+1;H=int(90/step)+1
xx,yy=np.meshgrid(np.arange(W)*step,np.arange(H)*step);gridpoints=np.c_[xx.ravel(),yy.ravel()]
def geom(o):
 if o['kind']=='pad':return box(*o['box'])
 if o['kind']=='via':return Point(o['center']).buffer(o['width']/2)
 return LineString([o['start'],o['end']]).buffer(o['width']/2)
for o in data:o['geometry']=geom(o)
idmap={o['id']:o for o in data};result=[]
def comp(net,actor):
 obs=[o for o in data if o['net']==net];seen={actor['id']};todo=[actor];out=[]
 while todo:
  a=todo.pop();out.append(a)
  for bb in obs:
   if bb['id'] not in seen and set(a['layers'])&set(bb['layers']) and a['geometry'].distance(bb['geometry'])<.002:
    seen.add(bb['id']);todo.append(bb)
 return out
dirs=[(-1,0,1),(1,0,1),(0,-1,1),(0,1,1),(-1,-1,1.4142),(-1,1,1.4142),(1,-1,1.4142),(1,1,1.4142)]
for gap in report['unconnected_items']:
 a,b=[idmap[i['uuid']] for i in gap['items']];net=a['net'];width=1.0 if net in ('SENSOR_5V','ESP32_5V','EXT_5V','EXT_5V_RAW','5V_SERVO','SERVO_5V_RAW') else .30
 starts=comp(net,a);goals=comp(net,b)
 if b['id'] in {o['id'] for o in starts}:continue
 clearance=.25 if width> .5 else .21
 safe=Polygon(manifest['outline']).buffer(-width/2-.35)
 voids=[box(*v).buffer(width/2+.01) for v in manifest['keepouts'].values()]+[LineString([(85,28),(104,28)]).buffer(.5+.35+width/2)]
 safe=safe.difference(unary_union(voids))
 base=contains_xy(safe,xx,yy);blocked=[];via_ok=[];goal_masks=[]
 for layer in (0,1):
  other=unary_union([o['geometry'] for o in data if layer in o['layers'] and o['net']!=net])
  blocked.append(~base|contains_xy(other.buffer(width/2+clearance+.08),xx,yy))
  vd=1.2 if width>.5 else .8
  via_ok.append(~contains_xy(other.buffer(vd/2+clearance+.08),xx,yy))
  goalgeo=unary_union([o['geometry'].buffer(.001) for o in goals if layer in o['layers']])
  goal_masks.append(contains_xy(goalgeo,xx,yy))
 via_mask=via_ok[0]&via_ok[1]&contains_xy(Polygon(manifest['outline']).buffer(-vd/2-.35).difference(unary_union([box(*v).buffer(vd/2+.01) for v in manifest['keepouts'].values()]+[LineString([(85,28),(104,28)]).buffer(.5+.35+vd/2)])),xx,yy)
 goal_cells=np.argwhere(goal_masks[0]|goal_masks[1]);gx0,gx1=goal_cells[:,1].min(),goal_cells[:,1].max();gy0,gy1=goal_cells[:,0].min(),goal_cells[:,0].max()
 def heuristic(x,y):return math.hypot(max(gx0-x,0,x-gx1),max(gy0-y,0,y-gy1))
 seeds=[]
 # Seed all existing start-component copper, allowing short connections from a large cluster.
 for l in (0,1):
  startgeo=unary_union([o['geometry'].buffer(.001) for o in starts if l in o['layers']]);sm=contains_xy(startgeo,xx,yy)&~blocked[l]
  for y,x in np.argwhere(sm):seeds.append((l,int(x),int(y)))
 if not seeds:raise RuntimeError('No accessible start cells for '+net)
 queue=[];dist={};prev={}
 for state in seeds:dist[state]=0;heapq.heappush(queue,(heuristic(state[1],state[2]),0,state))
 end=None;count=0
 while queue:
  _,cost,state=heapq.heappop(queue)
  if cost!=dist.get(state):continue
  l,x,y=state;count+=1
  if goal_masks[l][y,x]:end=state;break
  for dx,dy,dc in dirs:
   nx,ny=x+dx,y+dy
   if nx<0 or ny<0 or nx>=W or ny>=H or blocked[l][ny,nx]:continue
   if dx and dy and (blocked[l][y,nx] or blocked[l][ny,x]):continue
   ns=(l,nx,ny);nc=cost+dc
   if nc<dist.get(ns,math.inf):dist[ns]=nc;prev[ns]=state;heapq.heappush(queue,(nc+heuristic(nx,ny),nc,ns))
  if via_mask[y,x] and not blocked[1-l][y,x]:
   ns=(1-l,x,y);nc=cost+60
   if nc<dist.get(ns,math.inf):dist[ns]=nc;prev[ns]=state;heapq.heappush(queue,(nc+heuristic(x,y),nc,ns))
 if end is None:raise RuntimeError('No route found for '+net)
 states=[end]
 while states[-1] in prev:states.append(prev[states[-1]])
 states.reverse()
 # Keep only direction changes to create clean 45 degree tracks.
 keep=[states[0]]
 for i in range(1,len(states)-1):
  aa=states[i-1];bb=states[i];cc=states[i+1]
  if (bb[0]-aa[0],bb[1]-aa[1],bb[2]-aa[2])!=(cc[0]-bb[0],cc[1]-bb[1],cc[2]-bb[2]):keep.append(bb)
 keep.append(states[-1]);path=[[x*step,y*step,l] for l,x,y in keep]
 # Contact copper at each end, followed by an exact projection to its centerline/pad center.
 for index,group in [(0,starts),(-1,goals)]:
  point=Point(path[index][:2]);l=path[index][2];o=min([o for o in group if l in o['layers']],key=lambda o:o['geometry'].distance(point))
  center=Point(o['center']) if o['kind']!='track' else nearest_points(point,LineString([o['start'],o['end']]))[1]
  extra=[center.x,center.y,l]
  if index==0:path.insert(0,extra)
  else:path.append(extra)
 result.append({'net':net,'width':width,'path':path,'expanded_nodes':count})
 # Include newly routed copper in the next search's obstacles and connectivity.
 for aa,bb in zip(path,path[1:]):
  o={'id':'manual-'+str(len(data)),'net':net,'width':width,'layers':[aa[2]],'kind':'track','start':aa[:2],'end':bb[:2]}
  if aa[2]!=bb[2]:o.update(kind='via',center=aa[:2],width=vd,layers=[0,1])
  o['geometry']=geom(o);data.append(o)
 print(net,len(path),'points,',count,'expanded nodes',flush=True)
(R/'checks/manual_routes.json').write_text(json.dumps(result,indent=2))
