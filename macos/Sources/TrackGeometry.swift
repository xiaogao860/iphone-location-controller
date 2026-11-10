import Foundation
import CoreLocation
struct TrackGeometry {
    static func generate(center:CLLocationCoordinate2D,circumference:Double,angle:Double)->[CLLocationCoordinate2D] {
        // Stadium: two straight sections of length 2r and two semicircles.
        let r=circumference/(4+2 * Double.pi),theta=angle.truncatingRemainder(dividingBy:360) * .pi/180
        var local=[(Double,Double)]()
        for i in 0...24 {let t=Double(i)/24;local.append((r,-r+2*r*t))}
        for i in 1...48 {let a=Double(i)/48 * Double.pi;local.append((r*cos(a),r+r*sin(a)))}
        for i in 1...24 {let t=Double(i)/24;local.append((-r,r-2*r*t))}
        for i in 1...48 {let a=Double.pi+Double(i)/48 * Double.pi;local.append((r*cos(a),-r+r*sin(a)))}
        var result=local.map { east,north -> CLLocationCoordinate2D in
            let e=east*cos(theta)+north*sin(theta),n=north*cos(theta)-east*sin(theta)
            let distance=hypot(e,n),bearing=atan2(e,n),delta=distance/6371008.8
            let lat=center.latitude * .pi/180,lon=center.longitude * .pi/180
            let targetLat=asin(sin(lat)*cos(delta)+cos(lat)*sin(delta)*cos(bearing))
            let targetLon=lon+atan2(sin(bearing)*sin(delta)*cos(lat),cos(delta)-sin(lat)*sin(targetLat))
            return CLLocationCoordinate2D(latitude:targetLat*180 / .pi,longitude:(targetLon*180 / .pi+540).truncatingRemainder(dividingBy:360)-180)
        }
        if let first=result.first {result[result.count-1]=first}
        return result
    }
}
