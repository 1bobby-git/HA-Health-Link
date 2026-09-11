import Foundation

public struct HealthLinkSource: Codable, Sendable {
    public var bundleIdentifier: String?
    public var name: String?
    public var productType: String?
    public var deviceName: String?
    public var sourceVersion: String?
    enum CodingKeys: String, CodingKey { case bundleIdentifier = "bundle_identifier"; case name; case productType = "product_type"; case deviceName = "device_name"; case sourceVersion = "source_version" }
}

public struct HealthLinkItem: Codable, Sendable {
    public var objectKind: String
    public var typeID: String
    public var sampleUUID: String
    public var start: String
    public var end: String
    public var numericValue: Double?
    public var textValue: String?
    public var unit: String?
    public var domain: String
    public var privacyClass: String
    public var source: HealthLinkSource?
    public var payload: JSONValue?
    public var metadata: [String: JSONValue]?
    enum CodingKeys: String, CodingKey { case objectKind = "object_kind"; case typeID = "type_id"; case sampleUUID = "sample_uuid"; case start,end; case numericValue = "numeric_value"; case textValue = "text_value"; case unit,domain; case privacyClass = "privacy_class"; case source,payload,metadata }
}

public struct HealthLinkEnvelope: Codable, Sendable {
    public var schemaVersion: Int = 1
    public var profileID: String
    public var bridgeID: String
    public var sequence: Int64
    public var sentAt: String
    public var items: [HealthLinkItem]
    enum CodingKeys: String, CodingKey { case schemaVersion = "schema_version"; case profileID = "profile_id"; case bridgeID = "bridge_id"; case sequence; case sentAt = "sent_at"; case items }
}

public enum JSONValue: Codable, Sendable {
    case string(String), number(Double), bool(Bool), object([String: JSONValue]), array([JSONValue]), null
    public init(from decoder: Decoder) throws {
        let c=try decoder.singleValueContainer()
        if c.decodeNil(){self = .null}else if let v=try? c.decode(Bool.self){self = .bool(v)}else if let v=try? c.decode(Double.self){self = .number(v)}else if let v=try? c.decode(String.self){self = .string(v)}else if let v=try? c.decode([String:JSONValue].self){self = .object(v)}else{self = .array(try c.decode([JSONValue].self))}
    }
    public func encode(to encoder: Encoder) throws {
        var c=encoder.singleValueContainer()
        switch self { case .string(let v):try c.encode(v); case .number(let v):try c.encode(v); case .bool(let v):try c.encode(v); case .object(let v):try c.encode(v); case .array(let v):try c.encode(v); case .null:try c.encodeNil() }
    }
}
