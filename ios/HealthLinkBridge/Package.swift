// swift-tools-version: 5.10
import PackageDescription

let package = Package(
    name: "HealthLinkBridgeCore",
    platforms: [.iOS(.v17)],
    products: [.library(name: "HealthLinkBridgeCore", targets: ["HealthLinkBridgeCore"])],
    targets: [
        .target(name: "HealthLinkBridgeCore"),
        .testTarget(name: "HealthLinkBridgeCoreTests", dependencies: ["HealthLinkBridgeCore"])
    ]
)
