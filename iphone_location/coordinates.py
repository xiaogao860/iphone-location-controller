"""Local approximate GCJ-02/WGS-84 conversion; iterative inverse.
No network calls. For this app's mainland map coordinate mode only.
"""
import math
A=6378245.0
EE=0.00669342162296594323

def outside_china(lat,lon):
    return not (72.004 <= lon <= 137.8347 and 0.8293 <= lat <= 55.8271)

def _delta(lat,lon):
    x,y=lon-105,lat-35
    dlat=-100+2*x+3*y+0.2*y*y+0.1*x*y+0.2*math.sqrt(abs(x))
    dlat+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
    dlat+=(20*math.sin(y*math.pi)+40*math.sin(y/3*math.pi))*2/3
    dlat+=(160*math.sin(y/12*math.pi)+320*math.sin(y*math.pi/30))*2/3
    dlon=300+x+2*y+0.1*x*x+0.1*x*y+0.1*math.sqrt(abs(x))
    dlon+=(20*math.sin(6*x*math.pi)+20*math.sin(2*x*math.pi))*2/3
    dlon+=(20*math.sin(x*math.pi)+40*math.sin(x/3*math.pi))*2/3
    dlon+=(150*math.sin(x/12*math.pi)+300*math.sin(x/30*math.pi))*2/3
    rad=lat/180*math.pi
    magic=1-EE*math.sin(rad)**2
    root=math.sqrt(magic)
    dlat=dlat*180/((A*(1-EE)/(magic*root))*math.pi)
    dlon=dlon*180/(A/root*math.cos(rad)*math.pi)
    return dlat,dlon

def wgs84_to_gcj02(lat,lon):
    if outside_china(lat,lon):return lat,lon
    a,b=_delta(lat,lon)
    return lat+a,lon+b

def gcj02_to_wgs84(lat,lon):
    if outside_china(lat,lon):return lat,lon
    a,b=lat,lon
    for _ in range(12):
        projected_a,projected_b=wgs84_to_gcj02(a,b)
        da,db=projected_a-lat,projected_b-lon
        a-=da;b-=db
        if max(abs(da),abs(db))<1e-9:break
    return a,b
