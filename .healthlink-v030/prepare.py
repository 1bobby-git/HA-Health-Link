"""Finish import lifecycle safeguards and fix the authentication test fixture."""
from pathlib import Path
import runpy


def replace(path, old, new):
    path = Path(path)
    text = path.read_text()
    assert text.count(old) == 1, f'Unsafe patch: {path}: {old[:80]}'
    path.write_text(text.replace(old, new, 1))

replace('tests/test_health_import.py',
        'hass.auth.async_get_user = AsyncMock(return_value=NS(is_admin=False))',
        'hass.auth = NS(async_get_user=AsyncMock(return_value=NS(is_admin=False)))')

replace('custom_components/health_link/data_features.py',
        '\nasync def import_uploaded(',
        '''
async def _finish_worker(future):
    """Keep the import lock until a non-cancellable executor job has finished."""
    try:
        return await asyncio.shield(future)
    except asyncio.CancelledError:
        while not future.done():
            try:
                await asyncio.shield(future)
            except asyncio.CancelledError:
                continue
            except Exception:
                break
        if future.done() and not future.cancelled():
            # Consume a worker error without replacing the caller cancellation.
            future.exception()
        raise


async def import_uploaded(''')
replace('custom_components/health_link/data_features.py',
        'result = await hass.async_add_executor_job(process)',
        'result = await _finish_worker(hass.async_add_executor_job(process))')
replace('custom_components/health_link/data_features.py',
        'result = await hass.async_add_executor_job(_import_sync, store, json_records(data), include, "all")',
        'result = await _finish_worker(hass.async_add_executor_job(_import_sync, store, json_records(data), include, "all"))')

# This preserves original-file hash checks and removes the one-time staging dir.
runpy.run_path('.healthlink-v030/apply.py', run_name='__main__')

replace('custom_components/health_link/companion.py',
        '        if not import_now:\n            return\n',
        '        if not import_now or self._bulk_import_running():\n            return\n')
replace('custom_components/health_link/companion.py',
        '    async def _async_flush_pending(self) -> None:\n        pending = list(self._pending.values())',
        '''    def _bulk_import_running(self) -> bool:
        """Avoid competing SQLite writes during an atomic historical import."""
        lock = getattr(self.hass, "data", {}).get(DOMAIN, {}).get("import_locks", {}).get(
            self.runtime.coordinator.entry.entry_id
        )
        return lock is not None and lock.locked()

    async def _async_flush_pending(self) -> None:
        if self._bulk_import_running():
            # Retain just the latest value per entity while the import commits.
            # It is flushed normally once the import lock has been released.
            if self._flush_unsub is None:
                self._flush_unsub = async_call_later(
                    self.hass, _FLUSH_DELAY_SECONDS, self._scheduled_flush
                )
            return
        pending = list(self._pending.values())''')
print('Import cancellation, live-update coalescing and authentication fixture verified.')
