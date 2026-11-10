import Cocoa
import MapKit

final class App: NSObject, NSApplicationDelegate, NSWindowDelegate, MKMapViewDelegate {
    var window: NSWindow!
    var process: Process?, input: FileHandle?
    var buffer = "", keys = Set<UInt16>()
    var ready = false, moving = false, pending = false, quitting = false
    var lat = 40.158649, lon = 116.286210
    var last = Date(), lastSend = Date.distantPast
    let latField = NSTextField(string: "40.158649"), lonField = NSTextField(string: "116.286210")
    let speed = NSTextField(string: "5.0")
    let status = NSTextField(wrappingLabelWithString: "请用 USB 连接并解锁 iPhone，开启开发者模式。")
    let position = NSTextField(wrappingLabelWithString: "尚未发送模拟位置")
    let connect = NSButton(title: "连接手机", target: nil, action: nil)
    let toggle = NSButton(title: "开始 WASD 控制", target: nil, action: nil)
    let restore = NSButton(title: "恢复真实定位 / 断开", target: nil, action: nil)
    var timer: Timer?
    let map = MKMapView()
    let pin = MKPointAnnotation()
    let locationSource=NSTextField(labelWithString:"默认位置：北京邮电大学沙河校区操场中心")
    let mapMode=NSSegmentedControl(labels:["选择起点","绘制路线"],trackingMode:.selectOne,target:nil,action:nil)
    let routeInfo=NSTextField(labelWithString:"路线：未设置")
    let routeStart=NSButton(title:"开始路线跑步",target:nil,action:nil)
    let loop=NSButton(checkboxWithTitle:"循环路线",target:nil,action:nil)
    var routePoints=[CLLocationCoordinate2D](), routePins=[MKPointAnnotation]()
    var routeEngine:RouteMotion?, autoRunning=false, locationResolved=false, manuallySelected=true
    var routeLine:MKPolyline?
    let trackLength=NSTextField(string:"400")
    let trackAngle=NSTextField(string:"0")
    var trackCenter:CLLocationCoordinate2D?
    let coordinateCorrection=NSButton(checkboxWithTitle:"中国地图坐标校正（GCJ-02 → GPS）",target:nil,action:nil)
    func applicationDidFinishLaunching(_ notification: Notification) {
        window = NSWindow(contentRect: NSRect(x:0,y:0,width:760,height:895), styleMask:[.titled,.closable,.miniaturizable], backing:.buffered, defer:false)
        window.title = "iPhone 定位控制器"; window.delegate = self; window.center()
        let root = NSStackView(); root.orientation = .vertical; root.alignment = .leading; root.spacing = 11
        root.translatesAutoresizingMaskIntoConstraints = false
        window.contentView!.addSubview(root)
        NSLayoutConstraint.activate([root.leadingAnchor.constraint(equalTo:window.contentView!.leadingAnchor,constant:28),root.trailingAnchor.constraint(equalTo:window.contentView!.trailingAnchor,constant:-28),root.topAnchor.constraint(equalTo:window.contentView!.topAnchor,constant:25)])
        let title = NSTextField(labelWithString:"用键盘控制 iPhone 的模拟位置")
        title.font = .boldSystemFont(ofSize:22); root.addArrangedSubview(title)
        root.addArrangedSubview(NSTextField(wrappingLabelWithString:"W 向北 · S 向南 · A 向西 · D 向东\n按住移动，松开停下；斜向移动保持相同速度。"))
        map.translatesAutoresizingMaskIntoConstraints=false
        map.heightAnchor.constraint(equalToConstant:220).isActive=true
        map.mapType = .hybrid
        map.showsZoomControls=true; map.showsCompass=true; map.delegate=self
        let center=CLLocationCoordinate2D(latitude:lat,longitude:lon)
        pin.coordinate=center; pin.title="起始位置"; map.addAnnotation(pin)
        map.addGestureRecognizer(NSClickGestureRecognizer(target:self,action:#selector(selectMapPoint(_:))))
        root.addArrangedSubview(map)
        map.widthAnchor.constraint(equalTo:root.widthAnchor).isActive=true
        mapMode.selectedSegment=0; root.addArrangedSubview(mapMode)
        root.addArrangedSubview(NSTextField(labelWithString:"单击选点，拖动地图，＋ / − 缩放；绘制路线时依次点击途经点。"))
        root.addArrangedSubview(locationSource)
        let routeButtons=NSStackView(); routeButtons.orientation = .horizontal; routeButtons.spacing=10
        for (name,action) in [("撤销末点",#selector(undoPoint)),("清空路线",#selector(clearRoute))] {
            let b=NSButton(title:name,target:self,action:action); b.bezelStyle = .rounded; routeButtons.addArrangedSubview(b)
        }
        routeStart.target=self; routeStart.action=#selector(startRoute); routeStart.isEnabled=false; routeStart.bezelStyle = .rounded
        routeButtons.addArrangedSubview(routeStart); routeButtons.addArrangedSubview(loop)
        root.addArrangedSubview(routeButtons)
        let trackRow=NSStackView();trackRow.orientation = .horizontal;trackRow.spacing=8
        trackRow.addArrangedSubview(NSTextField(labelWithString:"跑道周长(m)"));trackLength.widthAnchor.constraint(equalToConstant:65).isActive=true;trackRow.addArrangedSubview(trackLength)
        trackRow.addArrangedSubview(NSTextField(labelWithString:"朝向(°)"));trackAngle.widthAnchor.constraint(equalToConstant:55).isActive=true;trackRow.addArrangedSubview(trackAngle)
        let generate=NSButton(title:"一键生成跑道",target:self,action:#selector(generateTrack));generate.bezelStyle = .rounded;trackRow.addArrangedSubview(generate)
        root.addArrangedSubview(trackRow);root.addArrangedSubview(routeInfo)
        for (label, field) in [("起始纬度",latField),("起始经度",lonField),("速度（km/h）",speed)] {
            let row = NSStackView(); row.orientation = .horizontal; row.spacing = 12
            let text = NSTextField(labelWithString:label); text.widthAnchor.constraint(equalToConstant:125).isActive = true
            field.widthAnchor.constraint(equalToConstant:200).isActive = true
            row.addArrangedSubview(text); row.addArrangedSubview(field); root.addArrangedSubview(row)
        }
        root.addArrangedSubview(NSTextField(wrappingLabelWithString:"地图坐标按 GCJ-02 校正后发送给 GPS；非中国底图可关闭校正。速度无上限。\n编辑框输入结束后，点击“开始控制”再使用 WASD。"))
        coordinateCorrection.state = .on;root.addArrangedSubview(coordinateCorrection)
        let buttons = NSStackView(); buttons.orientation = .horizontal; buttons.spacing = 10
        connect.target = self; connect.action = #selector(connectPhone)
        toggle.target = self; toggle.action = #selector(toggleMovement); toggle.isEnabled = false
        restore.target = self; restore.action = #selector(stop); restore.isEnabled = false
        for b in [connect,toggle,restore] { b.bezelStyle = .rounded; buttons.addArrangedSubview(b) }
        root.addArrangedSubview(buttons); root.addArrangedSubview(position); root.addArrangedSubview(status)
        status.textColor = .secondaryLabelColor
        NSEvent.addLocalMonitorForEvents(matching:[.keyDown,.keyUp]) { [weak self] e in
            guard let self = self, self.moving, self.window.isKeyWindow,
                  !(self.window.firstResponder is NSTextView), [0,1,2,13].contains(Int(e.keyCode)),
                  !e.modifierFlags.contains(.command), !e.modifierFlags.contains(.control) else { return e }
            if e.type == .keyDown { self.keys.insert(e.keyCode) } else { self.keys.remove(e.keyCode) }
            return nil
        }
        NotificationCenter.default.addObserver(forName:NSWindow.didResignKeyNotification,object:window,queue:.main) { [weak self] _ in self?.keys.removeAll() }
        timer = Timer.scheduledTimer(withTimeInterval:0.25,repeats:true) { [weak self] _ in self?.tick() }
        window.makeKeyAndOrderFront(nil); NSApp.activate(ignoringOtherApps:true)
        window.contentView!.layoutSubtreeIfNeeded()
        map.setRegion(MKCoordinateRegion(center:center,latitudinalMeters:350,longitudinalMeters:350),animated:false)
    }
    @objc func selectMapPoint(_ gesture:NSClickGestureRecognizer) {
        guard !moving && !autoRunning else { return }
        let c=map.convert(gesture.location(in:map),toCoordinateFrom:map)
        guard CLLocationCoordinate2DIsValid(c),abs(c.latitude)<=85 else { return }
        if mapMode.selectedSegment==1 {
            if let previous=routePoints.last, CLLocation(latitude:previous.latitude,longitude:previous.longitude).distance(from:CLLocation(latitude:c.latitude,longitude:c.longitude))<0.1 { return }
            trackCenter=nil;routePoints.append(c); updateRoute(); window.makeFirstResponder(window.contentView); return
        }
        trackCenter=nil;manuallySelected=true; locationSource.stringValue="起点来源：地图选点"
        lat=c.latitude; lon=c.longitude; pin.coordinate=c; pin.title="起始位置"
        if !map.annotations.contains(where:{$0 === pin}) { map.addAnnotation(pin) }
        latField.stringValue=String(format:"%.6f",lat); lonField.stringValue=String(format:"%.6f",lon)
        status.stringValue="已选择地图起点。点击开始控制后生效。"
        window.makeFirstResponder(window.contentView)
    }
    func coordinates() -> Bool {
        guard let a = Double(latField.stringValue), let b = Double(lonField.stringValue), a.isFinite,b.isFinite,abs(a)<=85,abs(b)<=180 else { status.stringValue="请输入有效坐标：纬度 -85～85，经度 -180～180。"; return false }
        lat=a; lon=b; pin.coordinate=CLLocationCoordinate2D(latitude:a,longitude:b); return true
    }
    @objc func connectPhone() {
        guard process == nil else { return }
        let p = Process(), stdinPipe = Pipe(), stdoutPipe = Pipe(), stderrPipe = Pipe()
        let resources = Bundle.main.resourceURL!
        p.executableURL = URL(fileURLWithPath:"/usr/bin/python3")
        p.arguments = ["-u",resources.appendingPathComponent("backend.py").path]
        var env = ProcessInfo.processInfo.environment
        env["PYTHONPATH"] = resources.appendingPathComponent("python").path
        env["PYTHONUNBUFFERED"]="1"; p.environment=env
        p.standardInput=stdinPipe; p.standardOutput=stdoutPipe; p.standardError=stderrPipe
        buffer=""; input=stdinPipe.fileHandleForWriting; process=p
        stdoutPipe.fileHandleForReading.readabilityHandler = { [weak self] h in
            let data=h.availableData; guard !data.isEmpty else { h.readabilityHandler=nil; return }
            let text=String(decoding:data,as:UTF8.self)
            DispatchQueue.main.async { self?.receive(text) }
        }
        stderrPipe.fileHandleForReading.readabilityHandler = { h in if h.availableData.isEmpty { h.readabilityHandler=nil } }
        p.terminationHandler = { [weak self] _ in DispatchQueue.main.async { self?.finished() } }
        connect.isEnabled=false; restore.isEnabled=true; status.stringValue="正在连接…"
        do { try p.run() } catch { status.stringValue=error.localizedDescription; finished() }
    }
    func receive(_ text:String) {
        buffer += text
        while let r=buffer.range(of:"\n") {
            let line=String(buffer[..<r.lowerBound]); buffer.removeSubrange(..<r.upperBound)
            guard let data=line.data(using:.utf8), let j=(try? JSONSerialization.jsonObject(with:data)) as? [String:Any], let event=j["event"] as? String else { continue }
            switch event {
            case "ready": ready=true; toggle.isEnabled=true; routeStart.isEnabled=routePoints.count>=2; status.stringValue="手机已连接。点击开始控制，将发送起始坐标。"
            case "status": status.stringValue=j["message"] as? String ?? ""
            case "position": pending=false; pin.coordinate=CLLocationCoordinate2D(latitude:j["lat"] as? Double ?? lat,longitude:j["lon"] as? Double ?? lon); pin.title="模拟位置"; position.stringValue=String(format:"地图：%.6f, %.6f\n已发送 GPS：%.6f, %.6f",j["lat"] as? Double ?? lat,j["lon"] as? Double ?? lon,j["gpsLat"] as? Double ?? lat,j["gpsLon"] as? Double ?? lon)
            case "cleared": status.stringValue="已发送恢复真实定位指令，请在手机地图确认。"
            case "error": autoRunning=false; routeStart.title="开始路线跑步"; status.stringValue=j["message"] as? String ?? "连接错误"; moving=false; keys.removeAll(); toggle.isEnabled=false; pending=false
            default: break
            }
        }
    }
    func send(_ object:[String:Any]) {
        guard let data=try? JSONSerialization.data(withJSONObject:object) else { return }
        do { try input?.write(contentsOf:data + Data([10])) } catch { status.stringValue="连接写入失败，请断开后重连。"; moving=false }
    }
    func mapView(_ mapView:MKMapView,rendererFor overlay:MKOverlay)->MKOverlayRenderer {
        let r=MKPolylineRenderer(overlay:overlay); r.strokeColor = .systemBlue; r.lineWidth=4; return r
    }
    func updateRoute() {
        if let line=routeLine { map.removeOverlay(line) }; map.removeAnnotations(routePins); routePins=[]
        if routePoints.count>=2 { let line=MKPolyline(coordinates:routePoints,count:routePoints.count); routeLine=line; map.addOverlay(line) }
        for (i,c) in routePoints.enumerated() { if routePoints.count>20 && i % 24 != 0 {continue};let p=MKPointAnnotation();p.coordinate=c;p.title="路线点 \(i+1)";routePins.append(p) }; map.addAnnotations(routePins)
        let length=RouteMotion(routePoints).total
        routeInfo.stringValue=String(format:"路线：%d 个点 · %.0f 米（按选点直线连接）",routePoints.count,length)
        routeStart.isEnabled=ready && routePoints.count>=2
        routeEngine=nil; routeStart.title="开始路线跑步"
    }
    @objc func generateTrack() {
        guard !moving && !autoRunning else {status.stringValue="请先暂停移动再生成跑道。";return}
        guard let circumference=Double(trackLength.stringValue),circumference.isFinite,circumference>=10,circumference<=100000,
              let angle=Double(trackAngle.stringValue),angle.isFinite else {status.stringValue="跑道周长请输入 10～100000 米，朝向请输入有效角度。";return}
        // First drawn point takes priority; otherwise the selected start is the track center.
        var center:CLLocationCoordinate2D
        if let saved=trackCenter {center=saved}
        else if let first=routePoints.first {center=first}
        else {guard manuallySelected else {status.stringValue="请先在地图选跑道中心；不会默认使用 Mac 位置。";return};guard coordinates() else {return};center=CLLocationCoordinate2D(latitude:lat,longitude:lon)}
        trackCenter=center
        routePoints=TrackGeometry.generate(center:center,circumference:circumference,angle:angle)
        updateRoute();loop.state = .on;mapMode.selectedSegment=1
        if let line=routeLine {map.setVisibleMapRect(line.boundingMapRect,edgePadding:NSEdgeInsets(top:30,left:30,bottom:30,right:30),animated:true)}
        window.makeFirstResponder(window.contentView)
        status.stringValue="已生成闭合跑道。中心取已有路线首点或选定起点；0° 长轴朝北。"
    }
    @objc func undoPoint() { guard !autoRunning && !moving else { return }; if !routePoints.isEmpty {routePoints.removeLast()};updateRoute() }
    @objc func clearRoute() { guard !autoRunning && !moving else { return };routePoints=[];trackCenter=nil;updateRoute() }
    @objc func startRoute() {
        if autoRunning { autoRunning=false; routeStart.title="继续路线跑步"; status.stringValue="路线已暂停，模拟位置保持。";return }
        guard ready,routePoints.count>=2,let s=validSpeed(),s>0 else { status.stringValue="请连接手机、绘制至少两个路线点，并设置大于 0 的速度。";return }
        moving=false;keys.removeAll();toggle.title="开始 WASD 控制"
        if routeEngine == nil || routeEngine!.completed {
            routeEngine=RouteMotion(routePoints)
            guard routeEngine!.total>0.1 else {status.stringValue="路线太短，请选择不同位置。";return}
            lat=routePoints[0].latitude;lon=routePoints[0].longitude
        }
        autoRunning=true; routeStart.title="暂停路线跑步";latField.isEnabled=false;lonField.isEnabled=false
        last=Date();lastSend = .distantPast;window.makeFirstResponder(window.contentView)
        status.stringValue="沿路线自动移动中。切换窗口后仍继续；可点击暂停。"
    }
    @objc func toggleMovement() {
        autoRunning=false;routeStart.title="开始路线跑步";routeEngine=nil
        if moving { moving=false; keys.removeAll(); toggle.title="继续 WASD 控制"; status.stringValue="已暂停移动，模拟位置仍保持；恢复请点右侧按钮。"; return }
        guard ready, coordinates(), validSpeed() != nil else { return }
        window.makeFirstResponder(window.contentView); moving=true; last=Date(); lastSend = .distantPast
        toggle.title="暂停移动"; latField.isEnabled=false; lonField.isEnabled=false
        status.stringValue="控制中：按住 WASD 移动。窗口失去焦点时停止移动。"
    }
    func validSpeed() -> Double? {
        guard let s=Double(speed.stringValue),s.isFinite,s>=0 else { status.stringValue="速度请输入有效的非负数（km/h），无上限。"; return nil }; return s
    }
    func tick() {
        let now=Date(),dt=min(now.timeIntervalSince(last),0.5); last=now
        guard (moving || autoRunning),ready,!pending,let kmh=validSpeed() else { return }
        if autoRunning {
            let c=routeEngine!.advance(kmh/3.6*dt,looping:loop.state == .on)
            lat=c.latitude;lon=c.longitude
            pending=true;lastSend=now;send(["action":"set","lat":lat,"lon":lon,"coordinateSystem":coordinateCorrection.state == .on ? "gcj02" : "wgs84"])
            latField.stringValue=String(format:"%.6f",lat);lonField.stringValue=String(format:"%.6f",lon)
            routeInfo.stringValue=String(format:"路线进度：%.0f / %.0f 米",routeEngine!.travelled,routeEngine!.total)
            if routeEngine!.completed {autoRunning=false;routeStart.title="重新跑路线";status.stringValue="路线已完成，停在终点。恢复真实定位请点击恢复按钮。"}
            return
        }
        var north=0.0,east=0.0
        if window.isKeyWindow && !(window.firstResponder is NSTextView) {
            north=(keys.contains(13) ? 1:0)-(keys.contains(1) ? 1:0)
            east=(keys.contains(2) ? 1:0)-(keys.contains(0) ? 1:0)
        } else { keys.removeAll() }
        let length=hypot(north,east)
        if length>0 {
            let distance=kmh/3.6*dt
            guard distance.isFinite else { status.stringValue="数值超过可计算范围，请调整速度。"; return }
            lat=max(-85,min(85,lat+north/length*distance/111320))
            lon += east/length*distance/(111320*cos(lat * .pi/180))
            lon=(lon+540).truncatingRemainder(dividingBy:360)-180
        }
        if length>0 || now.timeIntervalSince(lastSend)>=1 {
            pending=true; lastSend=now; send(["action":"set","lat":lat,"lon":lon,"coordinateSystem":coordinateCorrection.state == .on ? "gcj02" : "wgs84"])
            latField.stringValue=String(format:"%.6f",lat); lonField.stringValue=String(format:"%.6f",lon)
        }
    }
    @objc func stop() {
        moving=false;autoRunning=false; ready=false; keys.removeAll(); toggle.isEnabled=false; routeStart.isEnabled=false;restore.isEnabled=false
        status.stringValue="正在清除模拟定位…"; send(["action":"stop"])
    }
    func finished() {
        process=nil; input=nil; ready=false; moving=false; autoRunning=false;routeStart.isEnabled=false;routeStart.title="开始路线跑步"; pending=false; keys.removeAll()
        connect.isEnabled=true; toggle.isEnabled=false; restore.isEnabled=false; toggle.title="开始 WASD 控制"
        latField.isEnabled=true; lonField.isEnabled=true
        if !status.stringValue.contains("恢复") && !status.stringValue.contains("错误") { status.stringValue += "（连接已结束）" }
        if quitting { NSApp.reply(toApplicationShouldTerminate:true) }
    }
    func windowShouldClose(_ sender:NSWindow) -> Bool { NSApp.terminate(nil); return false }
    func applicationShouldTerminate(_ sender:NSApplication) -> NSApplication.TerminateReply {
        if process != nil { quitting=true; stop(); return .terminateLater }; return .terminateNow
    }
}
let app=NSApplication.shared
let delegate=App(); app.delegate=delegate; app.setActivationPolicy(.regular); app.run()
