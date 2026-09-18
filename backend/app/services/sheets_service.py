"""Optional Google Sheets sync — an example external-integration adapter.

WHY an adapter behind a flag?
  WHAT: when GOOGLE_SHEETS_ENABLED=true and credentials exist, new leads are
        appended to a Google Sheet via a service account.
  WHY: demonstrates the adapter pattern — the same seam could sync to a CRM
       (HubSpot, Zoho) without touching lead logic.
  TRADEOFF: sync is best-effort. A failure is logged and swallowed (the lead
       is already safe in SQLite); the docs explain how a retry queue would
       harden this in production.

Credentials come from GOOGLE_SERVICE_ACCOUNT_JSON (a file path OR the inline
JSON string) and are never logged. gspread is imported lazily so the base
install has no Google dependencies.
"""
import json
from pathlib import Path

from app.config import Settings
from app.logging_config import get_logger
from app.models.lead import Lead

logger = get_logger(__name__)


class SheetsService:
    """Best-effort lead sync to Google Sheets (disabled by default)."""

    def __init__(self, settings: Settings) -> None:
        self._enabled = settings.google_sheets_enabled
        self._credentials_ref = settings.google_service_account_json
        self._sheet_id = settings.google_sheet_id

    @property
    def enabled(self) -> bool:
        """True only when fully configured (flag + credentials + sheet id)."""
        return bool(self._enabled and self._credentials_ref and self._sheet_id)

    def sync_lead_created(self, lead: Lead) -> None:
        """Append one lead row. Never raises: integration is best-effort."""
        if not self.enabled:
            return
        try:
            worksheet = self._open_worksheet()
            worksheet.append_row(
                [
                    lead.id, lead.name, lead.phone, lead.email or "",
                    lead.city or "", lead.business_type or "",
                    lead.requirement or "", lead.lead_score, lead.priority,
                    lead.status, lead.source, str(lead.created_at),
                ]
            )
            logger.info("sheets sync: lead %d appended", lead.id)
        except Exception as exc:  # noqa: BLE001 — integration must never break the core flow (spec section 57)
            logger.warning("sheets sync failed for lead %d: %r", lead.id, exc)

    def _open_worksheet(self) -> object:
        """Authorize and open the first worksheet of the configured sheet."""
        import gspread  # lazy: optional dependency

        if Path(self._credentials_ref).is_file():
            client = gspread.service_account(filename=self._credentials_ref)
        else:
            info = json.loads(self._credentials_ref)
            client = gspread.service_account_from_dict(info)
        return client.open_by_key(self._sheet_id).sheet1
