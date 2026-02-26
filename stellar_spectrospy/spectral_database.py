"""
spectral_database.py

Lightweight SQLite-backed storage for stellar spectral analysis results.

Schema
------
    TABLE stars
      - id              INTEGER PRIMARY KEY
      - object_name     TEXT UNIQUE
      - constellation   TEXT
      - spectral_type   TEXT
      - ra_deg          REAL
      - dec_deg         REAL
      - vmag            REAL
      - dist_ly         REAL
      - timestamp       TEXT          -- ISO-8601

    TABLE spectral_metrics
      - id              INTEGER PRIMARY KEY
      - star_id         INTEGER REFERENCES stars(id)
      - peak_frequencies TEXT         -- JSON array of floats [Hz or Å⁻¹]
      - peak_amplitudes  TEXT         -- JSON array of floats
      - coherence_score  REAL         -- RC resonance coherence [0, ∞)
      - e_uv             REAL         -- integrated flux: UV band (W m⁻²)
      - e_vis            REAL         -- integrated flux: VIS band
      - e_ir             REAL         -- integrated flux: IR band
      - e_total          REAL         -- total integrated flux
      - energy_per_peak  TEXT         -- JSON array: E = h*f per peak (J)
      - harmonic_families TEXT        -- JSON array of lists (grouped peaks)
      - analysis_notes   TEXT
      - timestamp        TEXT

Usage
-----
    from stellar_spectrospy.spectral_database import SpectralDatabase

    db = SpectralDatabase()                      # default path
    db.store_star(star_record)
    db.store_metrics(object_name, metrics_dict)
    df = db.query_by_constellation("Taurus")
    db.export_csv("results.csv")
"""

from __future__ import annotations

import json
import sqlite3
import os
import csv
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional, Union

# Physical constants (SI)
PLANCK_H = 6.626e-34          # J·s
SPEED_OF_LIGHT = 2.998e8      # m/s

# Default database location: alongside this file
_DEFAULT_DB = Path(__file__).parent / "spectral_results.db"


class SpectralDatabase:
    """
    Thread-safe SQLite wrapper for storing stellar spectral analysis results.

    Parameters
    ----------
    db_path : str or Path, optional
        Path to the .db file. Created on first use if absent.
    """

    def __init__(self, db_path: Union[str, Path, None] = None):
        self.db_path = Path(db_path) if db_path else _DEFAULT_DB
        self._con: Optional[sqlite3.Connection] = None
        self._init_db()

    # ------------------------------------------------------------------
    # Private helpers
    # ------------------------------------------------------------------

    def _connect(self) -> sqlite3.Connection:
        if self._con is None:
            self._con = sqlite3.connect(self.db_path, check_same_thread=False)
            self._con.row_factory = sqlite3.Row
        return self._con

    def _init_db(self) -> None:
        con = self._connect()
        con.executescript("""
            CREATE TABLE IF NOT EXISTS stars (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                object_name     TEXT    NOT NULL UNIQUE,
                constellation   TEXT,
                spectral_type   TEXT,
                ra_deg          REAL,
                dec_deg         REAL,
                vmag            REAL,
                dist_ly         REAL,
                timestamp       TEXT    NOT NULL
            );

            CREATE TABLE IF NOT EXISTS spectral_metrics (
                id               INTEGER PRIMARY KEY AUTOINCREMENT,
                star_id          INTEGER NOT NULL REFERENCES stars(id),
                peak_frequencies TEXT,
                peak_amplitudes  TEXT,
                coherence_score  REAL,
                e_uv             REAL,
                e_vis            REAL,
                e_ir             REAL,
                e_total          REAL,
                energy_per_peak  TEXT,
                harmonic_families TEXT,
                analysis_notes   TEXT,
                timestamp        TEXT    NOT NULL
            );

            CREATE INDEX IF NOT EXISTS idx_stars_constellation
                ON stars (constellation);
        """)
        con.commit()

    def _now(self) -> str:
        return datetime.now(timezone.utc).isoformat()

    # ------------------------------------------------------------------
    # Public API — writing
    # ------------------------------------------------------------------

    def store_star(self, star) -> int:
        """
        Insert or update a StarRecord (from zodiac_targets) into the stars table.

        Returns the rowid of the upserted row.
        """
        con = self._connect()
        cur = con.execute("""
            INSERT INTO stars
                (object_name, constellation, spectral_type, ra_deg, dec_deg,
                 vmag, dist_ly, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT(object_name) DO UPDATE SET
                constellation   = excluded.constellation,
                spectral_type   = excluded.spectral_type,
                ra_deg          = excluded.ra_deg,
                dec_deg         = excluded.dec_deg,
                vmag            = excluded.vmag,
                dist_ly         = excluded.dist_ly,
                timestamp       = excluded.timestamp
        """, (
            star.name,
            star.constellation,
            star.spectral_type,
            star.ra_deg,
            star.dec_deg,
            star.vmag,
            star.dist_ly,
            self._now(),
        ))
        con.commit()
        # Retrieve the id regardless of insert or update
        cur2 = con.execute("SELECT id FROM stars WHERE object_name = ?", (star.name,))
        return cur2.fetchone()["id"]

    def store_metrics(
        self,
        object_name: str,
        metrics: Dict[str, Any],
        notes: str = "",
    ) -> None:
        """
        Persist spectral analysis results for a star.

        Expected keys in *metrics* (all optional – missing ones stored as NULL):
          peak_frequencies  : list[float]
          peak_amplitudes   : list[float]
          coherence_score   : float
          e_uv, e_vis, e_ir, e_total : float   (integrated flux bands, W m⁻²)
          energy_per_peak   : list[float]        (E = h·f per peak, J)
          harmonic_families : list[list[float]]
        """
        con = self._connect()
        row = con.execute(
            "SELECT id FROM stars WHERE object_name = ?", (object_name,)
        ).fetchone()
        if row is None:
            raise ValueError(
                f"Star '{object_name}' not found in database. "
                "Call store_star() first."
            )
        star_id = row["id"]

        def _json(val):
            return json.dumps(val) if val is not None else None

        con.execute("""
            INSERT INTO spectral_metrics
                (star_id, peak_frequencies, peak_amplitudes, coherence_score,
                 e_uv, e_vis, e_ir, e_total,
                 energy_per_peak, harmonic_families, analysis_notes, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            star_id,
            _json(metrics.get("peak_frequencies")),
            _json(metrics.get("peak_amplitudes")),
            metrics.get("coherence_score"),
            metrics.get("e_uv"),
            metrics.get("e_vis"),
            metrics.get("e_ir"),
            metrics.get("e_total"),
            _json(metrics.get("energy_per_peak")),
            _json(metrics.get("harmonic_families")),
            notes,
            self._now(),
        ))
        con.commit()

    # ------------------------------------------------------------------
    # Public API — reading
    # ------------------------------------------------------------------

    def query_by_constellation(self, constellation: str) -> List[Dict[str, Any]]:
        """
        Return the most-recent metric record per star for a given constellation.

        Returns a list of dicts merging stars + most-recent spectral_metrics.
        """
        con = self._connect()
        rows = con.execute("""
            SELECT s.object_name, s.constellation, s.spectral_type, s.vmag,
                   s.ra_deg, s.dec_deg, s.dist_ly,
                   m.peak_frequencies, m.peak_amplitudes, m.coherence_score,
                   m.e_uv, m.e_vis, m.e_ir, m.e_total,
                   m.energy_per_peak, m.harmonic_families,
                   m.analysis_notes, m.timestamp
            FROM stars s
            LEFT JOIN (
                SELECT star_id, MAX(timestamp) AS max_ts
                FROM spectral_metrics
                GROUP BY star_id
            ) latest ON latest.star_id = s.id
            LEFT JOIN spectral_metrics m
                ON m.star_id = s.id AND m.timestamp = latest.max_ts
            WHERE LOWER(s.constellation) = LOWER(?)
            ORDER BY s.vmag
        """, (constellation,)).fetchall()
        return [dict(r) for r in rows]

    def query_all(self) -> List[Dict[str, Any]]:
        """Return one row per star (most-recent metrics, deduplicated)."""
        con = self._connect()
        rows = con.execute("""
            SELECT s.object_name, s.constellation, s.spectral_type, s.vmag,
                   m.coherence_score, m.e_total, m.e_uv, m.e_vis, m.e_ir,
                   m.timestamp
            FROM stars s
            LEFT JOIN (
                SELECT star_id, MAX(timestamp) AS max_ts
                FROM spectral_metrics
                GROUP BY star_id
            ) latest ON latest.star_id = s.id
            LEFT JOIN spectral_metrics m
                ON m.star_id = s.id AND m.timestamp = latest.max_ts
            ORDER BY s.constellation, s.vmag
        """).fetchall()
        return [dict(r) for r in rows]

    def get_star_metrics(self, object_name: str) -> Optional[Dict[str, Any]]:
        """Return the most-recent metrics row for one star."""
        con = self._connect()
        row = con.execute("""
            SELECT m.*
            FROM spectral_metrics m
            JOIN stars s ON s.id = m.star_id
            WHERE LOWER(s.object_name) = LOWER(?)
            ORDER BY m.timestamp DESC
            LIMIT 1
        """, (object_name,)).fetchone()
        if row is None:
            return None
        d = dict(row)
        # Deserialise JSON fields
        for key in ("peak_frequencies", "peak_amplitudes",
                    "energy_per_peak", "harmonic_families"):
            if d.get(key):
                try:
                    d[key] = json.loads(d[key])
                except Exception:
                    pass
        return d

    def list_stars(self) -> List[str]:
        """Return all stored star names."""
        con = self._connect()
        rows = con.execute(
            "SELECT object_name FROM stars ORDER BY constellation, object_name"
        ).fetchall()
        return [r["object_name"] for r in rows]

    # ------------------------------------------------------------------
    # Export
    # ------------------------------------------------------------------

    def export_csv(self, output_path: Union[str, Path] = "spectral_results.csv") -> Path:
        """
        Write all stars + most-recent metrics to a CSV file.

        Returns the path of the written file.
        """
        output_path = Path(output_path)
        rows = self.query_all()
        if not rows:
            print("No data to export.")
            return output_path

        fieldnames = list(rows[0].keys())
        with open(output_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            writer.writerows(rows)

        print(f"Exported {len(rows)} records → {output_path}")
        return output_path

    # ------------------------------------------------------------------
    # Utility
    # ------------------------------------------------------------------

    def status(self) -> str:
        """Return a brief summary of database contents."""
        con = self._connect()
        n_stars = con.execute("SELECT COUNT(*) FROM stars").fetchone()[0]
        n_metrics = con.execute("SELECT COUNT(*) FROM spectral_metrics").fetchone()[0]
        n_const = con.execute(
            "SELECT COUNT(DISTINCT constellation) FROM stars"
        ).fetchone()[0]
        return (
            f"SpectralDatabase  path={self.db_path}\n"
            f"  Stars stored    : {n_stars}\n"
            f"  Metric records  : {n_metrics}\n"
            f"  Constellations  : {n_const}"
        )

    def close(self) -> None:
        if self._con:
            self._con.close()
            self._con = None

    def __repr__(self) -> str:
        return f"SpectralDatabase(db_path='{self.db_path}')"
