"""
zodiac_targets.py

Curated catalog of all 12 zodiac constellations and their principal stars.

Each record contains:
  - name       : common star name
  - bayer      : Bayer designation (e.g. 'α Tau')
  - ra_deg     : right ascension (degrees, J2000)
  - dec_deg    : declination (degrees, J2000)
  - spectral_type : Harvard spectral classification (e.g. 'K5III')
  - vmag       : apparent visual magnitude
  - dist_ly    : distance in light-years (approximate)
  - notes      : brief physical note

Physical references
-------------------
  - Yale Bright Star Catalogue (1991)
  - SIMBAD Astronomical Database
  - Hipparcos / Gaia parallax data
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, List, Optional

# ---------------------------------------------------------------------------
# Data structure
# ---------------------------------------------------------------------------

@dataclass
class StarRecord:
    """Minimal physical description of one star."""
    name: str
    bayer: str
    constellation: str
    ra_deg: float          # degrees, J2000
    dec_deg: float         # degrees, J2000
    spectral_type: str
    vmag: float            # apparent visual magnitude
    dist_ly: float         # light-years (approx)
    notes: str = ""

    # Populated lazily after spectrum analysis
    peak_frequencies: List[float] = field(default_factory=list)
    coherence_score: Optional[float] = None
    energy_vector: Optional[Dict[str, float]] = None


# ---------------------------------------------------------------------------
# Full 12-constellation zodiac catalog
# ---------------------------------------------------------------------------

ZODIAC_STARS: Dict[str, List[StarRecord]] = {

    # ------------------------------------------------------------------
    "Aries": [
        StarRecord("Hamal",     "α Ari", "Aries",  31.793, 23.462, "K2III",   2.00,  66,
                   "Brightest in Aries; K-type orange giant"),
        StarRecord("Sheratan",  "β Ari", "Aries",  28.660, 20.808, "A5V",     2.64,  59,
                   "Am-type metallic-line star"),
        StarRecord("Mesarthim", "γ Ari", "Aries",  28.382, 19.294, "A1pSi",   3.88, 164,
                   "First resolved binary star (1664)"),
        StarRecord("Botein",    "δ Ari", "Aries",  44.107, 19.726, "K2III",   4.35, 168,
                   "K-type giant"),
    ],

    # ------------------------------------------------------------------
    "Taurus": [
        StarRecord("Aldebaran", "α Tau", "Taurus",  68.980,  16.510, "K5III",   0.87,  65,
                   "Red giant, eye of the bull; strong Ca II"),
        StarRecord("Elnath",    "β Tau", "Taurus",  81.573,  28.608, "B7III",   1.65, 131,
                   "Blue-white giant, shared with Auriga"),
        StarRecord("Alcyone",   "η Tau", "Taurus",  56.871,  24.105, "B7IIIe",  2.87, 440,
                   "Brightest Pleiad, Be shell star"),
        StarRecord("Ain",       "ε Tau", "Taurus",  67.154,  19.180, "K0III",   3.53, 147,
                   "Hyades cluster giant with confirmed exoplanet"),
        StarRecord("Tianguan",  "ζ Tau", "Taurus",  84.411,  21.142, "B4IIIpe", 3.00, 440,
                   "B-type shell variable"),
    ],

    # ------------------------------------------------------------------
    "Gemini": [
        StarRecord("Pollux",  "β Gem", "Gemini", 116.329,  28.026, "K0IIIb",  1.14,  34,
                   "Brightest Gemini star; K-type giant with exoplanet"),
        StarRecord("Castor",  "α Gem", "Gemini", 113.650,  31.889, "A1V+A2V", 1.58,  51,
                   "Sextuple star system; strong Balmer lines"),
        StarRecord("Alhena",  "γ Gem", "Gemini", 99.428,  16.400, "A0IV",    1.93, 109,
                   "A-type subgiant, bright standard"),
        StarRecord("Mebsuda", "ε Gem", "Gemini", 100.983, 25.131, "G8Ib",    3.06, 900,
                   "G-type supergiant"),
        StarRecord("Mekbuda", "ζ Gem", "Gemini", 106.027, 20.570, "G4Ibv",   3.79, 1200,
                   "Classical Cepheid variable δ Cep type"),
    ],

    # ------------------------------------------------------------------
    "Cancer": [
        StarRecord("Altarf",              "β Cnc", "Cancer", 124.129, 9.186,  "K4III",  3.52, 290,
                   "Brightest Cancer star; K-type giant"),
        StarRecord("Asellus Australis",   "δ Cnc", "Cancer", 130.821, 18.154, "K0IIIb", 3.94, 136,
                   "Southern Donkey; Beehive cluster direction"),
        StarRecord("Asellus Borealis",    "γ Cnc", "Cancer", 130.022, 21.469, "A1IV",   4.66, 181,
                   "Northern Donkey"),
        StarRecord("Acubens",             "α Cnc", "Cancer", 134.622, 11.858, "Am",     4.25, 174,
                   "Metallic-line A-type binary"),
    ],

    # ------------------------------------------------------------------
    "Leo": [
        StarRecord("Regulus",   "α Leo", "Leo",  152.093, 11.967, "B7V",     1.35,  79,
                   "Heart of the lion; rapid rotator, nearly spherical"),
        StarRecord("Denebola",  "β Leo", "Leo",  177.265, 14.572, "A3V",     2.14,  36,
                   "Debris disk star; IR excess"),
        StarRecord("Algieba",   "γ Leo", "Leo",  154.993, 19.841, "K0IIIb+G7IIIb", 2.08, 126,
                   "Gold-orange double, both K/G giants"),
        StarRecord("Zosma",     "δ Leo", "Leo",  168.527, 20.524, "A4V",     2.56,  58,
                   "A-type main sequence"),
        StarRecord("Chertan",   "θ Leo", "Leo",  168.560, 15.430, "A2V",     3.34, 165,
                   "Rapid rotator"),
    ],

    # ------------------------------------------------------------------
    "Virgo": [
        StarRecord("Spica",     "α Vir", "Virgo", 201.298, -11.161, "B1III+B2V", 0.97, 250,
                   "Brightest Virgo star; spectroscopic binary, pulsating"),
        StarRecord("Porrima",   "γ Vir", "Virgo", 190.415,  -1.449, "F0V+F0V",  2.76,  38,
                   "Close visual binary, both F-type main sequence"),
        StarRecord("Minelauva", "δ Vir", "Virgo", 193.901,   3.397, "M3III",    3.38, 198,
                   "Red giant semiregular variable, strong TiO"),
        StarRecord("Vindemiatrix","ε Vir","Virgo",195.544,  10.959, "G9III",    2.83,  98,
                   "G-type giant, strong Ca II H&K"),
    ],

    # ------------------------------------------------------------------
    "Libra": [
        StarRecord("Zubeneschamali", "β Lib", "Libra", 229.252,  -9.383, "B8V",    2.61, 185,
                   "Brightest Libra; B-type mainstream, visual hint of green"),
        StarRecord("Zubenelgenubi",  "α Lib", "Libra", 222.719, -16.042, "A3IV",   2.75,  77,
                   "Wide visual double"),
        StarRecord("Brachium",       "σ Lib", "Libra", 231.957, -25.282, "M3-4III",3.29, 293,
                   "Red giant semiregular"),
        StarRecord("Girtab",         "γ Lib", "Libra", 225.486, -14.790, "K0III",  3.91, 152,
                   "K-type giant"),
    ],

    # ------------------------------------------------------------------
    "Scorpius": [
        StarRecord("Antares",   "α Sco", "Scorpius", 247.352, -26.432, "M1.5Iab", 1.09,  550,
                   "Red supergiant, semi-regular pulsation, companion B3V"),
        StarRecord("Shaula",    "λ Sco", "Scorpius", 263.402, -37.104, "B1.5IV",  1.63,  570,
                   "Beta Cephei pulsator + spectroscopic binary"),
        StarRecord("Sargas",    "θ Sco", "Scorpius", 252.968, -42.998, "F0II",    1.87,  272,
                   "F-type bright giant"),
        StarRecord("Dschubba",  "δ Sco", "Scorpius", 240.083, -22.622, "B0.3IV",  2.32,  401,
                   "Be-star outburst 2000; rapid rotation"),
        StarRecord("Graffias",  "β Sco", "Scorpius", 241.359, -19.805, "B1V+B2V", 2.56,  530,
                   "Close binary, B-type"),
    ],

    # ------------------------------------------------------------------
    "Sagittarius": [
        StarRecord("Kaus Australis", "ε Sgr", "Sagittarius", 276.043, -34.385, "B9.5III", 1.79, 143,
                   "Brightest Sgr; blue-white giant"),
        StarRecord("Nunki",          "σ Sgr", "Sagittarius", 283.816, -26.297, "B2.5V",   2.05, 228,
                   "Second brightest; rapid rotator"),
        StarRecord("Ascella",        "ζ Sgr", "Sagittarius", 285.653, -29.880, "A2III",   2.60,  89,
                   "Visual binary: A2 + F-type"),
        StarRecord("Kaus Media",     "δ Sgr", "Sagittarius", 275.249, -29.828, "K3III",   2.72, 306,
                   "K-type giant"),
        StarRecord("Kaus Borealis",  "λ Sgr", "Sagittarius", 276.993, -25.422, "K2IIIb",  2.81,  77,
                   "Northern bow of Sagittarius"),
    ],

    # ------------------------------------------------------------------
    "Capricornus": [
        StarRecord("Deneb Algedi", "δ Cap", "Capricornus", 326.760, -16.127, "A5m",    2.85,  39,
                   "Brightest Capricornus; eclipsing binary, Algol type"),
        StarRecord("Dabih",        "β Cap", "Capricornus", 305.253, -14.781, "F8V+A0V",3.05, 328,
                   "Wide visual pair, different distances"),
        StarRecord("Nashira",      "γ Cap", "Capricornus", 321.668, -16.662, "F0III",  3.69, 139,
                   "Slowly pulsating A/F star"),
        StarRecord("Algedi",       "α Cap", "Capricornus", 304.514, -12.508, "G9III",  3.57,  690,
                   "Visual double (unrelated), G-type giant"),
    ],

    # ------------------------------------------------------------------
    "Aquarius": [
        StarRecord("Sadalsuud",  "β Aqr", "Aquarius", 322.889,  -5.571, "G0Ib",  2.91, 607,
                   "Brightest Aquarius; G-type supergiant"),
        StarRecord("Sadalmelik", "α Aqr", "Aquarius", 331.446,  -0.320, "G2Ib",  2.96, 520,
                   "G-type supergiant, strong G-band"),
        StarRecord("Skat",       "δ Aqr", "Aquarius", 340.529, -15.821, "A3V",   3.27, 160,
                   "A-type main sequence"),
        StarRecord("Sadachbia",  "γ Aqr", "Aquarius", 332.166,  -1.387, "A0V",   3.84, 163,
                   "A-type, metal-weak"),
    ],

    # ------------------------------------------------------------------
    "Pisces": [
        StarRecord("Eta Piscium",    "η Psc", "Pisces", 22.870,  15.346, "G8III", 3.62, 294,
                   "Brightest Pisces; G-type giant"),
        StarRecord("Kullat Nunu",    "η Psc", "Pisces", 22.870,  15.346, "G7III", 3.62, 294,
                   "Same star, traditional name"),
        StarRecord("Fumalsamakah",   "β Psc", "Pisces",  5.622,   3.820, "B6Ve",  4.53, 408,
                   "B-type emission star"),
        StarRecord("Revati",         "ζ Psc", "Pisces",  9.833,   7.890, "A7V",   5.24,  148,
                   "Visual binary"),
        StarRecord("Alrescha",       "α Psc", "Pisces", 30.512,   2.764, "A0p",   3.82, 139,
                   "Chemically peculiar A star"),
    ],
}


# ---------------------------------------------------------------------------
# Convenience helpers
# ---------------------------------------------------------------------------

def get_all_stars() -> List[StarRecord]:
    """Return flat list of all stars across all constellations."""
    return [star for lst in ZODIAC_STARS.values() for star in lst]


def get_stars_by_constellation(constellation: str) -> List[StarRecord]:
    """Return all stars in a named constellation (case-insensitive)."""
    for key, stars in ZODIAC_STARS.items():
        if key.lower() == constellation.lower():
            return stars
    raise KeyError(f"Constellation '{constellation}' not found. "
                   f"Available: {list(ZODIAC_STARS.keys())}")


def get_star_by_name(name: str) -> StarRecord:
    """Look up a star by common name (case-insensitive)."""
    for star in get_all_stars():
        if star.name.lower() == name.lower():
            return star
    raise KeyError(f"Star '{name}' not found in catalog.")


def summary_table() -> str:
    """Print-friendly summary of the full catalog."""
    lines = [
        f"{'ZODIAC STAR CATALOG':^80}",
        f"{'=' * 80}",
        f"{'Constellation':<14} {'Name':<20} {'Bayer':<8} {'Type':<12} {'Vmag':>5} {'Dist(ly)':>9}",
        f"{'-' * 80}",
    ]
    for const, stars in ZODIAC_STARS.items():
        for i, s in enumerate(stars):
            const_col = const if i == 0 else ""
            lines.append(
                f"{const_col:<14} {s.name:<20} {s.bayer:<8} {s.spectral_type:<12} "
                f"{s.vmag:>5.2f} {s.dist_ly:>9.0f}"
            )
        lines.append(f"{'-' * 80}")
    lines.append(f"\nTotal stars: {len(get_all_stars())}  |  Constellations: {len(ZODIAC_STARS)}")
    return "\n".join(lines)


if __name__ == "__main__":
    print(summary_table())
