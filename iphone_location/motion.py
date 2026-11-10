import bisect
import math
from dataclasses import dataclass

R = 6371008.8
# Default map / start / track center: Tiananmen Square (WGS-84). Change it with search, map click or coordinates.
DEFAULT_CENTER = (39.9027218666, 116.3914413539)

def validate(point):
    lat, lon = map(float, point)
    if not math.isfinite(lat) or not math.isfinite(lon) or abs(lat) > 85 or abs(lon) > 180:
        raise ValueError('纬度须在 -85～85，经度须在 -180～180，且必须为有限数值')
    return lat, lon

def distance(a, b):
    a1, b1 = map(math.radians, a)
    a2, b2 = map(math.radians, b)
    h = math.sin((a2-a1)/2)**2 + math.cos(a1)*math.cos(a2)*math.sin((b2-b1)/2)**2
    return 2*R*math.asin(min(1, math.sqrt(h)))

def destination(point, meters, bearing):
    lat, lon = map(math.radians, point)
    d = meters/R
    a = math.asin(max(-1, min(1, math.sin(lat)*math.cos(d)+math.cos(lat)*math.sin(d)*math.cos(bearing))))
    b = lon+math.atan2(math.sin(bearing)*math.sin(d)*math.cos(lat), math.cos(d)-math.sin(lat)*math.sin(a))
    return validate((math.degrees(a), (math.degrees(b)+540)%360-180))

def manual_step(point, north, east, kmh, seconds):
    if not math.isfinite(kmh) or kmh < 0:
        raise ValueError('速度须为有效非负数')
    if not north and not east:
        return point
    return destination(point, kmh/3.6*seconds, math.atan2(east, north))

def track(center, perimeter=400, angle=0):
    validate(center)
    if not math.isfinite(perimeter) or not 10 <= perimeter <= 100000 or not math.isfinite(angle):
        raise ValueError('跑道周长须为 10～100000 米，朝向须为有限数值')
    r = perimeter/(4+2*math.pi)
    xy = [(r, -r+2*r*i/24) for i in range(25)]
    xy += [(r*math.cos(i*math.pi/48), r+r*math.sin(i*math.pi/48)) for i in range(1,49)]
    xy += [(-r, r-2*r*i/24) for i in range(1,25)]
    xy += [(r*math.cos(math.pi+i*math.pi/48), -r+r*math.sin(math.pi+i*math.pi/48)) for i in range(1,49)]
    theta = math.radians(angle % 360)
    points = [destination(center, math.hypot(x,y), math.atan2(x,y)+theta) for x,y in xy]
    points[-1] = points[0]
    return points

@dataclass
class Route:
    points: list
    progress: float = 0
    completed: bool = False
    def __post_init__(self):
        self.points = [validate(p) for p in self.points]
        if len(self.points)<2:
            raise ValueError('至少需要两个路线点')
        self.cumulative = [0.0]
        for a,b in zip(self.points,self.points[1:]):
            self.cumulative.append(self.cumulative[-1]+distance(a,b))
        self.total = self.cumulative[-1]
        if self.total < 0.1:
            raise ValueError('路线太短')
    def advance(self, meters, loop=False):
        if not math.isfinite(meters) or meters < 0:
            raise ValueError('移动距离无效')
        p = self.progress+meters
        if loop:
            p %= self.total
            self.completed = False
        elif p >= self.total:
            self.progress = self.total
            self.completed = True
            return self.points[-1]
        self.progress = p
        i = min(len(self.points)-2,bisect.bisect_right(self.cumulative,p)-1)
        a,b = self.points[i:i+2]
        lat1,lat2 = math.radians(a[0]), math.radians(b[0])
        dl = math.radians((b[1]-a[1]+540)%360-180)
        bearing = math.atan2(math.sin(dl)*math.cos(lat2),math.cos(lat1)*math.sin(lat2)-math.sin(lat1)*math.cos(lat2)*math.cos(dl))
        return destination(a,p-self.cumulative[i],bearing)
