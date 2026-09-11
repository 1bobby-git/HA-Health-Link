import CryptoKit
import Foundation

public enum HealthLinkSigner {
    public static func bodySHA256(_ body: Data) -> String { SHA256.hash(data: body).map { String(format: "%02x", $0) }.joined() }
    public static func signature(body: Data,secret: String,timestamp: Int64,sequence: Int64,nonce: String) -> String {
        let hash=bodySHA256(body);let message=Data("\(timestamp).\(sequence).\(nonce).\(hash)".utf8);let key=SymmetricKey(data:Data(secret.utf8))
        return HMAC<SHA256>.authenticationCode(for:message,using:key).map { String(format:"%02x",$0) }.joined()
    }
}
