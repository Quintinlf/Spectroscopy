"""Fetch planetary spectra with real default resolvers.

Primary source order for ``source='auto'`` is object-aware:
- Surface/reflection objects: NASA PDS -> HITRAN -> synthetic fallback
- Atmospheric objects: HITRAN -> NASA PDS -> synthetic fallback
"""

from __future__ import annotations

import json
import warnings
import importlib.util
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from io import BytesIO, StringIO
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, Union
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

import numpy as np

pd = None
try:
    import pandas as pd

    _PANDAS_OK = True
except ImportError:
    _PANDAS_OK = False

_ASTROPY_FITS_OK = importlib.util.find_spec("astropy.io.fits") is not None
_HORIZONS_OK = (
    importlib.util.find_spec("astroquery.jplhorizons") is not None
    and importlib.util.find_spec("astropy.time") is not None
)

from .planetary_catalog import CelestialBody, get_body_by_name
from .energy_model import ENERGY_MODEL_VERSION, compute_energy_spectrum
from .planetary_targets import register_observation
from .spectrum_cache import SpectrumCache

DateLike = Union[str, date, datetime]

_PDS_SEARCH_URL = "https://pds.nasa.gov/services/search/search"
_SUPPORTED_EXTENSIONS = (
    ".fits",
    ".fit",
    ".fts",
    ".csv",
    ".tab",
    ".txt",
    ".asc",
    ".dat",
)

_PDS_OBJECT_ALIASES: Dict[str, List[str]] = {
    "Moon": ["Moon", "Luna"],
    "Mercury": ["Mercury"],
    "Venus": ["Venus"],
    "Mars": ["Mars"],
    "Jupiter": ["Jupiter"],
    "Saturn": ["Saturn"],
    "Uranus": ["Uranus"],
    "Neptune": ["Neptune"],
    "Ceres": ["Ceres"],
    "Vesta": ["Vesta"],
    "Pallas": ["Pallas"],
    "Juno": ["Juno"],
}

_PDS_MISSION_HINTS: Dict[str, List[str]] = {
    "Moon": ["M3", "Moon Mineralogy Mapper", "Clementine"],
    "Mercury": ["MESSENGER", "MASCS"],
    "Venus": ["VEX", "VIRTIS"],
    "Mars": ["CRISM", "OMEGA", "TES"],
    "Jupiter": ["Galileo", "NIMS", "Voyager"],
    "Saturn": ["Cassini", "VIMS"],
    "Uranus": ["Voyager", "IRIS"],
    "Neptune": ["Voyager", "IRIS"],
    "Ceres": ["Dawn", "VIR"],
    "Vesta": ["Dawn", "VIR"],
    "Pallas": ["SMASS", "S3OS2"],
    "Juno": ["SMASS", "S3OS2"],
}

_ATMOSPHERIC_OBJECTS = {
    "Venus",
    "Mars",
    "Jupiter",
    "Saturn",
    "Uranus",
    "Neptune",
    "Titan",
}

_HITRAN_LOCAL_LINES: Dict[str, List[Tuple[float, float, float]]] = {
    # (center_angstrom, strength, width_angstrom)
    "Venus": [(4300.0, 0.55, 28.0), (7200.0, 0.75, 55.0), (8400.0, 0.50, 70.0)],
    "Mars": [(5100.0, 0.25, 30.0), (6500.0, 0.30, 42.0), (7800.0, 0.22, 50.0)],
    "Jupiter": [(4500.0, 0.22, 42.0), (6200.0, 0.45, 80.0), (8900.0, 0.55, 95.0)],
    "Saturn": [(4700.0, 0.20, 45.0), (6100.0, 0.42, 85.0), (8800.0, 0.62, 110.0)],
    "Uranus": [(5400.0, 0.30, 65.0), (6800.0, 0.55, 90.0), (9200.0, 0.85, 125.0)],
    "Neptune": [(5600.0, 0.35, 70.0), (7000.0, 0.60, 95.0), (9300.0, 0.92, 130.0)],
    "Titan": [(4400.0, 0.18, 35.0), (6000.0, 0.50, 75.0), (8800.0, 0.78, 115.0)],
}


@dataclass
class SpectrumFetchResult:
    """Container for fetched spectrum and provenance metadata."""

    target_name: str
    object_type: str
    observation_date: str
    wavelength: np.ndarray
    intensity: np.ndarray
    uncertainty: np.ndarray
    source: str
    metadata: Dict[str, Any]

    @property
    def flux(self) -> np.ndarray:
        """Backward-compatible alias."""

        return self.intensity


class PlanetarySpectrumFetcher:
    """Planetary fetcher with timed caching and provider fallback."""

    def __init__(
        self,
        cache_dir: Union[str, Path],
        hitran_wavelength_range: Tuple[float, float] = (3500.0, 9500.0),
        hitran_step_angstrom: float = 1.0,
    ):
        self.cache = SpectrumCache(cache_dir)
        self.hitran_wavelength_range = hitran_wavelength_range
        self.hitran_step_angstrom = hitran_step_angstrom

    @staticmethod
    def _require_pandas() -> None:
        if not _PANDAS_OK:
            raise ImportError("pandas is required for fetch_spectrum() output")

    @staticmethod
    def _normalize_date(observation_date: Optional[DateLike]) -> str:
        return SpectrumCache.normalize_date(observation_date)

    @staticmethod
    def _date_seed(day: str) -> int:
        return int(day.replace("-", ""))

    @staticmethod
    def _as_uncertainty(arr: np.ndarray, value: Optional[float] = None) -> np.ndarray:
        if value is None:
            return np.full_like(arr, np.nan, dtype=float)
        return np.full_like(arr, float(value), dtype=float)

    @staticmethod
    def _is_atmospheric_target(object_name: str) -> bool:
        return object_name in _ATMOSPHERIC_OBJECTS

    @staticmethod
    def _normalize_mode(mode: str) -> str:
        token = (mode or "reflectance").strip().lower()
        if token not in {"energy", "reflectance", "atmospheric"}:
            raise ValueError(
                f"Unsupported mode '{mode}'. Use one of: energy, reflectance, atmospheric"
            )
        return token

    def _apply_mode_transform(
        self,
        df,
        mode: str,
        object_name: str,
        observation_date: str,
    ):
        mode_token = self._normalize_mode(mode)

        if mode_token == "energy":
            out = compute_energy_spectrum(
                df=df,
                object_name=object_name,
                observation_date=observation_date,
            )
        elif mode_token in {"reflectance", "atmospheric"}:
            out = df.copy()
        else:
            out = df.copy()

        out["mode"] = mode_token
        out["energy_model"] = ENERGY_MODEL_VERSION
        return out

    def _source_sequence(self, source: str, object_name: str) -> List[str]:
        source = source.lower().strip()
        if source == "auto":
            if self._is_atmospheric_target(object_name):
                return ["hitran", "nasa_pds", "synthetic"]
            return ["nasa_pds", "hitran", "synthetic"]
        if source in {"nasa", "pds"}:
            return ["nasa_pds"]
        if source == "real_only":
            if self._is_atmospheric_target(object_name):
                return ["hitran", "nasa_pds"]
            return ["nasa_pds", "hitran"]
        return [source]

    @staticmethod
    def _http_get(url: str, headers: Optional[Dict[str, str]] = None, timeout: int = 45) -> Tuple[bytes, str]:
        req_headers = {"User-Agent": "NMR-Project-PlanetarySpectra/1.1"}
        if headers:
            req_headers.update(headers)
        req = Request(url=url, headers=req_headers)
        with urlopen(req, timeout=timeout) as resp:
            payload = resp.read()
            content_type = resp.headers.get("Content-Type", "")
        return payload, content_type

    @staticmethod
    def _extract_urls_from_json(node: Any) -> List[str]:
        urls: List[str] = []
        if isinstance(node, dict):
            for value in node.values():
                urls.extend(PlanetarySpectrumFetcher._extract_urls_from_json(value))
        elif isinstance(node, list):
            for item in node:
                urls.extend(PlanetarySpectrumFetcher._extract_urls_from_json(item))
        elif isinstance(node, str):
            s = node.strip()
            if s.lower().startswith("http://") or s.lower().startswith("https://"):
                urls.append(s)
        return urls

    @staticmethod
    def _rank_urls(urls: Iterable[str]) -> List[str]:
        seen = set()
        filtered: List[str] = []
        for url in urls:
            if url in seen:
                continue
            seen.add(url)
            path = urlparse(url).path.lower()
            if any(path.endswith(ext) for ext in _SUPPORTED_EXTENSIONS):
                filtered.append(url)

        ext_rank = {ext: idx for idx, ext in enumerate(_SUPPORTED_EXTENSIONS)}

        def score(u: str) -> int:
            path = urlparse(u).path.lower()
            for ext, idx in ext_rank.items():
                if path.endswith(ext):
                    return idx
            return len(ext_rank)

        return sorted(filtered, key=score)

    def _query_pds_urls(self, target_alias: str, hints: List[str]) -> List[str]:
        urls: List[str] = []
        queries = [
            f'target_name:"{target_alias}" AND (title:*spect* OR description:*spect* OR product_class:*spec*)',
            f'target_name:"{target_alias}" AND (instrument:*VIMS* OR instrument:*NIMS* OR instrument:*VIR* OR instrument:*CRISM*)',
        ]
        for hint in hints:
            queries.append(
                f'target_name:"{target_alias}" AND (title:*{hint}* OR investigation_name:*{hint}* OR instrument:*{hint}*)'
            )

        for q in queries:
            params = {"q": q, "wt": "json", "rows": 120}
            url = f"{_PDS_SEARCH_URL}?{urlencode(params)}"
            try:
                payload, _ = self._http_get(url)
                parsed = json.loads(payload.decode("utf-8", errors="replace"))
            except Exception:
                continue

            docs = parsed.get("response", {}).get("docs", [])
            if not docs and isinstance(parsed.get("docs"), list):
                docs = parsed.get("docs", [])
            for doc in docs:
                urls.extend(self._extract_urls_from_json(doc))
        return self._rank_urls(urls)

    def _resolve_nasa_pds_candidates(self, object_name: str) -> List[str]:
        aliases = _PDS_OBJECT_ALIASES.get(object_name, [object_name])
        hints = _PDS_MISSION_HINTS.get(object_name, [])
        urls: List[str] = []
        for alias in aliases:
            urls.extend(self._query_pds_urls(alias, hints=hints))
        return self._rank_urls(urls)

    def _table_to_arrays(self, table: Any) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """Map flexible table columns to wavelength/intensity/uncertainty."""

        self._require_pandas()
        import pandas as pd_local

        lowered = {str(c).lower(): c for c in table.columns}

        wl_candidates = [
            "wavelength",
            "wavelength_angstrom",
            "lambda",
            "wl",
            "wave",
            "wavenumber",
            "nu",
            "nu_cm-1",
        ]
        i_candidates = ["intensity", "flux", "radiance", "transmittance", "reflectance", "absorbance"]
        u_candidates = ["uncertainty", "sigma", "error", "err", "flux_error"]

        wl_col = next((lowered[c] for c in wl_candidates if c in lowered), None)
        it_col = next((lowered[c] for c in i_candidates if c in lowered), None)
        un_col = next((lowered[c] for c in u_candidates if c in lowered), None)
        if wl_col is None or it_col is None:
            return None

        wl = pd_local.to_numeric(table[wl_col], errors="coerce").to_numpy(dtype=float)
        intensity = pd_local.to_numeric(table[it_col], errors="coerce").to_numpy(dtype=float)
        if un_col is None:
            uncertainty = self._as_uncertainty(intensity)
        else:
            uncertainty = pd_local.to_numeric(table[un_col], errors="coerce").to_numpy(dtype=float)

        wl_name = str(wl_col).lower()
        if wl_name in {"wavenumber", "nu", "nu_cm-1"}:
            good = np.abs(wl) > 1e-12
            wl_out = np.full_like(wl, np.nan, dtype=float)
            wl_out[good] = 1e8 / wl[good]
            wl = wl_out

        valid = np.isfinite(wl) & np.isfinite(intensity)
        wl = wl[valid]
        intensity = intensity[valid]
        uncertainty = uncertainty[valid]
        if wl.size < 2:
            return None

        order = np.argsort(wl)
        return wl[order], intensity[order], uncertainty[order]

    def _parse_fits_payload(self, payload: bytes) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        if not _ASTROPY_FITS_OK:
            return None

        try:
            from astropy.io import fits as fits_local

            with fits_local.open(BytesIO(payload), memmap=False) as hdul:
                for hdu in hdul:
                    data = getattr(hdu, "data", None)
                    if data is None:
                        continue

                    if hasattr(data, "names") and data.names:
                        self._require_pandas()
                        import pandas as pd_local

                        cols: Dict[str, Any] = {}
                        for name in data.names:
                            try:
                                cols[str(name)] = np.asarray(data[name])
                            except Exception:
                                continue
                        if cols:
                            table = pd_local.DataFrame(cols)
                            parsed = self._table_to_arrays(table)
                            if parsed is not None:
                                return parsed

                    arr = np.asarray(data)
                    if arr.size == 0:
                        continue
                    arr = np.squeeze(arr)
                    if arr.ndim == 1:
                        wl = np.arange(arr.size, dtype=float)
                        intensity = arr.astype(float)
                        uncertainty = np.full_like(intensity, np.nan, dtype=float)
                        return wl, intensity, uncertainty
                    if arr.ndim == 2:
                        if arr.shape[0] >= 2:
                            wl = np.asarray(arr[0], dtype=float)
                            intensity = np.asarray(arr[1], dtype=float)
                            uncertainty = (
                                np.asarray(arr[2], dtype=float)
                                if arr.shape[0] >= 3
                                else np.full_like(intensity, np.nan, dtype=float)
                            )
                        elif arr.shape[1] >= 2:
                            wl = np.asarray(arr[:, 0], dtype=float)
                            intensity = np.asarray(arr[:, 1], dtype=float)
                            uncertainty = (
                                np.asarray(arr[:, 2], dtype=float)
                                if arr.shape[1] >= 3
                                else np.full_like(intensity, np.nan, dtype=float)
                            )
                        else:
                            continue

                        valid = np.isfinite(wl) & np.isfinite(intensity)
                        wl = wl[valid]
                        intensity = intensity[valid]
                        uncertainty = uncertainty[valid]
                        if wl.size >= 2:
                            order = np.argsort(wl)
                            return wl[order], intensity[order], uncertainty[order]
        except Exception:
            return None
        return None

    def _parse_text_payload(self, payload: bytes) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        self._require_pandas()
        import pandas as pd_local

        text = payload.decode("utf-8", errors="replace")
        parsers = [
            {"sep": ",", "comment": "#"},
            {"sep": "\\s+", "engine": "python", "comment": "#"},
            {"sep": None, "engine": "python", "comment": "#"},
        ]
        for kwargs in parsers:
            try:
                table = pd_local.read_csv(StringIO(text), **kwargs)
            except Exception:
                continue
            if table is None or table.empty:
                continue
            parsed = self._table_to_arrays(table)
            if parsed is not None:
                return parsed
        return None

    def _download_and_parse_product(self, url: str) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        try:
            payload, content_type = self._http_get(url)
        except Exception:
            return None

        path = urlparse(url).path.lower()
        if path.endswith((".fits", ".fit", ".fts")) or "fits" in content_type.lower():
            parsed = self._parse_fits_payload(payload)
            if parsed is not None:
                return parsed

        return self._parse_text_payload(payload)

    def _fetch_from_nasa_pds(self, target_name: str, observation_date: str) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """Fetch spectrum from public NASA PDS products.

        Supports FITS, ASCII tables, and CSV-like products.
        """

        _ = observation_date
        candidates = self._resolve_nasa_pds_candidates(target_name)
        for url in candidates:
            parsed = self._download_and_parse_product(url)
            if parsed is not None:
                return parsed
        return None

    def _load_local_hitran_lines(self, target_name: str) -> List[Tuple[float, float, float]]:
        """Load local HITRAN-like lines from optional CSV or built-in defaults."""

        file_name = f"hitran_{target_name.lower().replace(' ', '_')}.csv"
        local_path = Path(__file__).parent / "data" / file_name
        if local_path.exists():
            self._require_pandas()
            import pandas as pd_local

            try:
                table = pd_local.read_csv(local_path)
                cols = {c.lower(): c for c in table.columns}
                c_col = cols.get("center_angstrom", cols.get("center"))
                s_col = cols.get("strength")
                w_col = cols.get("width_angstrom", cols.get("width"))
                if c_col and s_col and w_col:
                    out: List[Tuple[float, float, float]] = []
                    for _, row in table.iterrows():
                        out.append((float(row[c_col]), float(row[s_col]), float(row[w_col])))
                    if out:
                        return out
            except Exception:
                pass
        return _HITRAN_LOCAL_LINES.get(target_name, [])

    def _synthesize_absorption_from_lines(
        self,
        lines: List[Tuple[float, float, float]],
        wl_min: float,
        wl_max: float,
        step_angstrom: float,
    ) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert line list into an absorption spectrum curve."""

        wl = np.arange(wl_min, wl_max + step_angstrom, step_angstrom, dtype=float)
        tau = np.zeros_like(wl)
        for center, strength, width in lines:
            width = max(float(width), 1e-6)
            tau += float(strength) * np.exp(-0.5 * ((wl - float(center)) / width) ** 2)

        intensity = np.exp(-tau)
        uncertainty = np.full_like(intensity, np.nan, dtype=float)
        return wl, intensity, uncertainty

    def _fetch_from_hitran(self, target_name: str, observation_date: str) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """Build absorption spectrum using HITRAN-like local line datasets."""

        _ = observation_date
        lines = self._load_local_hitran_lines(target_name)
        if not lines:
            return None

        wl_min, wl_max = self.hitran_wavelength_range
        return self._synthesize_absorption_from_lines(
            lines=lines,
            wl_min=wl_min,
            wl_max=wl_max,
            step_angstrom=self.hitran_step_angstrom,
        )

    def _fetch_from_jwst(self, target_name: str, observation_date: str) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """Placeholder for JWST retrieval via MAST.

        Future wiring:
        - Use MAST API with instrument filters (NIRSpec/NIRCam).
        - Parse calibrated products into wavelength/intensity/uncertainty.
        """

        _ = (target_name, observation_date)
        return None

    def _fetch_from_hst(self, target_name: str, observation_date: str) -> Optional[Tuple[np.ndarray, np.ndarray, np.ndarray]]:
        """Placeholder for HST retrieval via MAST.

        Future wiring:
        - Query STIS/COS products for target and date constraints.
        - Parse calibrated spectral products into pipeline arrays.
        """

        _ = (target_name, observation_date)
        return None

    def _ephemeris_metadata(self, target_name: str, observation_date: str) -> Dict[str, Any]:
        """Optionally enrich metadata with JPL Horizons geometry."""

        if not _HORIZONS_OK:
            return {}

        try:
            from astroquery.jplhorizons import Horizons as HorizonsLocal
            from astropy.time import Time as TimeLocal

            epoch_jd = TimeLocal(f"{observation_date} 00:00:00", format="iso", scale="utc").jd
        except Exception:
            return {}

        for id_type in ("majorbody", "smallbody"):
            try:
                obj = HorizonsLocal(id=target_name, id_type=id_type, location="500@10", epochs=epoch_jd)
                eph = getattr(obj, "ephemerides")()
                if len(eph) == 0:
                    continue
                return {
                    "phase_angle_deg": float(eph["alpha"][0]),
                    "heliocentric_distance_au": float(eph["r"][0]),
                    "observer_distance_au": float(eph["delta"][0]),
                }
            except Exception:
                continue
        return {}

    def _synthetic_spectrum(self, body: CelestialBody, day: str) -> Tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Generate deterministic synthetic fallback spectrum."""

        seed = self._date_seed(day) + abs(hash(body.name)) % 100_000
        rng = np.random.default_rng(seed)

        wl = np.linspace(3500.0, 9500.0, 2500)
        base = np.exp(-((wl - 6200.0) ** 2) / (2.0 * 1200.0**2))
        phase = (seed % 365) / 365.0
        shift = 30.0 * np.sin(2.0 * np.pi * phase)

        absorption = np.ones_like(wl)
        for center in [4300 + shift, 5170 - 0.6 * shift, 7600 + 0.4 * shift]:
            absorption -= 0.08 * np.exp(-((wl - center) ** 2) / (2.0 * 18.0**2))

        noise = rng.normal(0, 0.01, size=wl.size)
        intensity = np.clip(base * absorption + noise, 0, None)
        uncertainty = np.full_like(intensity, 0.01, dtype=float)
        return wl, intensity, uncertainty

    def _to_dataframe(
        self,
        body: CelestialBody,
        observation_date: str,
        source: str,
        wavelength: np.ndarray,
        intensity: np.ndarray,
        uncertainty: np.ndarray,
        query_timestamp: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> Any:
        self._require_pandas()
        import pandas as pd_local

        ts = query_timestamp or datetime.utcnow().isoformat()
        df = pd_local.DataFrame(
            {
                "wavelength": np.asarray(wavelength, dtype=float),
                "intensity": np.asarray(intensity, dtype=float),
                "uncertainty": np.asarray(uncertainty, dtype=float),
            }
        )
        df["object_name"] = body.name
        df["object_type"] = body.body_type
        df["observation_date"] = observation_date
        df["source"] = source
        df["query_timestamp"] = ts
        if metadata:
            for key, value in metadata.items():
                if isinstance(value, (str, int, float, bool)) or value is None:
                    df[key] = value
        return df

    def fetch_spectrum(
        self,
        object_name: str,
        observation_date: Optional[DateLike] = None,
        mode: str = "reflectance",
        source: str = "auto",
        local_csv_path: Optional[Union[str, Path]] = None,
        target_resolution_angstrom: float = 1.0,
        normalize_intensity: bool = True,
        include_ephemeris: bool = False,
    ) -> Any:
        """Fetch a spectrum and return ML-ready DataFrame.

        Returned columns include:
        wavelength, intensity, uncertainty,
        object_name, object_type, observation_date, source, query_timestamp,
        mode, energy_model
        """

        self._require_pandas()
        body = get_body_by_name(object_name)
        if body is None:
            raise KeyError(f"Unknown target '{object_name}'. Add it to planetary_catalog first.")

        day = self._normalize_date(observation_date)
        query_ts = datetime.utcnow().isoformat()

        # 1) Cache hit path (processed first)
        for tier in ("processed", "raw"):
            cached = self.cache.load_spectrum(body.name, day, source="cache", tier=tier)
            if cached is None:
                continue
            wl_c, it_c, un_c = cached
            if tier == "raw":
                wl_c, it_c, un_c = self.cache.normalize_spectrum(
                    wavelength=wl_c,
                    intensity=it_c,
                    uncertainty=un_c,
                    target_resolution_angstrom=target_resolution_angstrom,
                    normalize_intensity=normalize_intensity,
                )
                self.cache.save_spectrum(
                    target_name=body.name,
                    wavelength=wl_c,
                    intensity=it_c,
                    uncertainty=un_c,
                    observation_date=day,
                    source="cache",
                    tier="processed",
                    metadata={"generated_from": "raw_cache"},
                )
            ephem = self._ephemeris_metadata(body.name, day) if include_ephemeris else {}
            register_observation(body.name, source="csv_cache", observation_date=day)
            df_cached = self._to_dataframe(
                body=body,
                observation_date=day,
                source="csv_cache",
                wavelength=wl_c,
                intensity=it_c,
                uncertainty=un_c,
                query_timestamp=query_ts,
                metadata=ephem,
            )
            return self._apply_mode_transform(
                df=df_cached,
                mode=mode,
                object_name=body.name,
                observation_date=day,
            )

        # 2) Optional local CSV
        if source.lower().strip() == "local_csv":
            if local_csv_path is None:
                raise RuntimeError("local_csv source requested but local_csv_path was not provided")
            local = np.genfromtxt(local_csv_path, delimiter=",", skip_header=1)
            if local.ndim < 2 or local.shape[1] < 2:
                raise RuntimeError(f"Invalid local CSV format: {local_csv_path}")
            wl_raw = np.asarray(local[:, 0], dtype=float)
            it_raw = np.asarray(local[:, 1], dtype=float)
            un_raw = (
                np.asarray(local[:, 2], dtype=float)
                if local.shape[1] >= 3
                else self._as_uncertainty(it_raw)
            )
            source_used = "user_upload"
        else:
            wl_raw: Optional[np.ndarray] = None
            it_raw: Optional[np.ndarray] = None
            un_raw: Optional[np.ndarray] = None
            source_used: Optional[str] = None
            real_attempted = False

            for candidate in self._source_sequence(source, body.name):
                if candidate in {"nasa_pds", "hitran"}:
                    real_attempted = True

                if candidate == "nasa_pds":
                    remote = self._fetch_from_nasa_pds(body.name, day)
                elif candidate == "hitran":
                    remote = self._fetch_from_hitran(body.name, day)
                elif candidate == "jwst":
                    remote = self._fetch_from_jwst(body.name, day)
                elif candidate == "hst":
                    remote = self._fetch_from_hst(body.name, day)
                elif candidate == "synthetic":
                    remote = self._synthetic_spectrum(body, day)
                else:
                    remote = None

                if remote is None:
                    continue

                wl_raw, it_raw, un_raw = remote
                if candidate == "synthetic" and real_attempted:
                    source_used = "synthetic_fallback"
                else:
                    source_used = candidate
                break

            if wl_raw is None or it_raw is None or un_raw is None or source_used is None:
                raise RuntimeError(f"No usable spectrum found for {body.name} on {day}")

        ephem_meta = self._ephemeris_metadata(body.name, day) if include_ephemeris else {}

        # Cache raw
        self.cache.save_spectrum(
            target_name=body.name,
            wavelength=wl_raw,
            intensity=it_raw,
            uncertainty=un_raw,
            observation_date=day,
            source="cache",
            tier="raw",
            metadata={
                "upstream_source": source_used,
                "observation_date": day,
                **ephem_meta,
            },
        )

        # Cache processed
        wl_proc, it_proc, un_proc = self.cache.normalize_spectrum(
            wavelength=wl_raw,
            intensity=it_raw,
            uncertainty=un_raw,
            target_resolution_angstrom=target_resolution_angstrom,
            normalize_intensity=normalize_intensity,
        )
        self.cache.save_spectrum(
            target_name=body.name,
            wavelength=wl_proc,
            intensity=it_proc,
            uncertainty=un_proc,
            observation_date=day,
            source="cache",
            tier="processed",
            metadata={
                "upstream_source": source_used,
                "normalized": normalize_intensity,
                "target_resolution_angstrom": target_resolution_angstrom,
                **ephem_meta,
            },
        )

        register_observation(body.name, source=source_used, observation_date=day)
        df_out = self._to_dataframe(
            body=body,
            observation_date=day,
            source=source_used,
            wavelength=wl_proc,
            intensity=it_proc,
            uncertainty=un_proc,
            query_timestamp=query_ts,
            metadata=ephem_meta,
        )
        return self._apply_mode_transform(
            df=df_out,
            mode=mode,
            object_name=body.name,
            observation_date=day,
        )

    def fetch(
        self,
        target_name: str,
        observation_date: Optional[DateLike] = None,
        mode: str = "reflectance",
        source_priority: Optional[List[str]] = None,
        local_csv_path: Optional[Union[str, Path]] = None,
        auto_cache: bool = True,
    ) -> SpectrumFetchResult:
        """Backward-compatible fetch API returning arrays and metadata."""

        sequence = source_priority or ["auto"]
        last_error: Optional[Exception] = None
        df = None
        for candidate in sequence:
            try:
                df = self.fetch_spectrum(
                    object_name=target_name,
                    observation_date=observation_date,
                    mode=mode,
                    source=candidate,
                    local_csv_path=local_csv_path,
                )
                break
            except Exception as exc:
                last_error = exc
                continue

        if df is None:
            raise RuntimeError(f"No fetch source succeeded for {target_name}: {last_error}")

        if not auto_cache:
            warnings.warn("auto_cache=False is deprecated in compatibility fetch().", stacklevel=2)

        body = get_body_by_name(target_name)
        if body is None:
            raise KeyError(f"Unknown target '{target_name}'.")

        metadata: Dict[str, Any] = {"query_timestamp": str(df["query_timestamp"].iloc[0])}
        for col in ("phase_angle_deg", "heliocentric_distance_au", "observer_distance_au"):
            if col in df.columns:
                val = df[col].iloc[0]
                metadata[col] = float(val) if np.isfinite(val) else np.nan

        return SpectrumFetchResult(
            target_name=body.name,
            object_type=body.body_type,
            observation_date=str(df["observation_date"].iloc[0]),
            wavelength=df["wavelength"].to_numpy(dtype=float),
            intensity=df["intensity"].to_numpy(dtype=float),
            uncertainty=df["uncertainty"].to_numpy(dtype=float),
            source=str(df["source"].iloc[0]),
            metadata=metadata,
        )

    def fetch_date_range(
        self,
        target_name: str,
        start_date: DateLike,
        end_date: DateLike,
        mode: str = "reflectance",
        step_days: int = 1,
        source_priority: Optional[List[str]] = None,
        local_csv_path: Optional[Union[str, Path]] = None,
        source: str = "auto",
    ) -> List[SpectrumFetchResult]:
        """Fetch spectra across a date range inclusive."""

        start = datetime.fromisoformat(self._normalize_date(start_date)).date()
        end = datetime.fromisoformat(self._normalize_date(end_date)).date()
        if end < start:
            raise ValueError("end_date must be >= start_date")

        out: List[SpectrumFetchResult] = []
        current = start
        while current <= end:
            selected = source_priority[0] if source_priority else source
            out.append(
                self.fetch(
                    target_name=target_name,
                    observation_date=current,
                    mode=mode,
                    source_priority=[selected],
                    local_csv_path=local_csv_path,
                    auto_cache=True,
                )
            )
            current += timedelta(days=step_days)
        return out


def fetch_spectrum(
    object_name: str,
    observation_date: Optional[DateLike] = None,
    mode: str = "reflectance",
    source: str = "auto",
    cache_dir: Union[str, Path] = Path(__file__).parent / "spectral_cache",
) -> Any:
    """Module-level convenience wrapper for ML-ready spectrum fetching."""

    fetcher = PlanetarySpectrumFetcher(cache_dir=cache_dir)
    return fetcher.fetch_spectrum(
        object_name=object_name,
        observation_date=observation_date,
        mode=mode,
        source=source,
    )
