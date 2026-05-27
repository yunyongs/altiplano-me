"""Paso 1 Agent Loop state management.

Persists agent queue state to a JSON file inside the destination folder
so that browser refreshes can resume where the operator left off.

ES: Gestión de estado del bucle agente para Paso 1.
"""
from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path

from ar_utils import safe_resolve

_STATE_FILENAME = ".paso1_agent_state.json"


def _state_path(dest_folder: str, allowed_roots: list[str]) -> Path:
    base = safe_resolve(dest_folder, allowed_roots)
    return base / _STATE_FILENAME


def _extract_done_states(existing_state: dict, component: str, quarter: str) -> dict[str, str]:
    """Return {match_key: item_state} for done/skipped items to preserve across re-init.

    Returns an empty dict if the existing state is for a different quarter or component,
    meaning a fresh start is required.
    """
    if (existing_state.get("component") != component
            or existing_state.get("quarter") != quarter):
        return {}
    preserved: dict[str, str] = {}
    for item in existing_state.get("items", []):
        if item.get("item_state") in ("done", "skipped"):
            item_id = item.get("id", "")
            if component == "C2":
                # C2: item ID is the stable key (C2_grp_{contrato}_{quarter})
                key = item_id
            else:
                # C1/C3: use CdgActvdd code as key; fallback to item ID for rows without a code
                key = item.get("code") if item.get("code") else item_id
            if key:
                preserved[key] = item["item_state"]
    return preserved


def init_agent_state(
    dest_folder: str,
    component: str,
    quarter: str,
    diagnose_data: dict,
    allowed_roots: list[str],
) -> dict:
    """Build an agent work queue from diagnose results.

    For C1/C3: one item per child row (each row has its own SHP attachment).
    For C2: one item per group (contrato+quarter) — the SHP attachment is on
    the summary row, not on individual child rows.  Child codes are stored in
    the item so the ArcPy CdgActvdd mapping can use them.

    Only rows whose cmp_status != "verified_match" become queue items.
    """
    items: list[dict] = []

    if component == "C2":
        # ── C2: one item per group (contrato+quarter) ──
        _existing = load_agent_state(dest_folder, allowed_roots)
        _preserved = _extract_done_states(_existing, component, quarter) if _existing else {}

        for g in diagnose_data.get("groups", []):
            pending_rows = [
                r for r in g.get("rows", [])
                if r.get("cmp_status") != "verified_match"
            ]
            if not pending_rows:
                continue
            contrato = g.get("contrato", "")
            org = g.get("org", "")
            gt = g.get("quarter", "")
            grant_type = g.get("grant_type", "")
            summary_rn = g.get("summaryRowNumber")

            child_codes = [r.get("code", "") for r in pending_rows if r.get("code")]
            label = f"{contrato}_{org}_{gt}".replace(" ", "_") if contrato else "C2_group"

            item_id = f"C2_grp_{contrato}_{gt}".replace(" ", "_")

            # Smart merge: C2 uses item_id as its match key
            preserved_state = _preserved.get(item_id)

            items.append({
                "id": item_id,
                "rowNumber": summary_rn,
                "rowId": None,
                "code": label,
                "cmp_status": "new",
                "ss_ha": round(sum(r.get("ss_ha") or 0 for r in pending_rows), 4),
                "agol_ha": None,
                "grant_type": grant_type,
                "contrato": contrato,
                "child_codes": child_codes,
                "child_rows": [
                    {"rowNumber": r.get("rowNumber"), "code": r.get("code", ""),
                     "ss_ha": r.get("ss_ha")}
                    for r in pending_rows
                ],
                "item_state": preserved_state if preserved_state else "pending",
                "step_reached": "preserved" if preserved_state else None,
                "updated_at": None,
            })
    else:
        # ── C1/C3: one item per row ──
        _existing = load_agent_state(dest_folder, allowed_roots)
        _preserved = _extract_done_states(_existing, component, quarter) if _existing else {}

        for g in diagnose_data.get("groups", []):
            grant_type = g.get("grant_type", "")
            contrato = g.get("contrato", "")
            for r in g.get("rows", []):
                if r.get("cmp_status") == "verified_match":
                    continue
                item_id = component + "_row" + str(r.get("rowNumber", 0))

                # Smart merge: prefer code as match key; fallback to item_id
                match_key = r.get("code", "") or item_id
                preserved_state = _preserved.get(match_key)

                items.append({
                    "id": item_id,
                    "rowNumber": r.get("rowNumber"),
                    "rowId": r.get("rowId"),
                    "code": r.get("code", ""),
                    "cmp_status": r.get("cmp_status", ""),
                    "ss_ha": r.get("ss_ha"),
                    "agol_ha": r.get("agol_ha"),
                    "grant_type": grant_type,
                    "contrato": contrato,
                    "item_state": preserved_state if preserved_state else "pending",
                    "step_reached": "preserved" if preserved_state else None,
                    "updated_at": None,
                })

    state = {
        "version": 1,
        "created_at": datetime.now().isoformat(),
        "component": component,
        "quarter": quarter,
        "dest_folder": dest_folder,
        "items": items,
        "summary": _compute_summary(items),
    }
    fp = _state_path(dest_folder, allowed_roots)
    fp.parent.mkdir(parents=True, exist_ok=True)
    fp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def load_agent_state(dest_folder: str, allowed_roots: list[str]) -> dict | None:
    fp = _state_path(dest_folder, allowed_roots)
    if not fp.exists():
        return None
    return json.loads(fp.read_text(encoding="utf-8"))


def update_item(
    dest_folder: str,
    item_id: str,
    updates: dict,
    allowed_roots: list[str],
) -> dict:
    """Update a single item and recompute summary."""
    state = load_agent_state(dest_folder, allowed_roots)
    if state is None:
        raise FileNotFoundError("Agent state not found")
    for item in state["items"]:
        if item["id"] == item_id:
            item.update(updates)
            item["updated_at"] = datetime.now().isoformat()
            break
    else:
        raise KeyError(f"Item {item_id} not found")
    state["summary"] = _compute_summary(state["items"])
    fp = _state_path(dest_folder, allowed_roots)
    fp.write_text(json.dumps(state, ensure_ascii=False, indent=2), encoding="utf-8")
    return state


def reset_agent_state(dest_folder: str, allowed_roots: list[str]) -> bool:
    fp = _state_path(dest_folder, allowed_roots)
    if fp.exists():
        fp.unlink()
        return True
    return False


def _compute_summary(items: list[dict]) -> dict:
    s = {"total": len(items), "done": 0, "skipped": 0, "error": 0,
         "pending": 0, "in_progress": 0}
    for i in items:
        st = i.get("item_state", "pending")
        if st in s:
            s[st] += 1
        else:
            s["pending"] += 1
    return s
