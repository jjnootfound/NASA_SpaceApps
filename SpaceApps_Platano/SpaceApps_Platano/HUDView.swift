//
//  HUDView.swift
//  SpaceApps_Platano
//
//  Created by Fermin Gomez on 04/10/25.
//

import SwiftUI

struct HUDView: View {
    @ObservedObject var game: GameState

    var body: some View {
        HStack {
            Text("Score: \(game.score)")
                .font(.headline)
                .padding(.horizontal, 10)
                .padding(.vertical, 6)
                .background(.ultraThinMaterial)
                .clipShape(RoundedRectangle(cornerRadius: 10))

            Spacer()

            Button("Reset") { game.reset() }
                .buttonStyle(.bordered)

            Button("Clear") {
                NotificationCenter.default.post(name: .clearScene, object: nil)
            }
            .buttonStyle(.borderedProminent)
            Button("Recenter") {
                NotificationCenter.default.post(name: .recenterCockpit, object: nil)
            }
            .buttonStyle(.bordered)
        }
        .padding()
    }
}
