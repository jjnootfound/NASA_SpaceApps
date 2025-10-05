//
//  ARViewIOS.swift
//  SpaceApps_Platano
//
//  Created by Fermin Gomez on 04/10/25.
//

#if os(iOS)
import UIKit
import SwiftUI
import RealityKit
import ARKit
import simd
import Combine   // for AnyCancellable

// Convenience: get xyz from a simd_float4 (matrix column)
private extension simd_float4 {
    var xyz: SIMD3<Float> { SIMD3(x, y, z) }
}

struct ARViewIOS: UIViewRepresentable {
    @ObservedObject var game: GameState

    final class Coordinator {
        let parent: ARViewIOS
        var collisionSub: AnyCancellable?

        init(_ parent: ARViewIOS) { self.parent = parent }

        // Tap handler: check cockpit buttons first
        @objc func handleTap(_ recognizer: UITapGestureRecognizer) {
            guard let arView = recognizer.view as? ARView else { return }
            let loc = recognizer.location(in: arView)

            if let entity = arView.entity(at: loc),
               (entity.name == CockpitBuilder.Names.btnA || entity.name == CockpitBuilder.Names.btnB) {
                press(button: entity, in: arView)
                return
            }
            // (No world gameplay for the demo; just return.)
            return
        }

        // Button feedback + simple toggle animation
        fileprivate func press(button: Entity, in arView: ARView) {
            guard let model = button as? ModelEntity,
                  var simple = (model.model?.materials.first as? SimpleMaterial) else { return }

            UIImpactFeedbackGenerator(style: .light).impactOccurred()

            let wasGreen = (simple.color.tint == .systemGreen)
            simple.color = .init(tint: wasGreen ? .systemYellow : .systemGreen, texture: nil)
            model.model?.materials = [simple]

            let original = model.position
            let down = original + SIMD3<Float>(0, -0.006, 0)
            model.move(
                to: Transform(scale: .one, rotation: model.orientation, translation: down),
                relativeTo: model.parent, duration: 0.07, timingFunction: .easeInOut
            )
            DispatchQueue.main.asyncAfter(deadline: .now() + 0.12) {
                model.move(
                    to: Transform(scale: .one, rotation: model.orientation, translation: original),
                    relativeTo: model.parent, duration: 0.07, timingFunction: .easeInOut
                )
            }

            parent.game.add(points: 5)
        }

        // (Optional) collisions—leave empty unless you re-enable balls/targets
        func setUpCollisions(for arView: ARView) {
            collisionSub = arView.scene.publisher(for: CollisionEvents.Began.self).sink { _ in }
        }
    }

    func makeCoordinator() -> Coordinator { Coordinator(self) }

    func makeUIView(context: Context) -> ARView {
        let view = ARView(frame: .zero)

        // World tracking; no plane detection needed for seated demo
        let cfg = ARWorldTrackingConfiguration()
        cfg.planeDetection = []
        cfg.environmentTexturing = .automatic
        view.session.run(cfg)

        // --- Place the Cupola shell around the user, plus our small panel+buttons ---
        func placeCockpit() {
            // Remove previous cockpit anchors
            view.scene.anchors.filter { $0.name == "cockpitAnchor" }.forEach { $0.removeFromParent() }

            // Current camera pose → place model at the camera, facing forward (yaw only)
            let cam = view.cameraTransform
            let forward = -cam.matrix.columns.2.xyz
            let pos = cam.translation
            let yaw = atan2f(forward.x, forward.z)
            let yawRot = simd_quatf(angle: yaw, axis: [0, 1, 0])

            // World anchor
            let cockpitAnchor = AnchorEntity(world: pos)
            cockpitAnchor.name = "cockpitAnchor"

            // Load Cupola.usdz from app bundle
            guard let url = Bundle.main.url(forResource: "Cupola", withExtension: "usdz") else {
                assertionFailure("Cupola.usdz not found in app bundle"); return
            }
            let cupola = try! Entity.loadModel(contentsOf: url)
            cupola.transform.rotation = yawRot

            // SCALE FIX — un-comment ONE if needed based on Fusion units:
            // cupola.scale *= 0.001  // mm → m
            // cupola.scale *= 0.01   // cm → m

            // Slight vertical nudge
            cupola.position.y -= 0.05

            // Enable hit-testing on submeshes (useful later)
            cupola.generateCollisionShapes(recursive: true)

            cockpitAnchor.addChild(cupola)

            // --- Minimal panel + two buttons in front of user (for the demo) ---
            let root = Entity()
            root.position = [0, -0.05, 0]
            root.orientation = yawRot
            cockpitAnchor.addChild(root)

            let panel = CockpitBuilder.makePanel()
            panel.orientation = simd_quatf(angle: -.pi * 0.08, axis: [1, 0, 0])
            panel.position = [0, 0.0, -0.65]    // ~65 cm ahead
            root.addChild(panel)

            let btnA = CockpitBuilder.makeButton(name: CockpitBuilder.Names.btnA, color: UIColor.systemGreen)
            btnA.position = [-0.18, 0.02, 0.03]
            let btnB = CockpitBuilder.makeButton(name: CockpitBuilder.Names.btnB, color: UIColor.systemRed)
            btnB.position = [ 0.18, 0.02, 0.03]
            panel.addChild(btnA)
            panel.addChild(btnB)

            view.scene.addAnchor(cockpitAnchor)
        }

        // Place once (small delay so camera pose is valid)
        DispatchQueue.main.asyncAfter(deadline: .now() + 0.05) { placeCockpit() }

        // Tap gesture
        let tap = UITapGestureRecognizer(target: context.coordinator, action: #selector(Coordinator.handleTap(_:)))
        view.addGestureRecognizer(tap)

        // Clear → re-place
        NotificationCenter.default.addObserver(forName: .clearScene, object: nil, queue: .main) { _ in
            view.scene.anchors.forEach { $0.removeFromParent() }
            placeCockpit()
        }

        // Recenter → re-place
        NotificationCenter.default.addObserver(forName: .recenterCockpit, object: nil, queue: .main) { _ in
            placeCockpit()
        }

        return view
    }

    func updateUIView(_ uiView: ARView, context: Context) {}
}
#endif
