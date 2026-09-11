from pathlib import Path
from custom_components.health_link.storage.db import HealthLinkStore

def test_local_date_uses_home_assistant_timezone(tmp_path:Path)->None:
    store=HealthLinkStore(None,tmp_path/"test.db","profile");store.timezone_name="Asia/Seoul";assert store._local_date("2026-09-10T23:30:00+00:00")=="2026-09-11"
def test_series_chunk_round_trip(tmp_path:Path)->None:
    store=HealthLinkStore(None,tmp_path/"test.db","profile");store.timezone_name="Asia/Seoul";store._initialize_sync("entry","Test","Asia/Seoul");result=store._ingest_sync([{"object_kind":"series_chunk","type_id":"HKDataTypeIdentifierElectrocardiogram","series_uuid":"ecg-1","chunk_index":0,"series_kind":"ecg_voltage","points":[0.1,0.2,0.3],"start":"2026-09-11T00:00:00Z","end":"2026-09-11T00:00:03Z"}],1);assert result["inserted"]==1;assert store._series_chunks_sync("ecg-1",10)[0]["payload"]==[0.1,0.2,0.3]
