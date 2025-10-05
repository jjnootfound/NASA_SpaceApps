//
//  GameState.swift
//  SpaceApps_Platano
//
//  Created by Fermin Gomez on 04/10/25.
//

import Foundation
import Combine

final class GameState: ObservableObject {
	@Published var score: Int = 0
	func add(points: Int) { score += points }
	func reset() { score = 0 }
}
