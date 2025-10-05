//
//  SceneBuilder.swift
//  SpaceApps_Platano
//
//  Created by Fermin Gomez on 04/10/25.
//

import RealityKit

enum SceneBuilder {
	enum Name {
		static let target = "target"
		static let ball   = "ball"
		static let ground = "ground"
	}

	static func makeTarget(radius: Float = 0.06) -> ModelEntity {
		let mesh = MeshResource.generateSphere(radius: radius)
		let material = SimpleMaterial(color: .red, roughness: 0.2, isMetallic: true)
		let e = ModelEntity(mesh: mesh, materials: [material])
		e.name = Name.target

		// Collision + physics
		e.generateCollisionShapes(recursive: true)
		var body = PhysicsBodyComponent()
		body.mode = .dynamic
		body.material = .default            // or custom (see ball)
		// Leave massProperties as default (uses generated collision shape)
		e.components.set(body)
		return e
	}

	static func makeGround(size: Float = 10) -> ModelEntity {
		let mesh = MeshResource.generatePlane(width: size, depth: size)
		let mat = SimpleMaterial(color: .gray, roughness: 0.9, isMetallic: false)
		let e = ModelEntity(mesh: mesh, materials: [mat])
		e.name = Name.ground

		e.generateCollisionShapes(recursive: true)
		var body = PhysicsBodyComponent()
		body.mode = .static                 // ground doesn’t move
		body.material = .default
		e.components.set(body)
		return e
	}

	static func makeBall(radius: Float = 0.04) -> ModelEntity {
		let mesh = MeshResource.generateSphere(radius: radius)
		let mat = SimpleMaterial(color: .white, roughness: 0.3, isMetallic: true)
		let e = ModelEntity(mesh: mesh, materials: [mat])
		e.name = Name.ball

		e.generateCollisionShapes(recursive: true)
		var body = PhysicsBodyComponent()
		body.mode = .dynamic
		// Use the factory to create a material (don’t init directly)
		body.material = PhysicsMaterialResource.generate(friction: 0.6, restitution: 0.2)
		e.components.set(body)
		return e
	}
}
