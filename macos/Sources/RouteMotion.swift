import Foundation
import CoreLocation

struct RouteMotion {
    let points: [CLLocationCoordinate2D]
    private(set) var index = 1
    private(set) var offset = 0.0
    private(set) var travelled = 0.0
    private(set) var completed = false
    var lengths: [Double]
    var total: Double { lengths.reduce(0,+) }
    init(_ points: [CLLocationCoordinate2D]) {
        self.points=points
        lengths=zip(points,points.dropFirst()).map { CLLocation(latitude:$0.latitude,longitude:$0.longitude).distance(from:CLLocation(latitude:$1.latitude,longitude:$1.longitude)) }
        completed=points.count<2 || lengths.reduce(0,+)<0.01
    }
    mutating func advance(_ distance:Double, looping:Bool) -> CLLocationCoordinate2D {
        guard points.count>1,total>0.01,distance.isFinite,distance>=0 else { return points.first ?? CLLocationCoordinate2D() }
        if completed { return points.last! }
        var remaining=distance
        if looping && remaining>total { remaining=remaining.truncatingRemainder(dividingBy:total) }
        while index < points.count {
            let available=max(0,lengths[index-1]-offset)
            if remaining<available { offset += remaining; travelled += remaining; break }
            remaining -= available; travelled += available; offset=0; index += 1
            if index==points.count {
                if looping { index=1; travelled=0 } else { completed=true; return points.last! }
            }
        }
        let a=points[index-1], b=points[index], fraction=offset/max(lengths[index-1],0.000001)
        var delta=b.longitude-a.longitude
        if delta>180 {delta-=360}; if delta < -180 {delta+=360}
        let lon=(a.longitude+delta*fraction+540).truncatingRemainder(dividingBy:360)-180
        return CLLocationCoordinate2D(latitude:a.latitude+(b.latitude-a.latitude)*fraction,longitude:lon)
    }
}
