//
//  CockpitBuilder.swift
//  SpaceApps_Platano
//
//  Created by Fermin Gomez on 04/10/25.
//

import UIKit
import RealityKit
import simd

enum CockpitBuilder {
    struct Names {
        static let root   = "cockpitRoot"
        static let panel  = "panel"
        static let btnA   = "buttonA"
        static let btnB   = "buttonB"
        static let labelA = "labelA"
        static let labelB = "labelB"
    }

    static func makeCockpitRoot() -> Entity {
        let root = Entity()
        root.name = Names.root
        return root
    }

    // BIGGER, THICKER, DARKER panel (box instead of plane)
    static func makePanel(width: Float = 0.52, depth: Float = 0.22, thickness: Float = 0.02) -> ModelEntity {
        let mesh = MeshResource.generateBox(size: [width, thickness, depth], cornerRadius: 0.02)
        let mat  = SimpleMaterial(color: UIColor(white: 0.08, alpha: 0.95), roughness: 0.9, isMetallic: false)
        let panel = ModelEntity(mesh: mesh, materials: [mat])
        panel.name = Names.panel
        panel.generateCollisionShapes(recursive: true)
        panel.components.set(PhysicsBodyComponent(mode: .static))
        return panel
    }

    static func makeButton(name: String, color: UIColor) -> ModelEntity {
        let mesh = MeshResource.generateBox(size: [0.07, 0.02, 0.07], cornerRadius: 0.012)
        let mat  = SimpleMaterial(color: color, roughness: 0.3, isMetallic: true)
        let btn  = ModelEntity(mesh: mesh, materials: [mat])
        btn.name = name
        btn.generateCollisionShapes(recursive: true)
        btn.components.set(PhysicsBodyComponent(mode: .kinematic))
        return btn
    }

    static func makeLabel(width: Float = 0.10, textColor: UIColor = .white) -> ModelEntity {
        let mesh = MeshResource.generateBox(size: [width, 0.006, 0.024], cornerRadius: 0.003)
        let mat  = SimpleMaterial(color: textColor.withAlphaComponent(0.08), roughness: 1, isMetallic: false)
        let label = ModelEntity(mesh: mesh, materials: [mat])
        return label
    }

    // Simple frame rails so it looks like “cockpit”
    static func makeRails() -> Entity {
        let rails = Entity()

        func rail(width: Float, height: Float, depth: Float, color: UIColor) -> ModelEntity {
            let m = MeshResource.generateBox(size: [width, height, depth], cornerRadius: 0.012)
            let mat = SimpleMaterial(color: color, roughness: 0.6, isMetallic: true)
            let e = ModelEntity(mesh: m, materials: [mat])
            return e
        }

        let sideColor = UIColor(white: 0.10, alpha: 1.0)
        let topColor  = UIColor(white: 0.12, alpha: 1.0)

        // side rails
        let left  = rail(width: 0.04, height: 0.10, depth: 0.26, color: sideColor)
        let right = rail(width: 0.04, height: 0.10, depth: 0.26, color: sideColor)
        left.position  = [-0.29, 0.04, 0.0]
        right.position = [ 0.29, 0.04, 0.0]

        // top bezel
        let top = rail(width: 0.56, height: 0.06, depth: 0.04, color: topColor)
        top.position = [0.0, 0.09, -0.08]
        top.orientation = simd_quatf(angle: -.pi * 0.05, axis: [1,0,0])

        rails.addChild(left)
        rails.addChild(right)
        rails.addChild(top)
        return rails
    }

}
extension CockpitBuilder {
    static func makeSideWall(width: Float = 0.05, height: Float = 0.30, depth: Float = 0.60) -> ModelEntity {
        let mesh = MeshResource.generateBox(size: [width, height, depth], cornerRadius: 0.02)
        let mat  = SimpleMaterial(color: UIColor(white: 0.10, alpha: 1.0), roughness: 0.8, isMetallic: false)
        let wall = ModelEntity(mesh: mesh, materials: [mat])
        wall.generateCollisionShapes(recursive: true)
        wall.components.set(PhysicsBodyComponent(mode: .static))
        return wall
    }
    
    static func makeTopArch(radius: Float = 0.36,
                            tube:   Float = 0.025,
                            segments: Int = 24,
                            sweepDegrees: Float = 140) -> Entity {
        // Build an arch out of many small cylinders
        let arch = Entity()
        let color = UIColor(white: 0.12, alpha: 1.0)
        let mat   = SimpleMaterial(color: color, roughness: 0.6, isMetallic: true)

        // Total sweep centered around front (0°). e.g., 140° -> from -70° to +70°
        let startDeg = -sweepDegrees / 2
        let step = sweepDegrees / Float(max(1, segments - 1))

        for i in 0..<segments {
            let deg = startDeg + Float(i) * step
            let rad = deg * .pi / 180

            // Position on a horizontal circle centered above the panel
            let x: Float = radius * sin(rad)
            let y: Float = 0           // we’ll lift the whole arch when placing it
            let z: Float = -radius * cos(rad)

            // A small cylinder oriented tangent to the arch
            let cyl = ModelEntity(
                mesh: .generateCylinder(height: tube * 1.8, radius: tube * 0.5),
                materials: [mat]
            )

            // Rotate so the cylinder points along the tangential direction of the ring
            // Tangent direction around Y axis is approx. yaw = rad
            let yaw   = rad
            let pitch: Float = .pi / 2   // stand the cylinder up from lying flat
            cyl.orientation = simd_quatf(angle: pitch, axis: [1,0,0]) *
                              simd_quatf(angle: yaw,   axis: [0,1,0])
            cyl.position = [x, y, z]

            arch.addChild(cyl)
        }

        return arch
    }

    static func makeCenterStick() -> Entity {
        let root = Entity()

        let shaftMesh = MeshResource.generateCylinder(height: 0.18, radius: 0.012)
        let knobMesh  = MeshResource.generateSphere(radius: 0.028)
        let metal  = SimpleMaterial(color: .darkGray, roughness: 0.4, isMetallic: true)
        let plastic = SimpleMaterial(color: UIColor(white: 0.15, alpha: 1), roughness: 0.8, isMetallic: false)

        let shaft = ModelEntity(mesh: shaftMesh, materials: [metal])
        let knob  = ModelEntity(mesh: knobMesh,  materials: [plastic])

        shaft.position = [0, 0.09, 0]
        knob.position  = [0, 0.18, 0]

        root.addChild(shaft)
        root.addChild(knob)

        // slight tilt toward the user
        root.orientation = simd_quatf(angle: -.pi * 0.12, axis: [1, 0, 0])
        return root
    }
}
