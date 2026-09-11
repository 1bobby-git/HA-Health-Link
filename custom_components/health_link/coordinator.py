"""HealthLink push coordinator and derived context calculations."""
from __future__ import annotations

from datetime import datetime, timezone
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator

from .baseline.engine import robust_baseline, robust_zscore, relative_change
from .const import DEFAULT_BASELINE_WINDOW, DOMAIN
from .composer.engine import ComposerError, SafeFormula
from .storage import HealthLinkStore

ALIASES = {
    "steps": ["HKQuantityTypeIdentifierStepCount"],
    "active_energy": ["HKQuantityTypeIdentifierActiveEnergyBurned"],
    "exercise_time": ["HKQuantityTypeIdentifierAppleExerciseTime"],
    "hrv": ["HKQuantityTypeIdentifierHeartRateVariabilitySDNN"],
    "resting_hr": ["HKQuantityTypeIdentifierRestingHeartRate"],
    "sleep_duration": ["companion.health_sleep_duration", "derived.sleep.total_duration"],
    "sleep_deep": ["companion.health_sleep_deep", "derived.sleep.deep_duration"],
    "sleep_rem": ["companion.health_sleep_rem", "derived.sleep.rem_duration"],
    "sleep_awake": ["companion.health_sleep_awake", "derived.sleep.awake_duration"],
}

class HealthLinkCoordinator(DataUpdateCoordinator[dict[str, Any]]):
    """Coordinate push data and expose a compact HA-friendly snapshot."""

    def __init__(self, hass: HomeAssistant, store: HealthLinkStore, entry) -> None:
        super().__init__(hass, logger=__import__("logging").getLogger(__name__), config_entry=entry, name=f"{DOMAIN}-{entry.entry_id}")
        self.store=store
        self.entry=entry

    async def _async_update_data(self) -> dict[str, Any]:
        return await self._build_snapshot()

    async def async_refresh_from_store(self) -> None:
        self.async_set_updated_data(await self._build_snapshot())

    async def _build_snapshot(self) -> dict[str, Any]:
        opts=self.entry.options
        window=int(opts.get("baseline_window", DEFAULT_BASELINE_WINDOW))
        status=await self.store.async_status()
        exposed=await self.store.async_exposed_types()
        raw=await self.store.async_latest_for_types([x["type_id"] for x in exposed])

        steps=await self.store.async_today_metric(ALIASES["steps"])
        active=await self.store.async_today_metric(ALIASES["active_energy"])
        exercise=await self.store.async_today_metric(ALIASES["exercise_time"])
        sleep,_,sleep_ts=await self.store.async_latest_numeric(ALIASES["sleep_duration"])
        deep,_,_=await self.store.async_latest_numeric(ALIASES["sleep_deep"])
        rem,_,_=await self.store.async_latest_numeric(ALIASES["sleep_rem"])
        awake,_,_=await self.store.async_latest_numeric(ALIASES["sleep_awake"])
        hrv,_,_=await self.store.async_latest_numeric(ALIASES["hrv"])
        rhr,_,_=await self.store.async_latest_numeric(ALIASES["resting_hr"])

        hrv_hist=await self.store.async_daily_values(ALIASES["hrv"],window,snapshot=True)
        rhr_hist=await self.store.async_daily_values(ALIASES["resting_hr"],window,snapshot=True)
        sleep_hist=await self.store.async_daily_values(ALIASES["sleep_duration"],window,snapshot=True)
        steps_hist=await self.store.async_daily_values(ALIASES["steps"],window,snapshot=True)
        hrv_base=robust_baseline(hrv_hist)
        rhr_base=robust_baseline(rhr_hist)
        sleep_base=robust_baseline(sleep_hist)
        steps_base=robust_baseline(steps_hist)
        z_hrv=robust_zscore(hrv,hrv_base)
        z_rhr=robust_zscore(rhr,rhr_base)
        sleep_change=relative_change(sleep,sleep_base.median)

        usable=sum(x is not None for x in (z_hrv,z_rhr,sleep_change))
        sample_factor=min(1.0, min(hrv_base.count or 999, rhr_base.count or 999, sleep_base.count or 999)/14.0) if usable else 0.0
        confidence=round(min(1.0,(usable/3.0)*0.65+sample_factor*0.35)*100,1)
        score=None
        context="insufficient_data"
        if usable>=2:
            score=50.0
            if z_hrv is not None: score+=max(-2,min(2,z_hrv))*10
            if z_rhr is not None: score-=max(-2,min(2,z_rhr))*10
            if sleep_change is not None: score+=max(-30,min(30,sleep_change))/3
            score=round(max(0,min(100,score)),1)
            context="above_baseline" if score>=65 else "below_baseline" if score<40 else "within_baseline"

        efficiency=None
        if sleep is not None and awake is not None and sleep+awake>0:
            efficiency=round(sleep/(sleep+awake)*100,1)

        last=status.get("last_sync")
        latency=None
        if last:
            try: latency=max(0,(datetime.now(timezone.utc)-datetime.fromisoformat(last)).total_seconds())
            except ValueError: pass
        stale_hours=float(opts.get("stale_hours",24))
        stale=latency is None or latency>stale_hours*3600
        freshness=0.0 if stale else 1.0 if latency is not None and latency<3600 else 0.75
        data_confidence=round(min(100.0, confidence*0.7+freshness*30),1) if status.get("sample_count") else 0.0

        composer_values: dict[str, dict[str, Any]] = {}
        if opts.get("enable_composer", True):
            for item in await self.store.async_list_composers():
                if not item.get("enabled"):
                    continue
                definition=item.get("definition") or {}
                inputs=definition.get("inputs") or {}
                values: dict[str, Any] = {}
                available=0
                for key, source in inputs.items():
                    value=None
                    if source.get("source")=="healthkit":
                        value,_,_=await self.store.async_latest_numeric([source.get("type_id")])
                    elif source.get("source")=="ha":
                        state=self.hass.states.get(source.get("entity_id"))
                        if state is not None:
                            try: value=float(state.state)
                            except (TypeError,ValueError): value=None
                    values[key]=value
                    if value is not None: available+=1
                try:
                    result=SafeFormula(str(definition.get("formula") or "")).evaluate(values)
                except ComposerError:
                    result=None
                composer_values[item["id"]]={
                    "value":result,
                    "unit":definition.get("unit"),
                    "confidence":round(available/max(len(inputs),1)*100,1),
                    "inputs":len(inputs),
                    "available_inputs":available,
                    "name":item.get("name"),
                }

        return {
            **status,
            "sync_latency_seconds": latency,
            "data_stale": stale,
            "data_confidence": data_confidence,
            "steps_today": steps,
            "active_energy_today": active,
            "exercise_time_today": exercise,
            "sleep_duration": sleep,
            "sleep_deep": deep,
            "sleep_rem": rem,
            "sleep_awake": awake,
            "sleep_efficiency": efficiency,
            "sleep_last_ts": sleep_ts,
            "recovery_context": context,
            "recovery_score": score,
            "recovery_confidence": confidence,
            "recovery_below_baseline": context=="below_baseline",
            "hrv_vs_baseline": relative_change(hrv,hrv_base.median),
            "resting_hr_vs_baseline": relative_change(rhr,rhr_base.median),
            "sleep_vs_baseline": sleep_change,
            "activity_vs_baseline": relative_change(steps,steps_base.median),
            "raw_metrics": raw,
            "composer_values": composer_values,
        }
