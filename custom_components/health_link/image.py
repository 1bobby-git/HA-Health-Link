"""Authenticated Home Assistant image entity for the latest imported ECG."""
from __future__ import annotations

from datetime import datetime, timezone
import io

from PIL import Image, ImageDraw
from homeassistant.components.image import ImageEntity
from homeassistant.core import callback
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .data_features import _waveform_sync
from .ecg_entities import ecg_enabled, profile_device
from .health_import import HealthImportError, MAX_ECG_POINTS


def render_waveform(points):
    """Min/max preview preserving visible peaks, not a diagnostic ECG printout."""
    if not points:
        return None
    width, height = 1200, 360
    image = Image.new("RGB", (width, height), "white")
    draw = ImageDraw.Draw(image)
    left, top, right, bottom = 60, 50, width - 30, height - 45
    first, last = points[0][0], points[-1][0]
    low = min(point[1] for point in points); high = max(point[1] for point in points)
    span = max(high - low, 0.001)
    draw.text((left, 15), "Recorded ECG / voltage (mV) / Preview only - not for diagnosis", fill="black")
    for index in range(6):
        y = top + (bottom - top) * index / 5
        draw.line((left, y, right, y), fill="lightgray")
    bins = {}
    for second, voltage in points:
        x = left + int((second - first) / max(last - first, 0.001) * (right - left))
        y = bottom - (voltage - low) / span * (bottom - top)
        values = bins.setdefault(x, [y, y, y, y])
        values[1] = min(values[1], y); values[2] = max(values[2], y); values[3] = y
    previous = None
    for x, (start, minimum, maximum, end) in sorted(bins.items()):
        if previous:
            draw.line((*previous, x, start), fill="black")
        draw.line((x, minimum, x, maximum), fill="black")
        previous = (x, end)
    draw.text((left, height - 26), f"{first:.3f} - {last:.3f} seconds   |   Range {low:.4f} to {high:.4f} mV", fill="black")
    output = io.BytesIO(); image.save(output, format="PNG")
    return output.getvalue()


async def async_setup_entry(hass, entry, async_add_entities):
    runtime = entry.runtime_data
    if await ecg_enabled(runtime.store, entry.options):
        async_add_entities([HealthLinkECGImage(hass, runtime, entry)])


class HealthLinkECGImage(CoordinatorEntity, ImageEntity):
    _attr_has_entity_name = True
    _attr_translation_key = "ecg_waveform"
    _attr_content_type = "image/png"

    def __init__(self, hass, runtime, entry):
        ImageEntity.__init__(self, hass)
        CoordinatorEntity.__init__(self, runtime.coordinator)
        self.runtime = runtime
        self.entry = entry
        self._attr_unique_id = f"{entry.entry_id}_ecg_waveform"
        self._attr_device_info = profile_device(runtime, entry)
        self._record_id = None
        self._image_bytes = None
        self._image_record_id = None
        self._attr_image_last_updated = datetime.now(timezone.utc)

    def _latest(self):
        return ((self.coordinator.data or {}).get("ecg") or {}).get("latest") or {}

    @property
    def available(self):
        return super().available and bool(self.entry.options.get("enable_sensitive")) and bool(self._latest().get("point_count"))

    @callback
    def _handle_coordinator_update(self):
        identifier = self._latest().get("object_uuid") if self.available else None
        if identifier != self._record_id:
            self._record_id = identifier
            self._image_bytes = None
            self._image_record_id = None
            self._attr_image_last_updated = datetime.now(timezone.utc)
        super()._handle_coordinator_update()

    async def async_image(self):
        if not self.available:
            self._image_bytes = None
            return None
        identifier = self._latest().get("object_uuid")
        if self._image_bytes is not None and self._image_record_id == identifier:
            return self._image_bytes
        try:
            data = await self.runtime.store._run(_waveform_sync, self.runtime.store, identifier, 0, MAX_ECG_POINTS)
        except HealthImportError:
            return None
        result = await self.hass.async_add_executor_job(render_waveform, data["points"])
        if not self.available or identifier != self._latest().get("object_uuid"):
            return None
        self._image_record_id = identifier
        self._image_bytes = result
        return result
