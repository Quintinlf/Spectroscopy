"""SQLite persistence layer for timed planetary spectra and metrics."""

from __future__ import annotations

import csv
import json
import sqlite3
from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

import numpy as np

pd = None
try:
    import pandas as pd
    _PANDAS_OK = True
except ImportError:
    _PANDAS_OK = False

from stellar_spectrospy.spectral_database import SpectralDatabase

from .planetary_catalog import CelestialBody, get_body_by_name
from .spectrum_cache import SpectrumCache

DateLike = Union[str, date, datetime]
_DEFAULT_DB = Path(__file__).parent / "planetary_results.db"


@dataclass
class _LegacyStarLike:
    """Adapter record so planetary objects can be persisted in SpectralDatabase."""

    name: str
    constellation: str
    spectral_type: str
    ra_deg: float
    dec_deg: float
    vmag: float
    dist_ly: float
    notes: str = ""


class PlanetarySpectralDatabase:
    """Stores planetary spectra with date tags and temporal metrics."""

    def __init__(self, db_path: Union[str, Path, None] = None):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._con: Optional[sqlite3.Connection] = None
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        if self._con is None:
            self._con = sqlite3.connect(self.db_path, check_same_thread=False)
            self._con.row_factory = sqlite3.Row
        return self._con

    @staticmethod
    def _now() -> str:
        return datetime.now(timezone.utc).isoformat()

    @staticmethod
    def _normalize_date(value: Optional[DateLike]) -> str:
        return SpectrumCache.normalize_date(value)

    @staticmethod
    def _json(value: Any) -> Optional[str]:
        if value is None:
            return None
        return json.dumps(value)

    @staticmethod
    def _json_load(value: Optional[str]) -> Any:
        if value is None:
            return None
        try:
            return json.loads(value)
        except Exception:
            return value

    def _init_db(self) -> None:
        con = self._connect()
        con.executescript(
            """
            CREATE TABLE IF NOT EXISTS celestial_objects (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                name              TEXT NOT NULL UNIQUE,
                object_type       TEXT,
                parent_body       TEXT,
                average_distance_au REAL,
                radius_km         REAL,
                mass_kg           REAL,
                orbital_period_days REAL,
                metadata_json     TEXT,
                timestamp         TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS planetary_spectra (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                object_id         INTEGER NOT NULL REFERENCES celestial_objects(id),
                observation_date  TEXT NOT NULL,
                query_timestamp   TEXT NOT NULL,
                source            TEXT,
                wavelength_flux_blob BLOB NOT NULL,
                metadata_json     TEXT,
                timestamp         TEXT NOT NULL,
                UNIQUE(object_id, observation_date, source)
            );

            CREATE TABLE IF NOT EXISTS planetary_metrics (
                id                INTEGER PRIMARY KEY AUTOINCREMENT,
                spectrum_id       INTEGER NOT NULL REFERENCES planetary_spectra(id),
                comparison_spectrum_id INTEGER REFERENCES planetary_spectra(id),
                peak_frequencies  TEXT,
                peak_amplitudes   TEXT,
                coherence_score   REAL,
                e_uv              REAL,
                e_vis             REAL,
                e_ir              REAL,
                e_total           REAL,
                harmonic_families TEXT,
                spectral_difference_rms REAL,
                detected_shift_angstrom REAL,
                analysis_notes    TEXT,
                timestamp         TEXT NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_planetary_spectra_date
                ON planetary_spectra(object_id, observation_date);
            CREATE INDEX IF NOT EXISTS idx_planetary_metrics_spectrum
                ON planetary_metrics(spectrum_id, timestamp);
            """
        )
        con.commit()

    def store_celestial_object(self, body: CelestialBody) -> int:
        """Insert or update one celestial object record."""

        con = self._connect()
        con.execute(
            """
            INSERT INTO celestial_objects
                (name, object_type, parent_body, average_distance_au, radius_km,
                 mass_kg, orbital_period_days, metadata_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(name) DO UPDATE SET
                object_type = excluded.object_type,
                parent_body = excluded.parent_body,
                average_distance_au = excluded.average_distance_au,
                radius_km = excluded.radius_km,
                mass_kg = excluded.mass_kg,
                orbital_period_days = excluded.orbital_period_days,
                metadata_json = excluded.metadata_json,
                timestamp = excluded.timestamp
            """,
            (
                body.name,
                body.body_type,
                body.parent_body,
                body.average_distance_au,
                body.radius_km,
                body.mass_kg,
                body.orbital_elements.orbital_period_days,
                self._json(
                    {
                        "atmosphere": body.atmosphere,
                        "discovery_year": body.discovery_year,
                        "notes": body.notes,
                    }
                ),
                self._now(),
            ),
        )
        con.commit()
        row = con.execute("SELECT id FROM celestial_objects WHERE name = ?", (body.name,)).fetchone()
        return int(row["id"])

    def _get_object_id(self, target_name: str) -> int:
        row = self._connect().execute(
            "SELECT id FROM celestial_objects WHERE LOWER(name) = LOWER(?)", (target_name,)
        ).fetchone()
        if row is None:
            body = get_body_by_name(target_name)
            if body is None:
                raise KeyError(f"Unknown target '{target_name}'")
            return self.store_celestial_object(body)
        return int(row["id"])

    def store_spectrum(
        self,
        target_name: str,
        wavelength: np.ndarray,
        flux: np.ndarray,
        uncertainty: Optional[np.ndarray] = None,
        observation_date: Optional[DateLike] = None,
        source: str = "unknown",
        metadata: Optional[Dict[str, Any]] = None,
        query_timestamp: Optional[str] = None,
    ) -> int:
        """Store one date-tagged spectrum and return spectrum id."""

        object_id = self._get_object_id(target_name)
        obs_day = self._normalize_date(observation_date)
        blob = SpectrumCache.serialize_spectrum(wavelength, flux, uncertainty=uncertainty)
        q_time = query_timestamp or self._now()

        con = self._connect()
        con.execute(
            """
            INSERT INTO planetary_spectra
                (object_id, observation_date, query_timestamp, source,
                 wavelength_flux_blob, metadata_json, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_id, observation_date, source) DO UPDATE SET
                query_timestamp = excluded.query_timestamp,
                wavelength_flux_blob = excluded.wavelength_flux_blob,
                metadata_json = excluded.metadata_json,
                timestamp = excluded.timestamp
            """,
            (
                object_id,
                obs_day,
                q_time,
                source,
                sqlite3.Binary(blob),
                self._json(metadata or {}),
                self._now(),
            ),
        )
        con.commit()

        row = con.execute(
            """
            SELECT id FROM planetary_spectra
            WHERE object_id = ? AND observation_date = ? AND source = ?
            """,
            (object_id, obs_day, source),
        ).fetchone()
        return int(row["id"])

    def get_spectrum(self, spectrum_id: int) -> Dict[str, Any]:
        """Get one stored spectrum and deserialize arrays."""

        row = self._connect().execute(
            """
            SELECT ps.id, co.name AS object_name, co.object_type,
                   ps.observation_date, ps.query_timestamp, ps.source,
                   ps.wavelength_flux_blob, ps.metadata_json, ps.timestamp
            FROM planetary_spectra ps
            JOIN celestial_objects co ON co.id = ps.object_id
            WHERE ps.id = ?
            """,
            (spectrum_id,),
        ).fetchone()
        if row is None:
            raise KeyError(f"Spectrum id {spectrum_id} not found")

        wavelength, flux, uncertainty = SpectrumCache.deserialize_spectrum(row["wavelength_flux_blob"])
        out = dict(row)
        out["wavelength"] = wavelength
        out["flux"] = flux
        out["intensity"] = flux
        out["uncertainty"] = uncertainty
        out["metadata_json"] = self._json_load(out.get("metadata_json"))
        out.pop("wavelength_flux_blob", None)
        return out

    def query_spectra_as_dataframe(
        self,
        target_name: str,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> Any:
        """Return long-form DataFrame with ML-ready rows for one target."""

        if not _PANDAS_OK:
            raise ImportError("pandas is required for query_spectra_as_dataframe")
        import pandas as pd_local

        records: List[Dict[str, Any]] = []
        rows = self.query_spectra_by_object(target_name, start_date=start_date, end_date=end_date)
        for row in rows:
            spec = self.get_spectrum(int(row["id"]))
            wl = np.asarray(spec["wavelength"], dtype=float)
            it = np.asarray(spec["intensity"], dtype=float)
            unc = np.asarray(spec["uncertainty"], dtype=float)
            for w, i, u in zip(wl, it, unc):
                records.append(
                    {
                        "object_name": spec["object_name"],
                        "object_type": spec["object_type"],
                        "observation_date": spec["observation_date"],
                        "source": spec["source"],
                        "query_timestamp": spec["query_timestamp"],
                        "wavelength": float(w),
                        "intensity": float(i),
                        "uncertainty": float(u),
                    }
                )
        return pd_local.DataFrame(records)

    def query_spectra_by_object(
        self,
        target_name: str,
        start_date: Optional[DateLike] = None,
        end_date: Optional[DateLike] = None,
    ) -> List[Dict[str, Any]]:
        """Return spectra metadata rows by object and optional date range."""

        con = self._connect()
        args: List[Any] = [target_name]
        where = ["LOWER(co.name) = LOWER(?)"]

        if start_date is not None:
            where.append("ps.observation_date >= ?")
            args.append(self._normalize_date(start_date))
        if end_date is not None:
            where.append("ps.observation_date <= ?")
            args.append(self._normalize_date(end_date))

        rows = con.execute(
            f"""
            SELECT ps.id, co.name AS object_name, co.object_type,
                   ps.observation_date, ps.query_timestamp, ps.source,
                   ps.metadata_json, ps.timestamp
            FROM planetary_spectra ps
            JOIN celestial_objects co ON co.id = ps.object_id
            WHERE {' AND '.join(where)}
            ORDER BY ps.observation_date ASC
            """,
            args,
        ).fetchall()

        out = [dict(r) for r in rows]
        for item in out:
            item["metadata_json"] = self._json_load(item.get("metadata_json"))
        return out

    def store_metrics(
        self,
        spectrum_id: int,
        metrics: Dict[str, Any],
        comparison_spectrum_id: Optional[int] = None,
        analysis_notes: str = "",
    ) -> int:
        """Store computed metrics for a spectrum id."""

        con = self._connect()
        con.execute(
            """
            INSERT INTO planetary_metrics
                (spectrum_id, comparison_spectrum_id,
                 peak_frequencies, peak_amplitudes, coherence_score,
                 e_uv, e_vis, e_ir, e_total,
                 harmonic_families, spectral_difference_rms,
                 detected_shift_angstrom, analysis_notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                spectrum_id,
                comparison_spectrum_id,
                self._json(metrics.get("peak_frequencies")),
                self._json(metrics.get("peak_amplitudes")),
                metrics.get("coherence_score"),
                metrics.get("e_uv"),
                metrics.get("e_vis"),
                metrics.get("e_ir"),
                metrics.get("e_total"),
                self._json(metrics.get("harmonic_families")),
                metrics.get("spectral_difference_rms"),
                metrics.get("detected_shift_angstrom"),
                analysis_notes,
                self._now(),
            ),
        )
        con.commit()
        row = con.execute("SELECT last_insert_rowid() AS id").fetchone()
        return int(row["id"])

    def get_latest_metrics(self, target_name: str) -> Optional[Dict[str, Any]]:
        """Return most recent metrics row for a target."""

        row = self._connect().execute(
            """
            SELECT co.name AS object_name, co.object_type, ps.observation_date,
                   pm.*
            FROM planetary_metrics pm
            JOIN planetary_spectra ps ON ps.id = pm.spectrum_id
            JOIN celestial_objects co ON co.id = ps.object_id
            WHERE LOWER(co.name) = LOWER(?)
            ORDER BY pm.timestamp DESC
            LIMIT 1
            """,
            (target_name,),
        ).fetchone()
        if row is None:
            return None

        out = dict(row)
        for key in ("peak_frequencies", "peak_amplitudes", "harmonic_families"):
            out[key] = self._json_load(out.get(key))
        return out

    def export_metrics_csv(self, output_path: Union[str, Path]) -> Path:
        """Export latest metrics rows per object for quick inspection."""

        output = Path(output_path)
        rows = self._connect().execute(
            """
            SELECT co.name AS object_name, co.object_type,
                   ps.observation_date, ps.source,
                   pm.coherence_score, pm.e_total,
                   pm.spectral_difference_rms, pm.detected_shift_angstrom,
                   pm.analysis_notes, pm.timestamp
            FROM planetary_metrics pm
            JOIN planetary_spectra ps ON ps.id = pm.spectrum_id
            JOIN celestial_objects co ON co.id = ps.object_id
            ORDER BY co.name, pm.timestamp DESC
            """
        ).fetchall()

        if not rows:
            output.touch(exist_ok=True)
            return output

        keys = list(dict(rows[0]).keys())
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=keys)
            writer.writeheader()
            for row in rows:
                writer.writerow(dict(row))
        return output

    def sync_latest_to_spectral_database(
        self,
        target_name: str,
        spectral_db: Optional[SpectralDatabase] = None,
    ) -> bool:
        """Bridge latest planetary metrics into the existing SpectralDatabase schema.

        This is the primary compatibility point with spectral_database.py.
        """

        latest = self.get_latest_metrics(target_name)
        body = get_body_by_name(target_name)
        if latest is None or body is None:
            return False

        db = spectral_db or SpectralDatabase()
        db.store_object(
            object_name=body.name,
            object_type=body.body_type,
            group_name="SolarSystem",
            spectral_type=f"{body.body_type.title()} Spectrum",
            metadata={
                "parent_body": body.parent_body,
                "average_distance_au": body.average_distance_au,
            },
        )
        db.store_object_metrics(
            object_name=body.name,
            object_type=body.body_type,
            metrics=latest,
            source="planetary_sync",
            observation_date=latest.get("observation_date"),
            notes=f"Planetary sync from {self.db_path}",
        )
        return True

    def close(self) -> None:
        if self._con is not None:
            self._con.close()
            self._con = None
