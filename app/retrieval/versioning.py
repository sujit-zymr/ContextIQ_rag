"""Date and version annotations for retrieved source chunks."""

import re
from datetime import date, datetime
from pathlib import Path


def _date_value(value):
    if isinstance(value, datetime):
        return value.date()
    if isinstance(value, date):
        return value
    if isinstance(value, str) and value.strip():
        try:
            return date.fromisoformat(value.strip())
        except ValueError:
            return None
    return None


def _lineage_key(chunk):
    metadata = chunk.get("metadata") or {}
    title = metadata.get("title") or chunk.get("filename") or "unknown"
    normalized = re.sub(r"[^a-z0-9]+", " ", str(title).lower()).strip()
    return normalized or Path(str(title)).stem.lower()


def _revision_label(metadata, effective):
    version = metadata.get("version")
    if version is not None and effective:
        return f"{version} (effective {effective.isoformat()})"
    if version is not None:
        return f"version {version}"
    if effective:
        return f"effective {effective.isoformat()}"
    return None


def _version_key(value):
    if value is None:
        return None
    numbers = re.findall(r"\d+", str(value))
    return tuple(int(number) for number in numbers) if numbers else None


def annotate_source_versions(chunks, as_of=None):
    """Annotate freshness and competing document versions for a result set."""
    as_of = as_of or date.today()
    annotated = []
    groups = {}
    by_lineage = {}

    for chunk in chunks:
        metadata = chunk.get("metadata") or {}
        effective = _date_value(metadata.get("effective_date"))
        expiry = _date_value(metadata.get("expiry_date"))
        if effective and effective > as_of:
            freshness = "future"
        elif expiry and expiry < as_of:
            freshness = "outdated"
        elif effective or expiry:
            freshness = "current"
        else:
            freshness = "undated"

        result = {
            **chunk,
            "source_freshness": freshness,
            "effective_date": effective.isoformat() if effective else None,
            "expiry_date": expiry.isoformat() if expiry else None,
            "as_of_date": as_of.isoformat(),
            "has_competing_versions": False,
            "competing_versions": [],
        }
        annotated.append(result)

        lineage = _lineage_key(chunk)
        revision = _revision_label(metadata, effective)
        if revision:
            groups.setdefault(lineage, set()).add(revision)
        by_lineage.setdefault(lineage, []).append((result, effective, expiry, metadata.get("version")))

    competing_by_lineage = {
        lineage: sorted(versions)
        for lineage, versions in groups.items()
        if len(versions) > 1
    }
    for result in annotated:
        lineage = _lineage_key(result)
        versions = competing_by_lineage.get(lineage, [])
        result["has_competing_versions"] = bool(versions)
        result["competing_versions"] = versions

    # Mark older revisions when the retrieved candidates contain a newer
    # effective date or comparable numeric version. Effective dates take
    # precedence; a version breaks ties on the same date.
    for revisions in by_lineage.values():
        eligible = [
            item for item in revisions
            if item[0]["source_freshness"] in {"current", "undated"}
        ]
        if len(eligible) < 2:
            continue
        dated = [item for item in eligible if item[1] is not None]
        if dated:
            latest_date = max(item[1] for item in dated)
            latest_date_items = [item for item in dated if item[1] == latest_date]
            dated_eligible = [item for item in eligible if item[1] is not None]
            older = [item for item in dated_eligible if item[1] < latest_date]
            for result, _, _, _ in older:
                result["source_freshness"] = "superseded"
            eligible = latest_date_items

        comparable_versions = [
            (_version_key(item[3]), item)
            for item in eligible
            if _version_key(item[3]) is not None
        ]
        if len(comparable_versions) > 1:
            latest_version = max(key for key, _ in comparable_versions)
            for key, (result, _, _, _) in comparable_versions:
                if key < latest_version:
                    result["source_freshness"] = "superseded"
    return annotated
