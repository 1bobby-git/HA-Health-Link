"""SQLite-backed universal local health store for HealthLink."""
from __future__ import annotations

from collections.abc import Iterable, Sequence
from datetime import datetime, timedelta, timezone
import hashlib
import json
import math
from pathlib import Path
import sqlite3
from typing import Any
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from homeassistant.core import HomeAssistant

from ..const import DEFAULT_EXPOSED_TYPE_IDS, MAX_METADATA_BYTES

_SCHEMA = """
CREATE TABLE IF NOT EXISTS profiles(profile_id TEXT PRIMARY KEY,config_entry_id TEXT,display_name TEXT,timezone TEXT,created_at TEXT);
CREATE TABLE IF NOT EXISTS health_types(profile_id TEXT,type_id TEXT,object_kind TEXT,domain TEXT,display_name TEXT,canonical_unit TEXT,aggregation_kind TEXT,privacy_class TEXT DEFAULT 'wellness',exposed INTEGER DEFAULT 0,first_seen TEXT,last_seen TEXT,PRIMARY KEY(profile_id,type_id));
CREATE TABLE IF NOT EXISTS samples(profile_id TEXT,sample_uuid TEXT,type_id TEXT,object_kind TEXT,start_ts TEXT,end_ts TEXT,local_date TEXT,numeric_value REAL,text_value TEXT,canonical_unit TEXT,category_code TEXT,source_key TEXT,source_json TEXT,metadata_json TEXT,deleted INTEGER DEFAULT 0,ingest_seq INTEGER,modified_ts TEXT,PRIMARY KEY(profile_id,sample_uuid));
CREATE INDEX IF NOT EXISTS idx_hl_samples_metric_time ON samples(profile_id,type_id,end_ts) WHERE deleted=0;
CREATE TABLE IF NOT EXISTS structured_objects(profile_id TEXT,object_uuid TEXT,type_id TEXT,object_kind TEXT,start_ts TEXT,end_ts TEXT,payload_json TEXT,source_json TEXT,metadata_json TEXT,deleted INTEGER DEFAULT 0,ingest_seq INTEGER,modified_ts TEXT,PRIMARY KEY(profile_id,object_uuid));
CREATE INDEX IF NOT EXISTS idx_hl_structured_metric_time ON structured_objects(profile_id,type_id,end_ts) WHERE deleted=0;
CREATE TABLE IF NOT EXISTS series_chunks(profile_id TEXT,series_uuid TEXT,chunk_index INTEGER,series_kind TEXT,payload_json TEXT,checksum TEXT,point_count INTEGER,start_ts TEXT,end_ts TEXT,ingest_seq INTEGER,PRIMARY KEY(profile_id,series_uuid,chunk_index));
CREATE TABLE IF NOT EXISTS composer_definitions(profile_id TEXT,id TEXT,name TEXT,version INTEGER DEFAULT 1,enabled INTEGER DEFAULT 1,definition_json TEXT,entity_exposure INTEGER DEFAULT 1,updated_at TEXT,PRIMARY KEY(profile_id,id));
CREATE TABLE IF NOT EXISTS sync_state(profile_id TEXT,bridge_id TEXT,sequence INTEGER DEFAULT -1,last_nonce TEXT,last_success TEXT,PRIMARY KEY(profile_id,bridge_id));
CREATE TABLE IF NOT EXISTS audit_events(id INTEGER PRIMARY KEY AUTOINCREMENT,profile_id TEXT,action TEXT,actor TEXT,timestamp TEXT,object_type TEXT,success INTEGER,error_code TEXT);
CREATE TABLE IF NOT EXISTS routine_events(id INTEGER PRIMARY KEY AUTOINCREMENT,profile_id TEXT,routine TEXT,outcome TEXT,note TEXT,timestamp TEXT,actor TEXT);
CREATE TABLE IF NOT EXISTS meta(profile_id TEXT,key TEXT,value TEXT,PRIMARY KEY(profile_id,key));
"""
_STRUCTURED_KINDS={"workout","route","ecg","audiogram","clinical","medication","medication_dose","assessment","state_of_mind","vision","correlation","activity_summary","characteristic"}


def _utcnow()->str:return datetime.now(timezone.utc).isoformat()
def _finite(value:Any)->float|None:
    try:v=float(value)
    except (TypeError,ValueError):return None
    return v if math.isfinite(v) else None

def _json(value:Any,max_bytes:int=MAX_METADATA_BYTES)->str|None:
    if value in (None,{},[]):return None
    try:raw=json.dumps(value,ensure_ascii=False,separators=(",",":"),default=str)
    except (TypeError,ValueError):return None
    if len(raw.encode())>max_bytes:return json.dumps({"_truncated":True},separators=(",",":"))
    return raw

def _source_key(source:Any)->str:
    if not isinstance(source,dict):return "unknown"
    basis="|".join(str(source.get(k) or "") for k in ("bundle_identifier","name","device_name","product_type","source_version"))
    return hashlib.sha256(basis.encode()).hexdigest()[:24]

class HealthLinkStore:
    """Private per-profile SQLite store. Blocking DB work runs in HA's executor."""
    def __init__(self,hass:HomeAssistant|None,path:Path,profile_id:str)->None:
        self.hass=hass;self.path=Path(path);self.profile_id=profile_id;self.timezone_name="UTC"
    async def _run(self,fn,*args):
        if self.hass is None:return fn(*args)
        return await self.hass.async_add_executor_job(fn,*args)
    def _connect(self)->sqlite3.Connection:
        self.path.parent.mkdir(parents=True,exist_ok=True)
        con=sqlite3.connect(self.path,timeout=30);con.row_factory=sqlite3.Row
        con.execute("PRAGMA journal_mode=WAL");con.execute("PRAGMA foreign_keys=ON");con.execute("PRAGMA busy_timeout=5000")
        return con
    async def async_initialize(self,*,config_entry_id:str,display_name:str,timezone_name:str)->None:
        await self._run(self._initialize_sync,config_entry_id,display_name,timezone_name)
    def _initialize_sync(self,config_entry_id:str,display_name:str,timezone_name:str)->None:
        self.timezone_name=timezone_name or "UTC";now=_utcnow()
        with self._connect() as con:
            con.executescript(_SCHEMA)
            con.execute("INSERT INTO profiles(profile_id,config_entry_id,display_name,timezone,created_at) VALUES(?,?,?,?,?) ON CONFLICT(profile_id) DO UPDATE SET config_entry_id=excluded.config_entry_id,display_name=excluded.display_name,timezone=excluded.timezone",(self.profile_id,config_entry_id,display_name,self.timezone_name,now))
    def _local_date(self,timestamp:str,explicit:Any=None)->str:
        if explicit:return str(explicit)[:10]
        try:dt=datetime.fromisoformat(str(timestamp).replace("Z","+00:00"))
        except ValueError:return str(timestamp)[:10]
        if dt.tzinfo is None:dt=dt.replace(tzinfo=timezone.utc)
        try:zone=ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError:zone=timezone.utc
        return dt.astimezone(zone).date().isoformat()

    async def async_ingest(self,items:Sequence[dict[str,Any]],*,sequence:int|None=None)->dict[str,int]:return await self._run(self._ingest_sync,list(items),sequence)
    def _ingest_sync(self,items:list[dict[str,Any]],sequence:int|None,*,update_sync:bool=True)->dict[str,int]:
        inserted=updated=ignored=0;now=_utcnow()
        with self._connect() as con:
            con.executescript(_SCHEMA)
            for item in items:
                if not isinstance(item,dict):ignored+=1;continue
                kind=str(item.get("object_kind") or item.get("kind") or "quantity")
                type_id=str(item.get("type_id") or item.get("healthkit_type") or "").strip()
                if not type_id:ignored+=1;continue
                start=str(item.get("start") or item.get("start_ts") or item.get("timestamp") or now)
                end=str(item.get("end") or item.get("end_ts") or start)
                source=item.get("source") if isinstance(item.get("source"),dict) else {}
                privacy=str(item.get("privacy_class") or ("sensitive" if str(item.get("domain") or "") in {"clinical","medication","reproductive","assessment"} else "wellness"))
                con.execute("INSERT INTO health_types(profile_id,type_id,object_kind,domain,display_name,canonical_unit,aggregation_kind,privacy_class,exposed,first_seen,last_seen) VALUES(?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT(profile_id,type_id) DO UPDATE SET object_kind=excluded.object_kind,domain=excluded.domain,display_name=COALESCE(excluded.display_name,health_types.display_name),canonical_unit=COALESCE(excluded.canonical_unit,health_types.canonical_unit),aggregation_kind=COALESCE(excluded.aggregation_kind,health_types.aggregation_kind),privacy_class=excluded.privacy_class,last_seen=excluded.last_seen",(self.profile_id,type_id,kind,str(item.get("domain") or "other"),item.get("display_name") or item.get("name"),item.get("unit") or item.get("canonical_unit"),item.get("aggregation_kind") or "latest",privacy,1 if type_id in DEFAULT_EXPOSED_TYPE_IDS else 0,now,now))
                if kind=="series_chunk":
                    series_uuid=str(item.get("series_uuid") or item.get("sample_uuid") or "")
                    if not series_uuid:ignored+=1;continue
                    points=item.get("points") if "points" in item else item.get("payload")
                    raw=json.dumps(points,ensure_ascii=False,separators=(",",":"),default=str)
                    idx=int(item.get("chunk_index") or 0)
                    existed=con.execute("SELECT 1 FROM series_chunks WHERE profile_id=? AND series_uuid=? AND chunk_index=?",(self.profile_id,series_uuid,idx)).fetchone()
                    con.execute("INSERT OR REPLACE INTO series_chunks(profile_id,series_uuid,chunk_index,series_kind,payload_json,checksum,point_count,start_ts,end_ts,ingest_seq) VALUES(?,?,?,?,?,?,?,?,?,?)",(self.profile_id,series_uuid,idx,str(item.get("series_kind") or type_id),raw,hashlib.sha256(raw.encode()).hexdigest(),len(points) if isinstance(points,list) else None,start,end,sequence))
                    updated+=bool(existed);inserted+=not bool(existed);continue
                uuid=str(item.get("sample_uuid") or item.get("object_uuid") or item.get("uuid") or hashlib.sha256(f"{type_id}|{start}|{end}|{item.get('numeric_value')}|{item.get('value')}".encode()).hexdigest())
                numeric=_finite(item.get("numeric_value",item.get("value")))
                text=item.get("text_value")
                if text is None and numeric is None and item.get("value") is not None:text=str(item.get("value"))
                if kind in _STRUCTURED_KINDS or item.get("payload") is not None or item.get("structured_value") is not None:
                    payload=item.get("payload",item.get("structured_value",item))
                    existed=con.execute("SELECT 1 FROM structured_objects WHERE profile_id=? AND object_uuid=?",(self.profile_id,uuid)).fetchone()
                    con.execute("INSERT OR REPLACE INTO structured_objects(profile_id,object_uuid,type_id,object_kind,start_ts,end_ts,payload_json,source_json,metadata_json,deleted,ingest_seq,modified_ts) VALUES(?,?,?,?,?,?,?,?,?,?,?,?)",(self.profile_id,uuid,type_id,kind,start,end,_json(payload,1024*1024),_json(source),_json(item.get("metadata")),int(bool(item.get("deleted"))),sequence,now))
                    updated+=bool(existed);inserted+=not bool(existed)
                    if numeric is None:continue
                existed=con.execute("SELECT 1 FROM samples WHERE profile_id=? AND sample_uuid=?",(self.profile_id,uuid)).fetchone()
                con.execute("INSERT OR REPLACE INTO samples(profile_id,sample_uuid,type_id,object_kind,start_ts,end_ts,local_date,numeric_value,text_value,canonical_unit,category_code,source_key,source_json,metadata_json,deleted,ingest_seq,modified_ts) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",(self.profile_id,uuid,type_id,kind,start,end,self._local_date(end,item.get("local_date")),numeric,text,item.get("unit") or item.get("canonical_unit"),item.get("category_code"),_source_key(source),_json(source),_json(item.get("metadata")),int(bool(item.get("deleted"))),sequence,now))
                updated+=bool(existed);inserted+=not bool(existed)
            if update_sync:
                con.execute("INSERT INTO meta(profile_id,key,value) VALUES(?,?,?) ON CONFLICT(profile_id,key) DO UPDATE SET value=excluded.value",(self.profile_id,"last_sync",now))
        return {"inserted":int(inserted),"updated":int(updated),"ignored":ignored}

    async def async_last_sequence(self,bridge_id:str)->int:return await self._run(self._last_sequence_sync,bridge_id)
    def _last_sequence_sync(self,bridge_id:str)->int:
        with self._connect() as con:
            row=con.execute("SELECT sequence FROM sync_state WHERE profile_id=? AND bridge_id=?",(self.profile_id,bridge_id)).fetchone();return int(row[0]) if row else -1
    async def async_commit_sequence(self,bridge_id:str,sequence:int,nonce:str)->None:await self._run(self._commit_sequence_sync,bridge_id,sequence,nonce)
    def _commit_sequence_sync(self,bridge_id:str,sequence:int,nonce:str)->None:
        with self._connect() as con:con.execute("INSERT INTO sync_state(profile_id,bridge_id,sequence,last_nonce,last_success) VALUES(?,?,?,?,?) ON CONFLICT(profile_id,bridge_id) DO UPDATE SET sequence=excluded.sequence,last_nonce=excluded.last_nonce,last_success=excluded.last_success",(self.profile_id,bridge_id,sequence,nonce,_utcnow()))

    async def async_catalog(self)->list[dict[str,Any]]:return await self._run(self._catalog_sync)
    def _catalog_sync(self)->list[dict[str,Any]]:
        with self._connect() as con:return [dict(r) for r in con.execute("SELECT h.*,(SELECT COUNT(*) FROM samples s WHERE s.profile_id=h.profile_id AND s.type_id=h.type_id AND s.deleted=0)+(SELECT COUNT(*) FROM structured_objects o WHERE o.profile_id=h.profile_id AND o.type_id=h.type_id AND o.deleted=0) AS sample_count,(SELECT MAX(x.end_ts) FROM (SELECT end_ts FROM samples s2 WHERE s2.profile_id=h.profile_id AND s2.type_id=h.type_id AND s2.deleted=0 UNION ALL SELECT end_ts FROM structured_objects o2 WHERE o2.profile_id=h.profile_id AND o2.type_id=h.type_id AND o2.deleted=0) x) AS last_sample FROM health_types h WHERE h.profile_id=? ORDER BY h.domain,h.display_name,h.type_id",(self.profile_id,)).fetchall()]
    async def async_set_exposed(self,type_id:str,exposed:bool)->bool:return await self._run(self._set_exposed_sync,type_id,exposed)
    def _set_exposed_sync(self,type_id:str,exposed:bool)->bool:
        with self._connect() as con:
            cur=con.execute("UPDATE health_types SET exposed=? WHERE profile_id=? AND type_id=?",(int(exposed),self.profile_id,type_id));return cur.rowcount>0
    async def async_exposed_types(self)->list[dict[str,Any]]:return await self._run(self._exposed_types_sync)
    def _exposed_types_sync(self)->list[dict[str,Any]]:
        with self._connect() as con:return [dict(r) for r in con.execute("SELECT * FROM health_types WHERE profile_id=? AND exposed=1 ORDER BY domain,display_name,type_id",(self.profile_id,)).fetchall()]
    async def async_latest_for_types(self,type_ids:Iterable[str])->dict[str,dict[str,Any]]:return await self._run(self._latest_for_types_sync,list(dict.fromkeys(type_ids)))
    def _latest_for_types_sync(self,ids:list[str])->dict[str,dict[str,Any]]:
        out={}
        with self._connect() as con:
            for tid in ids:
                row=con.execute("SELECT s.*,h.display_name,h.domain,h.privacy_class,h.aggregation_kind FROM samples s JOIN health_types h ON h.profile_id=s.profile_id AND h.type_id=s.type_id WHERE s.profile_id=? AND s.type_id=? AND s.deleted=0 ORDER BY s.end_ts DESC LIMIT 1",(self.profile_id,tid)).fetchone()
                if row:out[tid]=dict(row)
        return out
    async def async_latest_numeric(self,type_ids:Iterable[str])->tuple[float|None,str|None,str|None]:return await self._run(self._latest_numeric_sync,list(type_ids))
    def _latest_numeric_sync(self,ids:list[str])->tuple[float|None,str|None,str|None]:
        if not ids:return None,None,None
        qs=','.join('?'*len(ids))
        with self._connect() as con:
            row=con.execute(f"SELECT numeric_value,canonical_unit,end_ts FROM samples WHERE profile_id=? AND type_id IN ({qs}) AND deleted=0 AND numeric_value IS NOT NULL ORDER BY end_ts DESC LIMIT 1",[self.profile_id,*ids]).fetchone();return (float(row[0]),row[1],row[2]) if row else (None,None,None)
    async def async_today_metric(self,type_ids:Iterable[str],*,companion_snapshot:bool=True)->float|None:return await self._run(self._today_metric_sync,list(type_ids),companion_snapshot)
    def _today_metric_sync(self,ids:list[str],companion_snapshot:bool)->float|None:
        if not ids:return None
        try:day=datetime.now(ZoneInfo(self.timezone_name)).date().isoformat()
        except ZoneInfoNotFoundError:day=datetime.now(timezone.utc).date().isoformat()
        qs=','.join('?'*len(ids))
        with self._connect() as con:
            rows=con.execute(f"SELECT numeric_value,end_ts FROM samples WHERE profile_id=? AND type_id IN ({qs}) AND local_date=? AND deleted=0 AND numeric_value IS NOT NULL ORDER BY end_ts",[self.profile_id,*ids,day]).fetchall()
        if not rows:return None
        vals=[float(r[0]) for r in rows]
        return vals[-1] if companion_snapshot else sum(vals)
    async def async_daily_values(self,type_ids:Iterable[str],days:int,*,snapshot:bool=False)->list[float]:return await self._run(self._daily_values_sync,list(type_ids),days,snapshot)
    def _daily_values_sync(self,ids:list[str],days:int,snapshot:bool)->list[float]:
        if not ids:return []
        try:zone=ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError:zone=timezone.utc
        start=(datetime.now(zone).date()-timedelta(days=max(1,days)-1)).isoformat();qs=','.join('?'*len(ids))
        with self._connect() as con:rows=con.execute(f"SELECT local_date,numeric_value,end_ts FROM samples WHERE profile_id=? AND type_id IN ({qs}) AND local_date>=? AND deleted=0 AND numeric_value IS NOT NULL ORDER BY local_date,end_ts",[self.profile_id,*ids,start]).fetchall()
        grouped:dict[str,list[float]]={}
        for r in rows:grouped.setdefault(r[0],[]).append(float(r[1]))
        return [vals[-1] if snapshot else sum(vals) for _,vals in sorted(grouped.items())]


    async def async_same_time_snapshots(self,type_ids:Iterable[str],days:int,reference:datetime|None=None)->list[float]:return await self._run(self._same_time_snapshots_sync,list(type_ids),days,reference)
    def _same_time_snapshots_sync(self,ids:list[str],days:int,reference:datetime|None)->list[float]:
        if not ids:return []
        try:zone=ZoneInfo(self.timezone_name)
        except ZoneInfoNotFoundError:zone=timezone.utc
        now=(reference or datetime.now(timezone.utc)).astimezone(zone)
        start=(now.date()-timedelta(days=max(1,days))).isoformat();qs=','.join('?'*len(ids))
        with self._connect() as con:rows=con.execute(f"SELECT local_date,numeric_value,end_ts FROM samples WHERE profile_id=? AND type_id IN ({qs}) AND local_date>=? AND local_date<? AND deleted=0 AND numeric_value IS NOT NULL ORDER BY local_date,end_ts",[self.profile_id,*ids,start,now.date().isoformat()]).fetchall()
        grouped:dict[str,float]={}
        cutoff=(now.hour,now.minute,now.second)
        for row in rows:
            try:stamp=datetime.fromisoformat(row[2].replace('Z','+00:00')).astimezone(zone)
            except (TypeError,ValueError):continue
            if (stamp.hour,stamp.minute,stamp.second)<=cutoff:grouped[row[0]]=float(row[1])
        return [grouped[key] for key in sorted(grouped)][-max(1,days):]

    async def async_record_routine(self,routine:str,outcome:str,*,note:str|None=None,actor:str="system")->int:return await self._run(self._record_routine_sync,routine,outcome,note,actor)
    def _record_routine_sync(self,routine:str,outcome:str,note:str|None,actor:str)->int:
        with self._connect() as con:
            cur=con.execute("INSERT INTO routine_events(profile_id,routine,outcome,note,timestamp,actor) VALUES(?,?,?,?,?,?)",(self.profile_id,routine,outcome,(note or '')[:500] or None,_utcnow(),actor))
            return int(cur.lastrowid)
    async def async_routine_history(self,*,routine:str|None=None,limit:int=50)->list[dict[str,Any]]:return await self._run(self._routine_history_sync,routine,limit)
    def _routine_history_sync(self,routine:str|None,limit:int)->list[dict[str,Any]]:
        where="profile_id=?";params:list[Any]=[self.profile_id]
        if routine:where+=" AND routine=?";params.append(routine)
        params.append(min(max(int(limit),1),200))
        with self._connect() as con:return [dict(r) for r in con.execute(f"SELECT id,routine,outcome,note,timestamp,actor FROM routine_events WHERE {where} ORDER BY id DESC LIMIT ?",params).fetchall()]

    async def async_series(self,type_id:str,start:str,end:str,limit:int=5000)->list[dict[str,Any]]:return await self._run(self._series_sync,type_id,start,end,limit)
    def _series_sync(self,type_id:str,start:str,end:str,limit:int)->list[dict[str,Any]]:
        with self._connect() as con:return [dict(r) for r in con.execute("SELECT start_ts AS timestamp,numeric_value AS value,canonical_unit AS unit FROM samples WHERE profile_id=? AND type_id=? AND deleted=0 AND end_ts>=? AND start_ts<=? ORDER BY start_ts LIMIT ?",(self.profile_id,type_id,start,end,min(max(limit,1),50000))).fetchall()]
    async def async_structured_object(self,object_uuid:str)->dict[str,Any]|None:return await self._run(self._structured_object_sync,object_uuid)
    def _structured_object_sync(self,object_uuid:str)->dict[str,Any]|None:
        with self._connect() as con:row=con.execute("SELECT * FROM structured_objects WHERE profile_id=? AND object_uuid=? AND deleted=0",(self.profile_id,object_uuid)).fetchone()
        if not row:return None
        out=dict(row)
        for key in ("payload_json","source_json","metadata_json"):
            raw=out.pop(key,None)
            if raw:
                try:out[key.removesuffix('_json')]=json.loads(raw)
                except json.JSONDecodeError:out[key.removesuffix('_json')]=None
        return out
    async def async_series_chunks(self,series_uuid:str,*,limit:int=256)->list[dict[str,Any]]:return await self._run(self._series_chunks_sync,series_uuid,limit)
    def _series_chunks_sync(self,series_uuid:str,limit:int)->list[dict[str,Any]]:
        with self._connect() as con:rows=con.execute("SELECT * FROM series_chunks WHERE profile_id=? AND series_uuid=? ORDER BY chunk_index LIMIT ?",(self.profile_id,series_uuid,min(max(limit,1),4096))).fetchall()
        out=[]
        for r in rows:
            item=dict(r);raw=item.pop("payload_json",None)
            try:item["payload"]=json.loads(raw) if raw is not None else None
            except json.JSONDecodeError:item["payload"]=None
            out.append(item)
        return out
    async def async_status(self)->dict[str,Any]:return await self._run(self._status_sync)
    def _status_sync(self)->dict[str,Any]:
        with self._connect() as con:
            sample=con.execute("SELECT COUNT(*) FROM samples WHERE profile_id=? AND deleted=0",(self.profile_id,)).fetchone()[0]
            structured=con.execute("SELECT COUNT(*) FROM structured_objects WHERE profile_id=? AND deleted=0",(self.profile_id,)).fetchone()[0]
            types=con.execute("SELECT COUNT(*) FROM health_types WHERE profile_id=?",(self.profile_id,)).fetchone()[0]
            exposed=con.execute("SELECT COUNT(*) FROM health_types WHERE profile_id=? AND exposed=1",(self.profile_id,)).fetchone()[0]
            sources=con.execute("SELECT COUNT(DISTINCT source_key) FROM samples WHERE profile_id=? AND source_key IS NOT NULL",(self.profile_id,)).fetchone()[0]
            row=con.execute("SELECT value FROM meta WHERE profile_id=? AND key='last_sync'",(self.profile_id,)).fetchone()
        return {"sample_count":int(sample)+int(structured),"type_count":int(types),"exposed_count":int(exposed),"source_count":int(sources),"last_sync":row[0] if row else None,"db_size":self.path.stat().st_size if self.path.exists() else 0}
    async def async_purge(self,older_than_days:int)->int:return await self._run(self._purge_sync,older_than_days)
    def _purge_sync(self,older_than_days:int)->int:
        cutoff=(datetime.now(timezone.utc)-timedelta(days=max(0,older_than_days))).isoformat()
        with self._connect() as con:
            a=con.execute("DELETE FROM samples WHERE profile_id=? AND end_ts<?",(self.profile_id,cutoff)).rowcount
            b=con.execute("DELETE FROM structured_objects WHERE profile_id=? AND end_ts<?",(self.profile_id,cutoff)).rowcount
            c=con.execute("DELETE FROM series_chunks WHERE profile_id=? AND end_ts<?",(self.profile_id,cutoff)).rowcount
        return int(a)+int(b)+int(c)

    async def async_save_composer(self,definition_id:str,name:str,definition:dict[str,Any],*,enabled:bool=True)->None:await self._run(self._save_composer_sync,definition_id,name,json.dumps(definition,ensure_ascii=False),enabled)
    def _save_composer_sync(self,definition_id:str,name:str,raw:str,enabled:bool)->None:
        with self._connect() as con:
            old=con.execute("SELECT version FROM composer_definitions WHERE profile_id=? AND id=?",(self.profile_id,definition_id)).fetchone();version=int(old[0])+1 if old else 1
            con.execute("INSERT OR REPLACE INTO composer_definitions(profile_id,id,name,version,enabled,definition_json,entity_exposure,updated_at) VALUES(?,?,?,?,?,?,1,?)",(self.profile_id,definition_id,name,version,int(enabled),raw,_utcnow()))
    async def async_list_composers(self)->list[dict[str,Any]]:return await self._run(self._list_composers_sync)
    def _list_composers_sync(self)->list[dict[str,Any]]:
        with self._connect() as con:rows=con.execute("SELECT * FROM composer_definitions WHERE profile_id=? ORDER BY name,id",(self.profile_id,)).fetchall()
        out=[]
        for r in rows:
            item=dict(r)
            try:item["definition"]=json.loads(item.pop("definition_json") or "{}")
            except json.JSONDecodeError:item["definition"]={}
            out.append(item)
        return out
    async def async_delete_composer(self,definition_id:str)->bool:return await self._run(self._delete_composer_sync,definition_id)
    def _delete_composer_sync(self,definition_id:str)->bool:
        with self._connect() as con:return con.execute("DELETE FROM composer_definitions WHERE profile_id=? AND id=?",(self.profile_id,definition_id)).rowcount>0
    async def async_export_rows(self,*,type_id:str|None=None,start:str|None=None,end:str|None=None)->list[dict[str,Any]]:return await self._run(self._export_rows_sync,type_id,start,end)
    def _export_rows_sync(self,type_id:str|None,start:str|None,end:str|None)->list[dict[str,Any]]:
        where=["profile_id=?","deleted=0"];params:[Any]=[self.profile_id]
        if type_id:where.append("type_id=?");params.append(type_id)
        if start:where.append("end_ts>=?");params.append(start)
        if end:where.append("start_ts<=?");params.append(end)
        with self._connect() as con:return [dict(r) for r in con.execute(f"SELECT sample_uuid,type_id,object_kind,start_ts,end_ts,numeric_value,text_value,canonical_unit,category_code FROM samples WHERE {' AND '.join(where)} ORDER BY start_ts",params).fetchall()]
    async def async_audit(self,action:str,*,actor:str="system",object_type:str|None=None,success:bool=True,error_code:str|None=None)->None:await self._run(self._audit_sync,action,actor,object_type,success,error_code)
    def _audit_sync(self,action:str,actor:str,object_type:str|None,success:bool,error_code:str|None)->None:
        with self._connect() as con:con.execute("INSERT INTO audit_events(profile_id,action,actor,timestamp,object_type,success,error_code) VALUES(?,?,?,?,?,?,?)",(self.profile_id,action,actor,_utcnow(),object_type,int(success),error_code))
