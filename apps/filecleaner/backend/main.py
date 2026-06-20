import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "..", "packages"))

from collections import Counter
from dataclasses import dataclass
import csv
import re

from fastapi import APIRouter, Depends, File, Form, UploadFile, HTTPException, BackgroundTasks, Query
from fastapi.responses import RedirectResponse, StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlmodel import Field, SQLModel, select
from typing import Any, Optional, Literal
from datetime import datetime, timezone
import pandas as pd
import io
import json
import boto3
import logging
import httpx

from fastapi.concurrency import run_in_threadpool
from backend_core import create_app, get_current_user, get_session, User, require_product_access, get_settings
from backend_core.database import get_managed_session
from backend_core.data_limits import DEFAULT_MAX_FUZZY_ROWS, is_fuzzy_row_count_allowed
from backend_core.email_service import send_email
from backend_core.file_utilities import process_image_file
from backend_core.outbox_models import SystemOutbox
from backend_core.product_insights import summarize_files
from backend_core.security_utils import is_public_http_url
from backend_core.worker import register_job_handler

settings = get_settings()

logger = logging.getLogger(__name__)

MAX_FILE_SIZE = 100 * 1024 * 1024  # 100MB on Free/Pro; chunked v2 will handle larger files.
MAX_RETRIES = 2


def _now_naive() -> datetime:
    return datetime.now(timezone.utc).replace(tzinfo=None)

async def cron_cleanup_files():
    """
    Periodic task to delete files older than 24 hours from S3/R2 and database.
    """
    from datetime import timedelta
    cutoff = _now_naive() - timedelta(hours=24)
    
    async with get_managed_session() as session:
        result = await session.execute(
            select(ProcessedFile).where(ProcessedFile.created_at < cutoff)
        )
        old_files = result.scalars().all()
        
        if not old_files:
            return 0
            
        bucket_name = settings.s3_bucket_name
        s3 = _get_s3_client()
        
        count = 0
        for f in old_files:
            # Delete from R2
            if bucket_name:
                keys = [
                    f.raw_object_key,
                    f.cleaned_object_key,
                    f.report_object_key,
                    f"raw/{f.id}_{f.original_name}",
                    f"cleaned/{f.id}_{f.original_name}",
                    f"magic-clean/{f.id}_{f.original_name}",
                    f"reports/{f.id}.json",
                ]
                for key in {item for item in keys if item}:
                    try:
                        s3.delete_object(Bucket=bucket_name, Key=key)
                    except Exception:
                        pass
            # Delete from DB
            await session.delete(f)
            count += 1
            
        await session.commit()
        return count

# --- Models ---
class ProcessedFile(SQLModel, table=True):
    __tablename__ = "processed_files"
    id: Optional[int] = Field(default=None, primary_key=True)
    user_id: int = Field(index=True)
    original_name: str
    size_bytes: int
    status: str = Field(default="pending")    # pending | processing | completed | failed | canceled
    download_url: Optional[str] = None
    raw_object_key: Optional[str] = None
    cleaned_object_key: Optional[str] = None
    report_object_key: Optional[str] = None
    detection_json: str = Field(default="{}")
    config_json: str = Field(default="{}")
    report_json: str = Field(default="{}")
    retry_count: int = Field(default=0)
    notify_email: Optional[str] = None
    notify_webhook_url: Optional[str] = None
    # Cleanup stats
    rows_original: int = Field(default=0)
    rows_clean: int = Field(default=0)
    duplicates_removed: int = Field(default=0)
    empty_removed: int = Field(default=0)
    whitespace_fixed: int = Field(default=0)
    error_message: Optional[str] = None
    created_at: datetime = Field(default_factory=_now_naive)
    updated_at: datetime = Field(default_factory=_now_naive)
    completed_at: Optional[datetime] = None


@dataclass
class FileCleanerPipelineResult:
    dataframe: pd.DataFrame
    output: io.BytesIO
    report: dict[str, Any]
    detection: dict[str, Any]


def _get_s3_client():
    return boto3.client(
        's3',
        endpoint_url=settings.s3_endpoint_url,
        aws_access_key_id=settings.s3_access_key_id,
        aws_secret_access_key=settings.s3_secret_access_key,
        region_name="auto"
    )

def _json_safe(value: Any) -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    if isinstance(value, pd.Timestamp):
        if value.tzinfo is not None:
            value = value.tz_convert("UTC").tz_localize(None)
        return value.isoformat()
    if isinstance(value, datetime):
        return value.isoformat()
    if isinstance(value, (str, int, float, bool)):
        return value
    return str(value)


def _df_preview(df: pd.DataFrame, limit: int = 100) -> list[dict[str, Any]]:
    preview = df.head(limit).where(pd.notna(df.head(limit)), None)
    return [
        {str(key): _json_safe(value) for key, value in row.items()}
        for row in preview.to_dict(orient="records")
    ]


def _parse_json_field(raw: str | None, default: Any = None) -> Any:
    if not raw:
        return {} if default is None else default
    try:
        return json.loads(raw)
    except (TypeError, json.JSONDecodeError):
        return {} if default is None else default


def _dump_json_field(payload: Any) -> str:
    return json.dumps(payload, ensure_ascii=False, default=_json_safe)


def _looks_binary(text: str) -> bool:
    if "\x00" in text:
        return True
    if not text:
        return False
    control_chars = sum(1 for char in text if ord(char) < 32 and char not in "\r\n\t")
    return control_chars / max(len(text), 1) > 0.05


def _decode_content(content: bytes) -> tuple[str, str]:
    for encoding in ("utf-8-sig", "utf-8", "utf-16", "latin-1"):
        try:
            decoded = content.decode(encoding)
        except UnicodeDecodeError:
            continue
        if not _looks_binary(decoded):
            return decoded, "utf-8" if encoding == "utf-8-sig" else encoding
    raise ValueError("Unable to detect a readable text encoding")


def _detect_delimiter(sample: str) -> str:
    try:
        return csv.Sniffer().sniff(sample[:65536], delimiters=",;\t|").delimiter
    except csv.Error:
        counts = {delimiter: sample.count(delimiter) for delimiter in [",", ";", "\t", "|"]}
        delimiter, count = max(counts.items(), key=lambda item: item[1])
        if count <= 0:
            raise ValueError("Unable to detect a CSV delimiter")
        return delimiter


def _detect_headers(sample: str, delimiter: str) -> bool:
    try:
        sniffer_result = csv.Sniffer().has_header(sample[:65536])
    except csv.Error:
        sniffer_result = True
    try:
        rows = list(csv.reader(io.StringIO(sample[:65536]), delimiter=delimiter))
    except csv.Error:
        return sniffer_result
    rows = [row for row in rows if any(cell.strip() for cell in row)]
    if len(rows) < 2:
        return sniffer_result
    first = [cell.strip() for cell in rows[0]]
    second = [cell.strip() for cell in rows[1]]
    if len(first) != len(second) or not first:
        return sniffer_result
    first_unique = len(set(first)) == len(first)
    first_looks_named = sum(bool(re.search(r"[A-Za-z_]", cell)) for cell in first) >= max(1, len(first) // 2)
    second_has_data = any(bool(re.search(r"\d|@|[$€]", cell)) for cell in second)
    return bool(sniffer_result or (first_unique and first_looks_named and second_has_data))


def _manual_options(error: str) -> dict[str, Any]:
    return {
        "error": error,
        "encoding": ["utf-8", "utf-8-sig", "utf-16", "latin-1"],
        "delimiter": [",", ";", "\\t", "|"],
        "header_mode": ["first_row", "no_header"],
    }


def _load_df(
    content: bytes,
    filename: str,
    *,
    encoding: str | None = None,
    delimiter: str | None = None,
    headers: bool = True,
) -> pd.DataFrame:
    normalized = filename.lower()
    if normalized.endswith('.csv'):
        if encoding is None:
            decoded, encoding = _decode_content(content)
            delimiter = delimiter or _detect_delimiter(decoded)
            source: io.BytesIO | io.StringIO = io.StringIO(decoded)
        else:
            source = io.BytesIO(content)
        header = 0 if headers else None
        return pd.read_csv(
            source,
            sep=delimiter or ",",
            encoding=None if isinstance(source, io.StringIO) else encoding,
            header=header,
            skip_blank_lines=True,
        )
    if normalized.endswith('.json'):
        df = pd.read_json(io.BytesIO(content))
        if isinstance(df, pd.Series):
            df = df.to_frame().T
        return df
    return pd.read_excel(io.BytesIO(content))

def _save_df(df: pd.DataFrame, filename: str) -> io.BytesIO:
    buf = io.BytesIO()
    normalized = filename.lower()
    if normalized.endswith('.csv'):
        df.to_csv(buf, index=False)
    elif normalized.endswith('.json'):
        buf.write(df.to_json(orient="records", force_ascii=False, indent=2).encode("utf-8"))
    else:
        df.to_excel(buf, index=False)
    buf.seek(0)
    return buf


def detect_file_profile(content: bytes, filename: str, *, manual_options: dict[str, Any] | None = None) -> dict[str, Any]:
    normalized = filename.lower()
    base: dict[str, Any] = {
        "filename": filename,
        "size_bytes": len(content),
        "encoding": None,
        "delimiter": None,
        "headers_detected": True,
        "loadable": False,
    }
    try:
        options = manual_options or {}
        if normalized.endswith(".csv"):
            if options.get("encoding") and options.get("delimiter"):
                encoding = str(options["encoding"])
                decoded = content.decode(encoding)
                delimiter = str(options["delimiter"]).replace("\\t", "\t")
            else:
                decoded, encoding = _decode_content(content)
                delimiter = _detect_delimiter(decoded)
            headers_detected = _detect_headers(decoded, delimiter)
            df = _load_df(content, filename, encoding=encoding, delimiter=delimiter, headers=headers_detected)
            base.update({"encoding": encoding, "delimiter": delimiter, "headers_detected": headers_detected})
        else:
            df = _load_df(content, filename)
            base.update({"encoding": "binary" if normalized.endswith((".xlsx", ".xls")) else "utf-8"})

        base.update({
            "loadable": True,
            "row_count": int(len(df)),
            "column_count": int(len(df.columns)),
            "columns": [str(column) for column in df.columns],
            "preview_row_count": int(min(len(df), 100)),
            "preview": _df_preview(df, 100),
        })
        return base
    except Exception as exc:
        base.update({
            "loadable": False,
            "error": str(exc),
            "manual_options": _manual_options(str(exc)),
        })
        return base


COUNTRY_CODES = {
    "united states": "US",
    "usa": "US",
    "u.s.a.": "US",
    "us": "US",
    "peru": "PE",
    "perú": "PE",
    "pe": "PE",
    "canada": "CA",
    "ca": "CA",
    "mexico": "MX",
    "méxico": "MX",
    "mx": "MX",
    "spain": "ES",
    "españa": "ES",
    "es": "ES",
    "germany": "DE",
    "deutschland": "DE",
    "de": "DE",
    "united kingdom": "GB",
    "uk": "GB",
    "gb": "GB",
}


def _default_config() -> dict[str, Any]:
    return {
        "basic_cleaning": {
            "drop_empty_rows": True,
            "trim_whitespace": True,
            "normalize_text": True,
            "drop_duplicates": True,
        },
        "fuzzy_matching": {"enabled": True, "columns": [], "threshold": 85},
        "schema_validation": {"rules": []},
        "anomaly_detection": {"enabled": True, "numeric_columns": [], "categorical_columns": []},
        "normalization": {"countries": [], "phones": [], "currencies": [], "dates": []},
    }


def _merge_config(config: dict[str, Any] | None) -> dict[str, Any]:
    merged = _default_config()
    for section, value in (config or {}).items():
        if isinstance(value, dict) and isinstance(merged.get(section), dict):
            merged[section].update(value)
        else:
            merged[section] = value
    return merged


def _basic_clean(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    clean = df.copy()
    rows_original = len(clean)
    null_cells_initial = int(clean.isna().sum().sum())
    text_columns = [col for col in clean.columns if clean[col].dtype == object or str(clean[col].dtype).startswith("string")]
    whitespace_fixed = 0
    text_normalized = 0

    if config.get("trim_whitespace", True):
        for col in text_columns:
            original = clean[col]
            as_string = original.astype("string")
            stripped = as_string.str.strip()
            mask = original.notna() & (as_string != stripped)
            whitespace_fixed += int(mask.sum())
            clean[col] = stripped.where(original.notna(), original)

    if config.get("normalize_text", True):
        for col in text_columns:
            original = clean[col]
            as_string = original.astype("string")
            collapsed = as_string.str.replace(r"\s+", " ", regex=True)
            mask = original.notna() & (as_string != collapsed)
            text_normalized += int(mask.sum())
            clean[col] = collapsed.where(original.notna(), original)
            clean[col] = clean[col].replace("", pd.NA)

    rows_before_empty = len(clean)
    if config.get("drop_empty_rows", True):
        clean = clean.dropna(how="all")
    empty_removed = rows_before_empty - len(clean)

    rows_before_dup = len(clean)
    if config.get("drop_duplicates", True):
        clean = clean.drop_duplicates()
    duplicates_removed = rows_before_dup - len(clean)

    report = {
        "rows_original": int(rows_original),
        "rows_clean": int(len(clean)),
        "duplicates_removed": int(duplicates_removed),
        "empty_removed": int(empty_removed),
        "whitespace_fixed": int(whitespace_fixed),
        "text_normalized": int(text_normalized),
        "null_cells_initial": int(null_cells_initial),
        "null_cells_remaining": int(clean.isna().sum().sum()),
    }
    return clean, report


def _normalize_country(value: Any) -> Any:
    if value is None:
        return value
    try:
        if pd.isna(value):
            return value
    except (TypeError, ValueError):
        pass
    key = str(value).strip().lower()
    return COUNTRY_CODES.get(key, str(value).strip())


def _normalize_phone(value: Any, default_country_code: str = "+1") -> Any:
    if value is None:
        return None
    try:
        if pd.isna(value):
            return None
    except (TypeError, ValueError):
        pass
    raw = str(value).strip()
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return None
    country_digits = re.sub(r"\D", "", default_country_code) or "1"
    if raw.startswith("+"):
        return f"+{digits}"
    if len(digits) > 10 and digits.startswith(country_digits):
        return f"+{digits}"
    if len(digits) == 10 and country_digits == "1":
        return f"+1{digits}"
    if len(digits) == 9 and country_digits == "51":
        return f"+51{digits}"
    if len(digits) >= 7:
        return f"+{country_digits}{digits}"
    return raw


def _parse_currency(value: Any) -> tuple[Any, str | None]:
    if value is None:
        return None, None
    try:
        if pd.isna(value):
            return None, None
    except (TypeError, ValueError):
        pass
    raw = str(value).strip()
    upper = raw.upper()
    currency = None
    if "$" in raw or "USD" in upper:
        currency = "USD"
    elif "S/" in upper or "PEN" in upper:
        currency = "PEN"
    elif "EUR" in upper or "€" in raw:
        currency = "EUR"
    number = re.sub(r"[^0-9,.\-]", "", raw)
    if "," in number and "." in number:
        number = number.replace(",", "")
    elif "," in number and "." not in number:
        number = number.replace(",", ".")
    try:
        return float(number), currency
    except ValueError:
        return value, currency


def _normalize_data(df: pd.DataFrame, config: dict[str, Any]) -> tuple[pd.DataFrame, dict[str, Any]]:
    normalized = df.copy()
    report = {
        "countries_normalized": 0,
        "phones_normalized": 0,
        "currencies_normalized": 0,
        "dates_normalized": 0,
        "columns": {},
    }

    for column in config.get("countries", []) or []:
        if column not in normalized.columns:
            continue
        before = normalized[column].copy()
        normalized[column] = normalized[column].apply(_normalize_country)
        changed = int((before.astype("string") != normalized[column].astype("string")).fillna(False).sum())
        report["countries_normalized"] += changed
        report["columns"][column] = {"type": "country_iso", "changed": changed}

    for phone_rule in config.get("phones", []) or []:
        column = phone_rule.get("column") if isinstance(phone_rule, dict) else str(phone_rule)
        default_code = phone_rule.get("default_country_code", "+1") if isinstance(phone_rule, dict) else "+1"
        if column not in normalized.columns:
            continue
        before = normalized[column].copy()
        normalized[column] = normalized[column].apply(lambda value: _normalize_phone(value, default_code))
        changed = int((before.astype("string") != normalized[column].astype("string")).fillna(False).sum())
        report["phones_normalized"] += changed
        report["columns"][column] = {"type": "e164_phone", "changed": changed}

    for column in config.get("currencies", []) or []:
        if column not in normalized.columns:
            continue
        parsed = normalized[column].apply(_parse_currency)
        normalized[column] = parsed.apply(lambda item: item[0])
        currency_column = f"{column}_currency"
        normalized[currency_column] = parsed.apply(lambda item: item[1])
        changed = int(parsed.apply(lambda item: item[1] is not None).sum())
        report["currencies_normalized"] += changed
        report["columns"][column] = {"type": "currency_amount", "changed": changed, "currency_column": currency_column}

    for column in config.get("dates", []) or []:
        if column not in normalized.columns:
            continue
        before = normalized[column].copy()
        parsed = pd.to_datetime(normalized[column], errors="coerce", utc=True)
        formatted = parsed.dt.strftime("%Y-%m-%dT%H:%M:%SZ")
        normalized[column] = formatted.where(parsed.notna(), before.astype("string"))
        changed = int(parsed.notna().sum())
        report["dates_normalized"] += changed
        report["columns"][column] = {"type": "iso8601_utc", "changed": changed}

    return normalized, report


def _jaro_winkler_similarity(left: str, right: str) -> int:
    s1 = left.lower()
    s2 = right.lower()
    if s1 == s2:
        return 100
    if not s1 or not s2:
        return 0

    match_distance = max(len(s1), len(s2)) // 2 - 1
    s1_matches = [False] * len(s1)
    s2_matches = [False] * len(s2)
    matches = 0

    for i, char in enumerate(s1):
        start = max(0, i - match_distance)
        end = min(i + match_distance + 1, len(s2))
        for j in range(start, end):
            if s2_matches[j] or char != s2[j]:
                continue
            s1_matches[i] = True
            s2_matches[j] = True
            matches += 1
            break

    if matches == 0:
        return 0

    transpositions = 0
    k = 0
    for i, char in enumerate(s1):
        if not s1_matches[i]:
            continue
        while not s2_matches[k]:
            k += 1
        if char != s2[k]:
            transpositions += 1
        k += 1

    jaro = (
        matches / len(s1)
        + matches / len(s2)
        + (matches - transpositions / 2) / matches
    ) / 3
    prefix = 0
    for left_char, right_char in zip(s1, s2):
        if left_char == right_char and prefix < 4:
            prefix += 1
        else:
            break
    winkler = jaro + prefix * 0.1 * (1 - jaro)
    return int(round(winkler * 100))


def _score_similarity(left: str, right: str) -> dict[str, int]:
    try:
        from thefuzz import fuzz
        return {
            "levenshtein": int(fuzz.ratio(left, right)),
            "jaro_winkler": _jaro_winkler_similarity(left, right),
            "token_set": int(fuzz.token_set_ratio(left, right)),
        }
    except Exception:
        from difflib import SequenceMatcher
        score = int(SequenceMatcher(None, left.lower(), right.lower()).ratio() * 100)
        return {"levenshtein": score, "jaro_winkler": _jaro_winkler_similarity(left, right), "token_set": score}


def _run_fuzzy_matching(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    if not config.get("enabled", True):
        return {"enabled": False, "clusters_found": 0, "clusters": []}
    if not is_fuzzy_row_count_allowed(len(df)):
        return {
            "enabled": True,
            "error": f"Fuzzy matching limited to {DEFAULT_MAX_FUZZY_ROWS} rows",
            "code": "too_many_rows",
            "total_rows": int(len(df)),
            "clusters_found": 0,
            "clusters": [],
        }

    columns = config.get("columns") or [
        column for column in df.columns
        if df[column].dtype == object or str(df[column].dtype).startswith("string")
    ]
    threshold = int(config.get("threshold", 85))
    clusters: list[dict[str, Any]] = []

    for column in columns:
        if column not in df.columns:
            continue
        value_rows: dict[str, list[int]] = {}
        for row_index, value in df[column].dropna().items():
            text = str(value).strip()
            if text:
                value_rows.setdefault(text, []).append(int(row_index))
        values = list(value_rows.keys())
        visited: set[str] = set()
        for value in values:
            if value in visited:
                continue
            members = [{"value": value, "rows": value_rows[value], "score": 100}]
            for candidate in values:
                if candidate == value or candidate in visited:
                    continue
                scores = _score_similarity(value, candidate)
                score = max(scores.values())
                if score >= threshold:
                    members.append({"value": candidate, "rows": value_rows[candidate], "score": score, "scores": scores})
                    visited.add(candidate)
            if len(members) > 1:
                visited.add(value)
                representative = max(members, key=lambda item: (len(item["rows"]), -len(item["value"])))["value"]
                clusters.append({
                    "column": column,
                    "representative": representative,
                    "values": members,
                    "row_count": int(sum(len(item["rows"]) for item in members)),
                })

    return {
        "enabled": True,
        "threshold": threshold,
        "algorithms": ["Levenshtein", "Jaro-Winkler", "Token Set"],
        "columns": list(columns),
        "clusters_found": len(clusters),
        "rows_affected": int(sum(cluster["row_count"] for cluster in clusters)),
        "clusters": clusters[:100],
    }


def _schema_value_errors(value: Any, rule: dict[str, Any], df: pd.DataFrame, row_index: Any) -> list[str]:
    errors: list[str] = []
    is_missing = value is None
    if not is_missing:
        try:
            is_missing = bool(pd.isna(value))
        except (TypeError, ValueError):
            is_missing = False
    if isinstance(value, str) and not value.strip():
        is_missing = True
    if rule.get("not_null") and is_missing:
        errors.append("not_null")
        return errors
    if is_missing:
        return errors

    rule_type = str(rule.get("type", "string")).lower()
    text_value = str(value).strip()
    numeric_value: float | None = None

    if rule_type == "email":
        if not re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", text_value):
            errors.append("email")
    elif rule_type == "int":
        try:
            numeric_value = float(text_value)
            if not numeric_value.is_integer():
                errors.append("int")
        except ValueError:
            errors.append("int")
    elif rule_type == "float":
        try:
            numeric_value = float(text_value)
        except ValueError:
            errors.append("float")
    elif rule_type == "date":
        if pd.isna(pd.to_datetime(text_value, errors="coerce", utc=True)):
            errors.append("date")
    elif rule_type == "regex":
        pattern = rule.get("pattern")
        if pattern and not re.match(str(pattern), text_value):
            errors.append("regex")

    if numeric_value is None and ("min" in rule or "max" in rule):
        try:
            numeric_value = float(text_value)
        except ValueError:
            errors.append("numeric_constraint")

    if numeric_value is not None:
        if "min" in rule and numeric_value < float(rule["min"]):
            errors.append("min")
        if "max" in rule and numeric_value > float(rule["max"]):
            errors.append("max")

    if "enum" in rule:
        allowed = {str(item) for item in rule.get("enum", [])}
        if text_value not in allowed:
            errors.append("enum")

    foreign_key_column = rule.get("allowed_values_column")
    if foreign_key_column and foreign_key_column in df.columns:
        allowed_values = {str(item) for item in df[foreign_key_column].dropna().tolist()}
        if text_value not in allowed_values:
            errors.append("cross_column_fk")

    if rule.get("unique") and row_index in set(df.index[df[rule["column"]].duplicated(keep=False)]):
        errors.append("unique")

    return errors


def _run_schema_validation(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    rules = config.get("rules", []) or []
    invalid_rows: set[int] = set()
    columns: dict[str, Any] = {}

    for rule in rules:
        column = rule.get("column")
        if not column:
            continue
        errors_by_row: list[dict[str, Any]] = []
        if column not in df.columns:
            columns[str(column)] = {
                "valid_count": 0,
                "invalid_count": int(len(df)),
                "errors": [{"row_index": int(index), "value": None, "reasons": ["missing_column"]} for index in list(df.index)[:100]],
            }
            invalid_rows.update(int(index) for index in df.index)
            continue

        for row_index, value in df[column].items():
            row_errors = _schema_value_errors(value, rule, df, row_index)
            if row_errors:
                invalid_rows.add(int(row_index))
                errors_by_row.append({
                    "row_index": int(row_index),
                    "value": _json_safe(value),
                    "reasons": row_errors,
                })
        columns[str(column)] = {
            "valid_count": int(len(df) - len(errors_by_row)),
            "invalid_count": int(len(errors_by_row)),
            "errors": errors_by_row[:100],
            "constraints": {key: value for key, value in rule.items() if key != "column"},
        }

    return {
        "rules_count": len(rules),
        "valid_rows": int(len(df) - len(invalid_rows)),
        "invalid_rows": int(len(invalid_rows)),
        "columns": columns,
    }


def _pattern_for_value(value: Any) -> str:
    text = str(value)
    text = re.sub(r"[A-Za-z]", "A", text)
    text = re.sub(r"\d", "9", text)
    text = re.sub(r"\s+", " ", text)
    return text[:80]


def _run_anomaly_detection(df: pd.DataFrame, config: dict[str, Any]) -> dict[str, Any]:
    if not config.get("enabled", True):
        return {"enabled": False, "total_flags": 0, "flags": []}
    numeric_columns = config.get("numeric_columns") or [
        column for column in df.columns if pd.api.types.is_numeric_dtype(df[column])
    ]
    categorical_columns = config.get("categorical_columns") or [
        column for column in df.columns if df[column].dtype == object or str(df[column].dtype).startswith("string")
    ]
    flags: list[dict[str, Any]] = []

    for column in numeric_columns:
        if column not in df.columns:
            continue
        numeric = pd.to_numeric(df[column], errors="coerce").dropna()
        if len(numeric) < 3:
            continue
        mean = numeric.mean()
        std = numeric.std(ddof=0)
        q1 = numeric.quantile(0.25)
        q3 = numeric.quantile(0.75)
        iqr = q3 - q1
        median = numeric.median()
        mad = (numeric - median).abs().median()
        for row_index, value in numeric.items():
            methods: list[str] = []
            z_score = abs((value - mean) / std) if std else 0
            if z_score >= float(config.get("zscore_threshold", 3)):
                methods.append("zscore")
            if iqr and (value < q1 - 1.5 * iqr or value > q3 + 1.5 * iqr):
                methods.append("iqr")
            if mad and abs(0.6745 * (value - median) / mad) >= 3.5:
                methods.append("mad")
            if methods:
                flags.append({
                    "type": "outlier",
                    "column": column,
                    "row_index": int(row_index),
                    "value": _json_safe(value),
                    "methods": methods,
                })

    for column in categorical_columns:
        if column not in df.columns:
            continue
        values = df[column].dropna().astype(str)
        if len(values) < 3:
            continue
        counts = values.value_counts()
        unique_ratio = len(counts) / max(len(values), 1)
        if unique_ratio >= float(config.get("max_unique_ratio", 0.9)) and len(values) >= 10:
            flags.append({"type": "unexpected_cardinality", "column": column, "unique_ratio": round(unique_ratio, 3)})
        null_ratio = df[column].isna().mean()
        if null_ratio >= float(config.get("null_cluster_threshold", 0.4)):
            flags.append({"type": "null_cluster", "column": column, "null_ratio": round(float(null_ratio), 3)})
        patterns = Counter(_pattern_for_value(value) for value in values)
        if len(patterns) > 1 and patterns.most_common(1)[0][1] / max(len(values), 1) < 0.8:
            flags.append({
                "type": "format_inconsistency",
                "column": column,
                "patterns": [{"pattern": pattern, "count": count} for pattern, count in patterns.most_common(5)],
            })

    return {"enabled": True, "total_flags": len(flags), "flags": flags[:200]}


def run_filecleaner_pipeline(content: bytes, filename: str, config: dict[str, Any] | None = None) -> FileCleanerPipelineResult:
    merged_config = _merge_config(config)
    detection = detect_file_profile(content, filename, manual_options=merged_config.get("manual_options"))
    if not detection.get("loadable"):
        raise ValueError(f"Manual review required: {detection.get('error', 'unable to load file')}")

    df = _load_df(
        content,
        filename,
        encoding=detection.get("encoding") if filename.lower().endswith(".csv") else None,
        delimiter=detection.get("delimiter"),
        headers=bool(detection.get("headers_detected", True)),
    )
    cleaned, basic_report = _basic_clean(df, merged_config.get("basic_cleaning", {}))
    normalized, normalization_report = _normalize_data(cleaned, merged_config.get("normalization", {}))
    fuzzy_report = _run_fuzzy_matching(normalized, merged_config.get("fuzzy_matching", {}))
    schema_report = _run_schema_validation(normalized, merged_config.get("schema_validation", {}))
    anomaly_report = _run_anomaly_detection(normalized, merged_config.get("anomaly_detection", {}))

    basic_report["rows_clean"] = int(len(normalized))
    report = {
        "version": "filecleaner-pipeline-v1",
        "generated_at": _now_naive().isoformat() + "Z",
        "detection": detection,
        "basic_cleaning": basic_report,
        "fuzzy_matching": fuzzy_report,
        "schema_validation": schema_report,
        "anomaly_detection": anomaly_report,
        "normalization": normalization_report,
        "download_format": filename.rsplit(".", 1)[-1].lower() if "." in filename else "csv",
    }
    return FileCleanerPipelineResult(
        dataframe=normalized,
        output=_save_df(normalized, filename),
        report=report,
        detection=detection,
    )


async def _notify_file_job(record: ProcessedFile, event: str) -> None:
    payload = {
        "event": f"filecleaner.job.{event}",
        "file_id": record.id,
        "name": record.original_name,
        "status": record.status,
        "download_url": record.download_url,
        "report_url": f"/files/{record.id}/report" if record.id else None,
        "error": record.error_message,
    }

    if record.notify_email:
        subject = f"File Cleaner job {event}: {record.original_name}"
        html = (
            f"<p>Your File Cleaner job for <strong>{record.original_name}</strong> is {record.status}.</p>"
            f"<p>Rows clean: {record.rows_clean}. Rows original: {record.rows_original}.</p>"
            f"{'<p>Error: ' + record.error_message + '</p>' if record.error_message else ''}"
        )
        try:
            await run_in_threadpool(send_email, record.notify_email, subject, html)
        except Exception as exc:
            logger.warning("FileCleaner email notification failed for %s: %s", record.id, exc)

    if record.notify_webhook_url:
        if not is_public_http_url(record.notify_webhook_url):
            logger.warning("Skipped non-public FileCleaner webhook notification for %s", record.id)
            return
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(record.notify_webhook_url, json=payload)
        except Exception as exc:
            logger.warning("FileCleaner webhook notification failed for %s: %s", record.id, exc)


async def _mark_processing_failure(session: AsyncSession, record: ProcessedFile, payload: dict[str, Any], error: str) -> None:
    current_retries = int(record.retry_count or 0)
    if current_retries < MAX_RETRIES:
        record.retry_count = current_retries + 1
        record.status = "pending"
        record.error_message = f"Retry {record.retry_count}/{MAX_RETRIES} scheduled after error: {error[:350]}"
        record.updated_at = _now_naive()
        retry_payload = dict(payload)
        retry_payload["retry_count"] = record.retry_count
        retry_payload["backoff_seconds"] = [60, 120]
        session.add(SystemOutbox(
            app_name="filecleaner",
            job_type="process_csv",
            payload=retry_payload,
            priority=4,
            max_attempts=1,
        ))
        return

    record.status = "failed"
    record.error_message = f"Manual review required after {MAX_RETRIES} retries: {error[:420]}"
    record.updated_at = _now_naive()
    record.completed_at = record.updated_at
    await _notify_file_job(record, "failed")


async def handle_process_csv(payload: dict):
    record_id = payload["record_id"]
    object_key = payload["object_key"]
    filename = payload["filename"]
    
    bucket_name = settings.s3_bucket_name
    s3 = _get_s3_client()

    async with get_managed_session() as session:
        record = await session.get(ProcessedFile, record_id)
        if not record:
            return
        if record.status == "canceled":
            return {"status": "canceled"}

        try:
            record.status = "processing"
            record.updated_at = _now_naive()
            record.error_message = None
            session.add(record)
            await session.commit()

            raw_buf = io.BytesIO()
            s3.download_fileobj(bucket_name, object_key, raw_buf)
            content = raw_buf.getvalue()
            config = _parse_json_field(record.config_json)
            result = await run_in_threadpool(run_filecleaner_pipeline, content, filename, config)

            object_name = f"cleaned/{record.id}_{filename}"
            report_name = f"reports/{record.id}.json"
            s3.upload_fileobj(result.output, bucket_name, object_name)
            s3.upload_fileobj(io.BytesIO(_dump_json_field(result.report).encode("utf-8")), bucket_name, report_name)

            record.status = "completed"
            record.download_url = f"/files/{record.id}/download"
            record.cleaned_object_key = object_name
            record.report_object_key = report_name
            record.detection_json = _dump_json_field(result.detection)
            record.report_json = _dump_json_field(result.report)
            record.rows_original = result.report["basic_cleaning"]["rows_original"]
            record.rows_clean = result.report["basic_cleaning"]["rows_clean"]
            record.duplicates_removed = result.report["basic_cleaning"]["duplicates_removed"]
            record.empty_removed = result.report["basic_cleaning"]["empty_removed"]
            record.whitespace_fixed = result.report["basic_cleaning"]["whitespace_fixed"]
            record.updated_at = _now_naive()
            record.completed_at = record.updated_at
            await _notify_file_job(record, "completed")

        except Exception as e:
            logger.error(f"Background file processing failed for record {record_id}: {e}")
            await _mark_processing_failure(session, record, payload, str(e))

        session.add(record)
        await session.commit()

register_job_handler("filecleaner", "process_csv", handle_process_csv)


def _is_completed_status(status: str | None) -> bool:
    return status in {"completed", "complete"}


def _is_failed_status(status: str | None) -> bool:
    return status in {"failed", "error"}


def _report_from_record(record: ProcessedFile) -> dict[str, Any]:
    base = {
        "rows_original": record.rows_original,
        "rows_clean": record.rows_clean,
        "duplicates_removed": record.duplicates_removed,
        "empty_removed": record.empty_removed,
        "whitespace_fixed": record.whitespace_fixed,
        "rows_saved": record.rows_original - record.rows_clean,
        "reduction_pct": round((1 - record.rows_clean / max(record.rows_original, 1)) * 100, 1),
    }
    full_report = _parse_json_field(record.report_json)
    if isinstance(full_report, dict) and full_report:
        base["pipeline"] = full_report
        for key in ("detection", "fuzzy_matching", "schema_validation", "anomaly_detection", "normalization"):
            if key in full_report:
                base[key] = full_report[key]
    return base


def _serialize_file(record: ProcessedFile) -> dict[str, Any]:
    data: dict[str, Any] = {
        "id": record.id,
        "name": record.original_name,
        "size": record.size_bytes,
        "status": record.status,
        "retry_count": record.retry_count,
        "download_url": record.download_url,
        "report_url": f"/files/{record.id}/report" if record.id else None,
        "detection": _parse_json_field(record.detection_json),
    }
    if _is_completed_status(record.status):
        data["report"] = _report_from_record(record)
    elif _is_failed_status(record.status):
        data["error"] = record.error_message
    return data


def _storage_keys_for_record(record: ProcessedFile) -> list[str]:
    keys = [
        record.raw_object_key,
        record.cleaned_object_key,
        record.report_object_key,
        f"raw/{record.id}_{record.original_name}",
        f"cleaned/{record.id}_{record.original_name}",
        f"magic-clean/{record.id}_{record.original_name}",
        f"reports/{record.id}.json",
    ]
    return list(dict.fromkeys([key for key in keys if key]))


def _delete_storage_objects(record: ProcessedFile) -> None:
    bucket_name = settings.s3_bucket_name
    if not bucket_name:
        return
    s3 = _get_s3_client()
    for key in _storage_keys_for_record(record):
        try:
            s3.delete_object(Bucket=bucket_name, Key=key)
        except Exception:
            logger.warning("Could not delete FileCleaner object %s for record %s", key, record.id)


# --- Routers ---
file_router = APIRouter(prefix="/files", tags=["files"], dependencies=[Depends(require_product_access("filecleaner"))])
demo_router = APIRouter(prefix="/files", tags=["demo"])
settings_router = APIRouter(prefix="/settings", tags=["settings"])


@file_router.post("/analyze")
async def analyze_file_profile(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Preview analysis is limited to 20MB")
    ext = (file.filename or "file.csv").rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "xls", "json"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV, JSON, or Excel.")
    profile = await run_in_threadpool(detect_file_profile, content, file.filename or "file.csv")
    if not profile.get("loadable"):
        return profile
    return profile


@file_router.post("/upload")
async def upload_file(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    config_json: str = Form("{}"),
    notify_email: str = Form(""),
    notify_webhook_url: str = Form(""),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Accepts a file, creates a DB record immediately (status=pending), and
    processes it in the background. Returns {id, status} so the client can poll.
    """
    content = await file.read()
    file_size = file.size or len(content)
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File too large (100MB max on Free/Pro). Upgrade/chunked v2 will support larger files.",
        )

    ext = (file.filename or "file.csv").rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "xls", "json"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV, JSON, or Excel.")

    config = _parse_json_field(config_json)
    if not isinstance(config, dict):
        raise HTTPException(status_code=400, detail="config_json must be a JSON object")
    if notify_webhook_url and not is_public_http_url(notify_webhook_url):
        raise HTTPException(status_code=400, detail="Notify webhook URL must be a public http(s) URL")

    detection = await run_in_threadpool(detect_file_profile, content, file.filename or "file.csv")
    if not detection.get("loadable"):
        raise HTTPException(
            status_code=400,
            detail={
                "message": "Could not detect file format. Provide manual encoding/delimiter/header options.",
                "profile": detection,
            },
        )

    bucket_name = settings.s3_bucket_name
    if not bucket_name:
        raise HTTPException(status_code=500, detail="Storage not configured")

    record = ProcessedFile(
        user_id=user.id,
        original_name=file.filename or "unnamed",
        size_bytes=file_size,
        status="pending",
        detection_json=_dump_json_field(detection),
        config_json=_dump_json_field(config),
        notify_email=notify_email or None,
        notify_webhook_url=notify_webhook_url or None,
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    s3 = _get_s3_client()
    raw_key = f"raw/{record.id}_{record.original_name}"
    record.raw_object_key = raw_key
    session.add(record)
    await run_in_threadpool(s3.upload_fileobj, io.BytesIO(content), bucket_name, raw_key)

    # Enqueue to system_outbox
    job = SystemOutbox(
        app_name="filecleaner",
        job_type="process_csv",
        payload={
            "record_id": record.id,
            "object_key": raw_key,
            "filename": record.original_name,
            "backoff_seconds": [60, 120],
        },
        priority=5,
        max_attempts=1,
    )
    session.add(job)
    await session.commit()

    return {
        "id": record.id,
        "status": "pending",
        "name": record.original_name,
        "detection": detection,
        "report_url": f"/files/{record.id}/report",
    }


@file_router.post("/utility")
async def process_file_utility(
    file: UploadFile = File(...),
    output_format: Optional[Literal["png", "jpg", "jpeg", "webp"]] = Query(default=None),
    quality: int = Query(default=82, ge=1, le=95),
    user: User = Depends(get_current_user),
):
    content = await file.read()
    if len(content) > 50 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Utility processing is limited to 50MB")

    ext = (file.filename or "").rsplit(".", 1)[-1].lower()
    if ext not in {"png", "jpg", "jpeg", "webp", "heic", "heif", "svg", "pdf"}:
        raise HTTPException(status_code=400, detail="Use PNG, JPG, WEBP, HEIC, SVG, or PDF.")

    try:
        processed = await run_in_threadpool(
            process_image_file,
            content,
            file.filename or "file",
            output_format=output_format,
            quality=quality,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    headers = {
        "Content-Disposition": f'attachment; filename="{processed.filename}"',
        "X-DevForge-Metadata-Removed": "true" if processed.metadata_removed else "false",
        "X-DevForge-Bytes-Saved": str(processed.bytes_saved),
        "X-DevForge-Output-Count": str(processed.output_count),
    }
    return StreamingResponse(io.BytesIO(processed.content), media_type=processed.media_type, headers=headers)


@demo_router.post("/demo/upload")
async def demo_upload(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    session: AsyncSession = Depends(get_session),
):
    """
    Public demo endpoint — no signup required.
    Uses a hardcoded GUEST_USER_ID (0).
    """
    GUEST_USER_ID = 0
    content = await file.read()
    file_size = file.size or len(content)
    if file_size > 5 * 1024 * 1024:  # Limit demo to 5MB
        raise HTTPException(status_code=413, detail="Demo limited to 5MB")

    ext = (file.filename or "demo_file.csv").rsplit(".", 1)[-1].lower()
    if ext not in ("csv", "xlsx", "xls", "json"):
        raise HTTPException(status_code=400, detail="Unsupported file type. Use CSV, JSON, or Excel.")

    detection = await run_in_threadpool(detect_file_profile, content, file.filename or "demo_file.csv")
    if not detection.get("loadable"):
        raise HTTPException(status_code=400, detail={"message": "Could not detect file format.", "profile": detection})

    record = ProcessedFile(
        user_id=GUEST_USER_ID,
        original_name=file.filename or "demo_file.csv",
        size_bytes=file_size,
        status="pending",
        detection_json=_dump_json_field(detection),
        config_json=_dump_json_field(_default_config()),
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    bucket_name = settings.s3_bucket_name
    if not bucket_name:
        raise HTTPException(status_code=500, detail="Storage not configured")
        
    s3 = _get_s3_client()
    raw_key = f"demo/{record.id}_{record.original_name}"
    record.raw_object_key = raw_key
    session.add(record)
    
    # Run upload_fileobj in a threadpool to avoid blocking event loop
    await run_in_threadpool(
        s3.upload_fileobj, io.BytesIO(content), bucket_name, raw_key
    )

    job = SystemOutbox(
        app_name="filecleaner",
        job_type="process_csv",
        payload={
            "record_id": record.id,
            "object_key": raw_key,
            "filename": record.original_name,
            "backoff_seconds": [60, 120],
        },
        priority=10, # Demo jobs have lower priority
        max_attempts=1,
    )
    session.add(job)
    await session.commit()

    return {"id": record.id, "status": "pending", "name": record.original_name, "detection": detection}


@demo_router.get("/demo/{file_id}/status")
async def get_demo_file_status(
    file_id: int,
    session: AsyncSession = Depends(get_session),
):
    """Public poll endpoint for demo."""
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != 0:
        raise HTTPException(status_code=404, detail="Demo file not found")

    response: dict = _serialize_file(record)

    if _is_completed_status(record.status):
        response["download_url"] = f"/files/demo/{record.id}/download"
    return response


@demo_router.get("/demo/{file_id}/download")
async def download_demo_file(
    file_id: int,
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != 0:
        raise HTTPException(status_code=404, detail="File not found")

    bucket_name = settings.s3_bucket_name
    if bucket_name:
        s3 = _get_s3_client()
        object_name = record.cleaned_object_key or f"cleaned/{record.id}_{record.original_name}"
        url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': object_name}, ExpiresIn=3600)
        return RedirectResponse(url)
    raise HTTPException(status_code=404, detail="Storage not configured")


@file_router.get("/{file_id}/status")
async def get_file_status(
    file_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """Poll endpoint — returns current processing status and report when complete."""
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")

    return _serialize_file(record)


@file_router.get("/{file_id}/report")
async def get_file_report(
    file_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if not _is_completed_status(record.status) and not _is_failed_status(record.status):
        raise HTTPException(status_code=409, detail="Report is not available until the job finishes")
    return _report_from_record(record)


@file_router.post("/{file_id}/cancel")
async def cancel_file_job(
    file_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="Job not found")
    if _is_completed_status(record.status):
        raise HTTPException(status_code=409, detail="Completed jobs cannot be canceled")
    if record.status != "canceled":
        record.status = "canceled"
        record.updated_at = _now_naive()
        record.error_message = None
        await run_in_threadpool(_delete_storage_objects, record)
        session.add(record)
        await session.commit()
    return {"id": record.id, "status": record.status}


@file_router.get("/list")
async def list_files(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ProcessedFile)
        .where(ProcessedFile.user_id == user.id)
        .order_by(ProcessedFile.created_at.desc())
        .limit(50)
    )
    files = result.scalars().all()
    return [_serialize_file(f) for f in files]


@file_router.get("/summary")
async def get_file_summary(
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    result = await session.execute(
        select(ProcessedFile)
        .where(ProcessedFile.user_id == user.id)
        .order_by(ProcessedFile.created_at.desc())
        .limit(500)
    )
    return summarize_files(result.scalars().all())


@file_router.post("/fuzzy-check")
async def fuzzy_check(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    threshold: int = 85,
):
    """
    Detecta duplicados 'blandos' usando fuzzy matching (thefuzz).
    threshold: similitud mínima 0-100 (default 85).
    """
    content = await file.read()
    if len(content) > 20 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="Fuzzy check limited to 20MB")

    def run_fuzzy(file_content: bytes, fname: str, thresh: int):
        try:
            from thefuzz import fuzz
        except ImportError:
            return {"error": "thefuzz not installed. Run: pip install thefuzz[speedup]", "groups": []}

        df = _load_df(file_content, fname)
        str_rows = df.astype(str).apply(lambda r: " | ".join(r.values), axis=1).tolist()
        n = len(str_rows)
        if not is_fuzzy_row_count_allowed(n):
            return {
                "error": f"Fuzzy check limited to {DEFAULT_MAX_FUZZY_ROWS} rows",
                "code": "too_many_rows",
                "total_rows": n,
                "groups": [],
            }
        visited = set()
        groups = []

        for i in range(n):
            if i in visited:
                continue
            group = [i]
            for j in range(i + 1, n):
                if j in visited:
                    continue
                score = fuzz.token_sort_ratio(str_rows[i], str_rows[j])
                if score >= thresh:
                    group.append(j)
                    visited.add(j)
            if len(group) > 1:
                visited.add(i)
                groups.append({"rows": group, "sample": str_rows[i][:200], "count": len(group)})

        return {
            "total_rows": n,
            "fuzzy_groups_found": len(groups),
            "rows_affected": sum(g["count"] for g in groups),
            "threshold_used": thresh,
            "groups": groups[:50],
        }

    result = await run_in_threadpool(run_fuzzy, content, file.filename or "file.csv", threshold)
    if result.get("code") == "too_many_rows":
        raise HTTPException(status_code=413, detail=result["error"])
    return result


@file_router.post("/magic-clean")
async def magic_clean(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Normalización avanzada: estandariza fechas, teléfonos, emails, precios.
    Procesa en background y retorna un job_id para polling.
    """
    content = await file.read()

    record = ProcessedFile(
        user_id=user.id,
        original_name=file.filename or "unnamed",
        size_bytes=len(content),
        status="pending",
    )
    session.add(record)
    await session.commit()
    await session.refresh(record)

    # Upload raw to R2
    bucket_name = settings.s3_bucket_name
    if not bucket_name:
        raise HTTPException(status_code=500, detail="Storage not configured")
        
    s3 = _get_s3_client()
    raw_key = f"raw/{record.id}_{record.original_name}"
    record.raw_object_key = raw_key
    session.add(record)
    s3.upload_fileobj(io.BytesIO(content), bucket_name, raw_key)

    # Enqueue to system_outbox
    job = SystemOutbox(
        app_name="filecleaner",
        job_type="magic_clean",
        payload={
            "record_id": record.id,
            "object_key": raw_key,
            "filename": record.original_name,
            "backoff_seconds": [60, 120],
        },
        priority=5,
        max_attempts=1,
    )
    session.add(job)
    await session.commit()

    return {"id": record.id, "status": "pending"}

async def handle_magic_clean(payload: dict):
    record_id = payload["record_id"]
    object_key = payload["object_key"]
    filename = payload["filename"]
    
    bucket_name = settings.s3_bucket_name
    s3 = _get_s3_client()
    
    # Download raw file
    raw_buf = io.BytesIO()
    s3.download_fileobj(bucket_name, object_key, raw_buf)
    content = raw_buf.getvalue()

    async with get_managed_session() as bg_session:
        rec = await bg_session.get(ProcessedFile, record_id)
        if not rec:
            return
        try:
            import re
            rec.status = "processing"
            rec.updated_at = _now_naive()
            bg_session.add(rec)
            await bg_session.commit()

            def run_magic(fc: bytes, fn: str):
                df = _load_df(fc, fn)
                for col in df.columns:
                    col_lower = col.lower()
                    s = df[col]
                    if any(k in col_lower for k in ["email", "correo", "mail"]):
                        df[col] = s.astype(str).str.strip().str.lower()
                    elif any(k in col_lower for k in ["phone", "telefono", "tel", "celular"]):
                        def norm_phone(v):
                            if pd.isna(v): return v
                            d = re.sub(r"\D", "", str(v))
                            if len(d) == 9: return f"+51 {d[:3]} {d[3:6]} {d[6:]}"
                            if len(d) == 10: return f"+1 ({d[:3]}) {d[3:6]}-{d[6:]}"
                            return d if d else str(v)
                        df[col] = s.apply(norm_phone)
                    elif any(k in col_lower for k in ["price", "precio", "amount", "monto", "cost", "total"]):
                        def clean_price(v):
                            if pd.isna(v): return v
                            cleaned = re.sub(r"[^\d.,]", "", str(v)).replace(",", ".")
                            try: return float(cleaned)
                            except: return v
                        df[col] = s.apply(clean_price)
                    elif any(k in col_lower for k in ["date", "fecha", "created", "updated"]):
                        df[col] = pd.to_datetime(s, dayfirst=True, errors='coerce').dt.strftime('%Y-%m-%d').where(
                            pd.to_datetime(s, dayfirst=True, errors='coerce').notna(), other=s.astype(str)
                        )
                    elif any(k in col_lower for k in ["name", "nombre", "city", "ciudad"]):
                        df[col] = s.astype(str).str.strip().str.title()
                rows_before = len(df)
                df.dropna(how='all', inplace=True)
                df.drop_duplicates(inplace=True)
                return df, rows_before, len(df)

            df_clean, rows_orig, rows_clean = await run_in_threadpool(run_magic, content, filename)
            out_buf = _save_df(df_clean, filename)

            object_name = f"magic-clean/{rec.id}_{filename}"
            s3.upload_fileobj(out_buf, bucket_name, object_name)

            rec.status = "completed"
            rec.download_url = f"/files/{rec.id}/download?type=magic"
            rec.rows_original = rows_orig
            rec.rows_clean = rows_clean
            rec.cleaned_object_key = object_name
            rec.updated_at = _now_naive()
            rec.completed_at = rec.updated_at
        except Exception as e:
            logger.error(f"Magic clean failed for {record_id}: {e}", exc_info=True)
            rec.status = "failed"
            rec.error_message = str(e)[:500]
            rec.updated_at = _now_naive()
        bg_session.add(rec)
        await bg_session.commit()

register_job_handler("filecleaner", "magic_clean", handle_magic_clean)


@file_router.get("/{file_id}/download")
async def download_file(
    file_id: int,
    type: Optional[str] = Query(None),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="File not found")

    bucket_name = settings.s3_bucket_name
    if bucket_name:
        s3 = _get_s3_client()
        prefix = "magic-clean" if type == "magic" else "cleaned"
        object_name = record.cleaned_object_key if type != "magic" and record.cleaned_object_key else f"{prefix}/{record.id}_{record.original_name}"
        url = s3.generate_presigned_url('get_object', Params={'Bucket': bucket_name, 'Key': object_name}, ExpiresIn=3600)
        return RedirectResponse(url)
    raise HTTPException(status_code=404, detail="Storage not configured")


# ---------------------------------------------------------------------------
# Export endpoint — Skill: backend-architect + react-patterns
# ---------------------------------------------------------------------------
@file_router.get("/export")
async def export_files(
    format: Literal["csv", "xlsx", "json"] = Query(default="csv"),
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    """
    Export all processed files metadata as CSV, XLSX, or JSON.
    Uses pandas (already in stack) — no S3 required.
    """
    result = await session.execute(
        select(ProcessedFile)
        .where(ProcessedFile.user_id == user.id, ProcessedFile.status.in_(["complete", "completed"]))
        .order_by(ProcessedFile.created_at.desc())
    )
    records = result.scalars().all()

    rows = [{
        "id": r.id,
        "name": r.original_name,
        "size_bytes": r.size_bytes,
        "rows_original": r.rows_original,
        "rows_clean": r.rows_clean,
        "duplicates_removed": r.duplicates_removed,
        "empty_removed": r.empty_removed,
        "whitespace_fixed": r.whitespace_fixed,
        "reduction_pct": round((1 - r.rows_clean / max(r.rows_original, 1)) * 100, 1),
        "processed_at": r.created_at.isoformat(),
    } for r in records]

    if format == "json":
        return StreamingResponse(
            io.BytesIO(json.dumps(rows, indent=2).encode()),
            media_type="application/json",
            headers={"Content-Disposition": "attachment; filename=filecleaner_export.json"}
        )

    df = pd.DataFrame(rows)
    buf = io.BytesIO()
    if format == "xlsx":
        df.to_excel(buf, index=False, engine="openpyxl")
        media_type = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        filename = "filecleaner_export.xlsx"
    else:
        df.to_csv(buf, index=False)
        media_type = "text/csv"
        filename = "filecleaner_export.csv"
    buf.seek(0)
    return StreamingResponse(buf, media_type=media_type, headers={"Content-Disposition": f"attachment; filename={filename}"})


# ---------------------------------------------------------------------------
# AI Analyze endpoint — Skill: gemini-api-dev
# ---------------------------------------------------------------------------
@file_router.post("/ai-analyze")
async def ai_analyze_file(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    Reads first 20 rows of the CSV/JSON/Excel and uses Gemini Flash to suggest
    cleanup rules. Falls back to heuristic analysis if no API key.
    """
    content = await file.read()
    if len(content) > 10 * 1024 * 1024:
        raise HTTPException(status_code=413, detail="AI analyze limited to 10MB")

    def analyze_locally(file_content: bytes, fname: str):
        df = _load_df(file_content, fname)
        preview = df.head(20)
        suggestions = []
        for col in preview.columns:
            null_pct = preview[col].isnull().mean()
            if null_pct > 0.5:
                suggestions.append({"column": col, "issue": f"{int(null_pct*100)}% valores nulos", "fix": "Considerar eliminar esta columna", "severity": "high"})
            elif preview[col].dtype == object:
                has_spaces = preview[col].dropna().str.strip().ne(preview[col].dropna()).any()
                if has_spaces:
                    suggestions.append({"column": col, "issue": "Espacios en blanco al inicio/fin", "fix": "Aplicar strip() automáticamente", "severity": "low"})
            if preview[col].dtype == object:
                dup_ratio = 1 - preview[col].nunique() / max(len(preview[col].dropna()), 1)
                if dup_ratio > 0.8:
                    suggestions.append({"column": col, "issue": f"{int(dup_ratio*100)}% valores duplicados", "fix": "Alta repetición — revisar si es categórico", "severity": "medium"})
        return {
            "total_rows": len(df),
            "total_columns": len(df.columns),
            "preview_rows": 20,
            "suggestions": suggestions,
            "engine": "heuristic",
        }

    async def analyze_with_gemini(file_content: bytes, fname: str):
        if not settings.gemini_api_key:
            return None
        try:
            df = await run_in_threadpool(_load_df, file_content, fname)
            preview_csv = df.head(20).to_csv(index=False)
            from google import genai
            client = genai.Client(api_key=settings.gemini_api_key)
            prompt = f"""Analiza este CSV y sugiere reglas de limpieza de datos. Responde en JSON:
{{
  "total_rows": number,
  "total_columns": number,
  "suggestions": [
    {{"column": "nombre_columna", "issue": "descripcion del problema", "fix": "accion recomendada", "severity": "high|medium|low"}}
  ],
  "summary": "resumen general de calidad de los datos"
}}

Primeras 20 filas del CSV:
{preview_csv[:3000]}"""
            response = client.models.generate_content(
                model="gemini-3-flash-preview",
                contents=prompt,
                config={"response_mime_type": "application/json"}
            )
            result = json.loads(response.text)
            result["engine"] = "gemini"
            result["preview_rows"] = min(20, len(df))
            return result
        except Exception as e:
            logger.warning(f"Gemini AI analyze failed: {e}")
            return None

    result = await analyze_with_gemini(content, file.filename or "file.csv")
    if result is None:
        result = await run_in_threadpool(analyze_locally, content, file.filename or "file.csv")
    return result


@file_router.delete("/{file_id}")
async def delete_file(
    file_id: int,
    user: User = Depends(get_current_user),
    session: AsyncSession = Depends(get_session),
):
    record = await session.get(ProcessedFile, file_id)
    if not record or record.user_id != user.id:
        raise HTTPException(status_code=404, detail="File not found")

    await run_in_threadpool(_delete_storage_objects, record)

    await session.delete(record)
    await session.commit()
    return {"message": "Deleted successfully"}


# --- App ---
app = create_app(
    title="File Cleaner",
    description="Upload, process, and clean your CSV/Excel datasets",
    domain_routers=[file_router, demo_router, settings_router]
)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8001, reload=True)
