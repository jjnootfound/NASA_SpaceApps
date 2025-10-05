//
//  ContentView.swift
//  SpaceApps_Platano
//
//  Created by Fermin Gomez on 04/10/25.
//

import SwiftUI

struct ContentView: View {
    @StateObject private var game = GameState()

    var body: some View {
        ZStack(alignment: .top) {
            // iOS AR camera view (from the file ARViewIOS.swift)
            ARViewIOS(game: game)
                .ignoresSafeArea()

            // Simple score / reset UI
            HUDView(game: game)
        }
    }
}

#Preview {
    ContentView()
}
