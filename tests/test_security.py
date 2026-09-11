import hashlib,hmac
import pytest
from custom_components.health_link.ingest.security import SignatureError,verify_signed_request
from custom_components.health_link.const import WEBHOOK_HEADER_BRIDGE,WEBHOOK_HEADER_NONCE,WEBHOOK_HEADER_SEQUENCE,WEBHOOK_HEADER_SIGNATURE,WEBHOOK_HEADER_TIMESTAMP

def _headers(body,secret,now):
    nonce="abc";sequence=42;digest=hashlib.sha256(body).hexdigest();message=f"{now}.{sequence}.{nonce}.{digest}".encode();signature=hmac.new(secret.encode(),message,hashlib.sha256).hexdigest();return {WEBHOOK_HEADER_BRIDGE:"iphone",WEBHOOK_HEADER_SEQUENCE:str(sequence),WEBHOOK_HEADER_TIMESTAMP:str(now),WEBHOOK_HEADER_NONCE:nonce,WEBHOOK_HEADER_SIGNATURE:signature}
def test_valid_signature():assert verify_signed_request(_headers(b'{"schema_version":1}',"secret",1000),b'{"schema_version":1}',"secret",now=1000).sequence==42
def test_modified_body_is_rejected():
    headers=_headers(b'{}',"secret",1000)
    with pytest.raises(SignatureError):verify_signed_request(headers,b'{"x":1}',"secret",now=1000)
