"""
zodiac_targets.py

Curated catalog of all 12 zodiac constellations plus 29 ecliptic-adjacent /
traditional belt constellations (41 constellations total).

Each record contains:
  - name       : common star name
  - bayer      : Bayer designation (e.g. 'α Tau')
  - ra_deg     : right ascension (degrees, J2000)
  - dec_deg    : declination (degrees, J2000)
  - spectral_type : Harvard spectral classification (e.g. 'K5III')
  - vmag       : apparent visual magnitude
  - dist_ly    : distance in light-years (approximate)
  - notes      : brief physical note

Constellations
--------------
  Zodiac (12) : Aries, Taurus, Gemini, Cancer, Leo, Virgo,
                Libra, Scorpius, Sagittarius, Capricornus, Aquarius, Pisces
  Adjacent (29): Cetus, Andromeda, Perseus, Cassiopeia, Triangulum, Pegasus,
                 Eridanus, Orion, Auriga, Canis Major, Canis Minor,
                 Hydra, Crater, Corvus, Ursa Major, Ursa Minor,
                 Canes Venatici, Boötes, Corona Borealis, Serpens,
                 Ophiuchus, Centaurus, Crux, Piscis Austrinus,
                 Draco, Lyra, Cygnus, Aquila, Delphinus

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
        StarRecord("Altarf",            "β Cnc", "Cancer", 124.129,  9.186,  "K4III",  3.52, 290,
                   "Brightest Cancer star; K-type giant"),
        StarRecord("Asellus Australis", "δ Cnc", "Cancer", 130.821, 18.154,  "K0IIIb", 3.94, 136,
                   "Southern Donkey; Beehive cluster direction"),
        StarRecord("Asellus Borealis",  "γ Cnc", "Cancer", 130.022, 21.469,  "A1IV",   4.66, 181,
                   "Northern Donkey"),
        StarRecord("Acubens",           "α Cnc", "Cancer", 134.622, 11.858,  "Am",     4.25, 174,
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
        StarRecord("Kerb",           "τ Peg", "Pisces", 345.943,  23.741, "B9.5V", 4.58, 172,
                   "Faint ecliptic marker star near Pisces/Pegasus border"),
    ],

    # ======================================================================
    # ECLIPTIC-ADJACENT & TRADITIONAL BELT CONSTELLATIONS
    # ======================================================================

    # ------------------------------------------------------------------
    "Cetus": [
        StarRecord("Deneb Kaitos", "β Cet", "Cetus",  10.897, -17.987, "K0III",     2.02,  96,
                   "Brightest Cetus; K-type giant, traditional whale tail"),
        StarRecord("Menkar",       "α Cet", "Cetus",  45.570,   4.090, "M1.5IIIa",  2.53, 249,
                   "Red giant, jaw of the whale"),
        StarRecord("Mira",         "ο Cet", "Cetus",  34.836,  -2.978, "M5-M9IIIe", 6.47, 418,
                   "Prototype long-period Mira variable; ~332 d period"),
        StarRecord("Kaffaljidhma", "γ Cet", "Cetus",  40.825,   3.236, "A3V",        3.47, 82,
                   "A-type main sequence, visual binary"),
        StarRecord("Diphda",       "β Cet", "Cetus",  10.897, -17.987, "K0III",     2.02,  96,
                   "Alias for Deneb Kaitos (β Cet)"),
    ],

    # ------------------------------------------------------------------
    "Andromeda": [
        StarRecord("Alpheratz",  "α And", "Andromeda",   2.097,  29.091, "B8IVpHg",   2.06,  97,
                   "Shared corner with Pegasus Square; hot mercury-manganese star"),
        StarRecord("Mirach",     "β And", "Andromeda",  17.433,  35.621, "M0IIIa",    2.06, 197,
                   "Red giant, guide star for Andromeda Galaxy"),
        StarRecord("Almach",     "γ And", "Andromeda",  30.975,  42.330, "K3IIb+A2V", 2.26, 355,
                   "Striking gold-blue double star"),
        StarRecord("Adhil",      "ξ And", "Andromeda",  17.096,  45.529, "K0III",     4.87, 196,
                   "K-type giant"),
    ],

    # ------------------------------------------------------------------
    "Perseus": [
        StarRecord("Mirfak",   "α Per", "Perseus",  51.081,  49.861, "F5Ib",    1.79,  590,
                   "Brightest Perseus; F-type supergiant, Alpha Per cluster"),
        StarRecord("Algol",    "β Per", "Perseus",  47.042,  40.957, "B8V+K2IV",2.12,   93,
                   "Eclipsing binary prototype, 2.87 d period"),
        StarRecord("Miram",    "η Per", "Perseus",  43.560,  55.896, "K3Ib",    3.77, 1331,
                   "K-type supergiant"),
        StarRecord("Menkib",   "ξ Per", "Perseus",  58.533,  35.791, "O7.5III", 4.04, 1200,
                   "Bright O-type giant"),
        StarRecord("Atik",     "ο Per", "Perseus",  58.535,  32.288, "B1III",   3.83,  960,
                   "B-type giant, near ecliptic"),
    ],

    # ------------------------------------------------------------------
    "Cassiopeia": [
        StarRecord("Schedar",   "α Cas", "Cassiopeia",  10.127,  56.537, "K0IIa",  2.25, 228,
                   "Brightest Cassiopeia; K-type bright giant"),
        StarRecord("Caph",      "β Cas", "Cassiopeia",   2.295,  59.150, "F2III",  2.27,  54,
                   "F-type giant/subgiant, Delta Scuti pulsator"),
        StarRecord("Gamma Cas", "γ Cas", "Cassiopeia",  14.178,  60.717, "B0IVe",  2.47, 550,
                   "Luminous Be variable (1.6–3.0); X-ray emitter"),
        StarRecord("Ruchbah",   "δ Cas", "Cassiopeia",  21.454,  60.235, "A5III",  2.68,  99,
                   "A-type giant, eclipsing binary"),
        StarRecord("Segin",     "ε Cas", "Cassiopeia",  28.599,  63.670, "B3III",  3.38, 442,
                   "B-type giant"),
    ],

    # ------------------------------------------------------------------
    "Triangulum": [
        StarRecord("Mothallah",  "α Tri", "Triangulum",  28.271,  29.579, "F6IV",  3.42,  65,
                   "Brightest Triangulum; F-type subgiant"),
        StarRecord("Deltotum",   "β Tri", "Triangulum",  32.394,  34.988, "A5III", 3.00, 124,
                   "A-type giant, standard star"),
        StarRecord("Gamma Tri",  "γ Tri", "Triangulum",  30.929,  33.847, "A1Vnn", 4.01, 118,
                   "Rapid rotator"),
    ],

    # ------------------------------------------------------------------
    "Pegasus": [
        StarRecord("Enif",      "ε Peg", "Pegasus", 326.046,   9.875, "K2Ib",   2.38, 690,
                   "Nose of Pegasus; K-type supergiant"),
        StarRecord("Scheat",    "β Peg", "Pegasus", 345.944,  28.083, "M2.5IIa",2.42, 196,
                   "Semiregular red giant pulsator (2.4–2.8)"),
        StarRecord("Markab",    "α Peg", "Pegasus", 346.190,  15.205, "B9III",  2.49, 140,
                   "Shoulder of Pegasus; B-type giant"),
        StarRecord("Algenib",   "γ Peg", "Pegasus",   3.309,  15.183, "B2IV",   2.83, 391,
                   "Beta Cephei pulsator"),
        StarRecord("Matar",     "η Peg", "Pegasus", 343.146,  30.222, "G2II+F5", 2.94, 215,
                   "Yellow bright giant"),
        StarRecord("Homam",     "ζ Peg", "Pegasus", 329.609,  10.831, "B8V",    3.40, 204,
                   "B-type main sequence"),
        StarRecord("Biham",     "θ Peg", "Pegasus", 336.034,   6.196, "A1V",    3.53, 97,
                   "A-type main sequence"),
    ],

    # ------------------------------------------------------------------
    "Eridanus": [
        StarRecord("Achernar",  "α Eri", "Eridanus",  24.429, -57.237, "B3Vpe",  0.46,  139,
                   "Southernmost bright star in Eridanus; rapid rotator, oblate"),
        StarRecord("Acamar",    "θ Eri", "Eridanus",  44.565, -40.305, "A4III",  2.88,  161,
                   "Wide visual double"),
        StarRecord("Zaurak",    "γ Eri", "Eridanus",  59.507, -13.509, "M1III",  2.95,  221,
                   "Red giant semiregular variable"),
        StarRecord("Cursa",     "β Eri", "Eridanus",  76.962,  -5.086, "A3IIIv", 2.79,   89,
                   "Foot of Orion constellation marker"),
        StarRecord("Rana",      "δ Eri", "Eridanus",  52.888,  -9.763, "K0IV",   3.54,   29,
                   "K-type subgiant, nearby star"),
        StarRecord("Beid",      "ο¹ Eri","Eridanus",  68.888, -6.838, "F2III",  4.04,  125,
                   "F-type giant"),
    ],

    # ------------------------------------------------------------------
    "Orion": [
        StarRecord("Rigel",      "β Ori", "Orion",  78.634,  -8.201, "B8Ia",      0.13,  863,
                   "Brightest Orion; blue-white supergiant, luminosity ~120000 L\u2609"),
        StarRecord("Betelgeuse", "α Ori", "Orion",  88.793,   7.407, "M1-M2Ia",   0.42,  700,
                   "Red supergiant, semiregular variable; candidate supernova"),
        StarRecord("Bellatrix",  "γ Ori", "Orion",  81.283,   6.350, "B2III",     1.64,  244,
                   "Amazon star; B-type giant"),
        StarRecord("Alnilam",    "ε Ori", "Orion",  84.053,  -1.202, "B0Ia",      1.70, 2000,
                   "Central belt star; massive blue supergiant"),
        StarRecord("Alnitak",    "ζ Ori", "Orion",  85.190,  -1.943, "O9.5Ib",    1.77,  1260,
                   "Eastern belt star; near Horsehead Nebula"),
        StarRecord("Saiph",      "κ Ori", "Orion",  86.939,  -9.670, "B0.5Ia",    2.07,  724,
                   "B-type supergiant, southwestern foot of Orion"),
        StarRecord("Mintaka",    "δ Ori", "Orion",  83.002,  -0.299, "O9.5II",    2.25,  900,
                   "Western belt star; double with weak emission"),
        StarRecord("Meissa",     "λ Ori", "Orion",  83.785,   9.934, "O8III",     3.33, 1100,
                   "Head of Orion; O-type giant, Orion OB1 association"),
    ],

    # ------------------------------------------------------------------
    "Auriga": [
        StarRecord("Capella",     "α Aur", "Auriga",  79.172,  45.998, "G5III+G0III", 0.08,  43,
                   "Brightest Auriga; giant spectroscopic binary, G+G pair"),
        StarRecord("Menkalinan", "β Aur", "Auriga",  89.882,  44.947, "A2IV",        1.90,  82,
                   "A-type subgiant, eclipsing binary 3.96 d"),
        StarRecord("Hassaleh",   "ι Aur", "Auriga",  74.248,  33.166, "K3II",        2.69, 512,
                   "K-type bright giant"),
        StarRecord("Mahasim",    "θ Aur", "Auriga",  89.930,  37.213, "A0pSi",       2.62, 173,
                   "Chemically peculiar Si-star"),
    ],

    # ------------------------------------------------------------------
    "Canis Major": [
        StarRecord("Sirius",   "α CMa", "Canis Major", 101.288, -16.716, "A1V",    -1.46,    8.6,
                   "Brightest star in the sky; white dwarf binary (Sirius B)"),
        StarRecord("Adhara",   "ε CMa", "Canis Major", 104.656, -28.972, "B2Ia",    1.50,  431,
                   "Strongest UV source beyond the Sun; blue supergiant"),
        StarRecord("Wezen",    "δ CMa", "Canis Major", 107.098, -26.393, "F8Ia",    1.84, 1600,
                   "Yellow-white hypergiant supergiant"),
        StarRecord("Mirzam",   "β CMa", "Canis Major",  95.675, -17.956, "B1II-III",1.98,  500,
                   "Beta Cephei pulsator"),
        StarRecord("Aludra",   "η CMa", "Canis Major", 111.024, -29.303, "B5Ia",    2.45, 3200,
                   "B-type hypergiant, one of largest stars known"),
        StarRecord("Furud",    "ζ CMa", "Canis Major", 100.003, -30.063, "B2.5V",   3.02,  362,
                   "B-type main sequence"),
    ],

    # ------------------------------------------------------------------
    "Canis Minor": [
        StarRecord("Procyon",  "α CMi", "Canis Minor", 114.826,   5.225, "F5IV-V",   0.34,  11.5,
                   "8th brightest star; subgiant with white dwarf companion"),
        StarRecord("Gomeisa",  "β CMi", "Canis Minor", 111.791,   8.289, "B8Ve",     2.90,  170,
                   "B-type emission star, rapid rotator"),
    ],

    # ------------------------------------------------------------------
    "Hydra": [
        StarRecord("Alphard",   "α Hya", "Hydra", 141.897,  -8.659, "K3II",   1.97,  177,
                   "Brightest Hydra; solitary K-type bright giant"),
        StarRecord("Minchir",   "σ Hya", "Hydra", 127.566,   5.952, "K2IIIb", 4.44,  351,
                   "K-type giant"),
        StarRecord("Ukdah",     "ι Hya", "Hydra", 133.848,  -1.144, "K2.5III",3.91,  303,
                   "K-type giant"),
        StarRecord("Lisan al Shuja","ε Hya","Hydra",130.809,   6.419,"F0III+G5III",3.38, 135,
                   "Close binary, F+G pair"),
    ],

    # ------------------------------------------------------------------
    "Crater": [
        StarRecord("Alkes",    "α Crt", "Crater", 164.944, -18.299, "K1III",  4.07, 174,
                   "Brightest Crater; K-type giant"),
        StarRecord("Beta Crt", "β Crt", "Crater", 161.690, -22.826, "A2III",  4.48, 296,
                   "A-type giant"),
        StarRecord("Labrum",   "δ Crt", "Crater", 169.841, -14.778, "G8II",   3.56, 163,
                   "G-type bright giant"),
    ],

    # ------------------------------------------------------------------
    "Corvus": [
        StarRecord("Gienah",   "γ Crv", "Corvus", 183.953, -17.542, "B8IIIp",  2.59, 165,
                   "Brightest Corvus; B-type giant with peculiar spectrum"),
        StarRecord("Kraz",     "β Crv", "Corvus", 188.600, -23.397, "G5II",    2.65, 146,
                   "G-type bright giant"),
        StarRecord("Algorab",  "δ Crv", "Corvus", 187.464, -16.515, "B9.5V",   2.94, 88,
                   "B-type main sequence; wide visual double"),
        StarRecord("Alchiba",  "α Crv", "Corvus", 182.101, -24.729, "F1V",     4.02,  48,
                   "F-type main sequence, nearest Corvus star"),
        StarRecord("Minkar",   "ε Crv", "Corvus", 186.847, -22.620, "K2III",   3.02, 303,
                   "K-type giant"),
    ],

    # ------------------------------------------------------------------
    "Ursa Major": [
        StarRecord("Alioth",   "\u03b5 UMa", "Ursa Major", 193.507,  55.960, "A0pCr",  1.77,  81,
                   "Brightest UMa; chemically peculiar Ap star"),
        StarRecord("Dubhe",    "\u03b1 UMa", "Ursa Major", 165.932,  61.751, "K0IIIa", 1.79, 124,
                   "Pointer star to Polaris; K-type giant"),
        StarRecord("Alkaid",   "\u03b7 UMa", "Ursa Major", 206.886,  49.313, "B3V",    1.85, 101,
                   "End of the Big Dipper handle; B-type main sequence"),
        StarRecord("Mizar",    "\u03b6 UMa", "Ursa Major", 200.981,  54.925, "A2V",    2.04, 86,
                   "First telescopic double star; with Alcor (80 UMa)"),
        StarRecord("Merak",    "\u03b2 UMa", "Ursa Major", 165.461,  56.382, "A1V",    2.34,  79,
                   "Second pointer to Polaris; A-type main sequence"),
        StarRecord("Phecda",   "\u03b3 UMa", "Ursa Major", 178.458,  53.695, "A0Ve",   2.44,  84,
                   "Gamma Ursae Majoris; rapid rotator"),
        StarRecord("Tania Australis", "\u03bc UMa", "Ursa Major", 167.415, 41.499, "M0III", 3.05, 250,
                   "M-type giant, southern of the Two Stepping Stones"),
        StarRecord("Megrez",    "\u03b4 UMa", "Ursa Major", 183.857,  57.033, "A3V",   3.32,  81,
                   "Junction of Dipper handle and bowl"),
    ],

    # ------------------------------------------------------------------
    "Ursa Minor": [
        StarRecord("Polaris",  "\u03b1 UMi", "Ursa Minor",  37.955,  89.264, "F7Ib",    1.97,  430,
                   "North Pole star; Cepheid variable, ~4 day period"),
        StarRecord("Kochab",   "\u03b2 UMi", "Ursa Minor", 222.676,  74.156, "K4III",   2.08,  131,
                   "Former pole star (3000 BCE); K-type giant"),
        StarRecord("Pherkad",  "\u03b3 UMi", "Ursa Minor", 230.180,  71.834, "A3III",   3.05,  487,
                   "A-type giant, outer bowl of Little Dipper"),
        StarRecord("Yildun",   "\u03b4 UMi", "Ursa Minor", 256.432,  86.586, "A1V",     4.35,  183,
                   "Close to celestial north pole"),
    ],

    # ------------------------------------------------------------------
    "Canes Venatici": [
        StarRecord("Cor Caroli", "\u03b1 CVn", "Canes Venatici", 194.007,  38.318, "A0p",  2.89,  110,
                   "Prototype Ap star; strong magnetic field"),
        StarRecord("Chara",      "\u03b2 CVn", "Canes Venatici", 188.435,  41.357, "G0V",  4.26,   27,
                   "G-type main sequence, solar analogue"),
    ],

    # ------------------------------------------------------------------
    "Bo\u00f6tes": [
        StarRecord("Arcturus",  "\u03b1 Boo", "Bo\u00f6tes", 213.915,  19.182, "K1.5IIIFe",  -0.05,  37,
                   "4th brightest star; K-type red giant, high proper motion"),
        StarRecord("Izar",      "\u03b5 Boo", "Bo\u00f6tes", 221.247,  27.074, "K0II+A2V",    2.35, 203,
                   "Pulcherrima — beautiful double, gold+blue"),
        StarRecord("Muphrid",   "\u03b7 Boo", "Bo\u00f6tes", 208.671,  18.398, "G0IVvar",     2.68,  37,
                   "G-type subgiant, nearest to Arcturus on sky"),
        StarRecord("Seginus",   "\u03b3 Boo", "Bo\u00f6tes", 218.019,  38.308, "A7III",       3.04, 85,
                   "A-type giant"),
        StarRecord("Nekkar",    "\u03b2 Boo", "Bo\u00f6tes", 225.486,  40.390, "G8IIIa",      3.50, 219,
                   "G-type giant, northern Bo\u00f6tes"),
    ],

    # ------------------------------------------------------------------
    "Corona Borealis": [
        StarRecord("Alphecca",  "\u03b1 CrB", "Corona Borealis", 233.673,  26.715, "A0V+G5V", 2.21,  75,
                   "Gem of the Crown; eclipsing binary 17.36 d"),
        StarRecord("Nusakan",   "\u03b2 CrB", "Corona Borealis", 231.956,  29.106, "F0pSrEuCr",3.68, 114,
                   "Chemically peculiar SrEuCr star"),
        StarRecord("Theta CrB", "\u03b8 CrB", "Corona Borealis", 228.327,  31.360, "B6Vn",    4.14, 312,
                   "Rapid rotator"),
    ],

    # ------------------------------------------------------------------
    "Serpens": [
        StarRecord("Unukalhai",  "\u03b1 Ser", "Serpens", 236.067,   6.426, "K2IIIb",  2.63,  73,
                   "Heart of the Serpent; K-type giant"),
        StarRecord("Mu Ser",     "\u03bc Ser", "Serpens", 237.402,  -3.430, "F2V",      3.53,  57,
                   "F-type main sequence"),
        StarRecord("Delta Ser",  "\u03b4 Ser", "Serpens", 240.037,  10.539, "F0IV",     3.80, 210,
                   "F-type subgiant"),
    ],

    # ------------------------------------------------------------------
    "Ophiuchus": [
        StarRecord("Rasalhague", "\u03b1 Oph", "Ophiuchus", 263.734,  12.560, "A5III",     2.08,  47,
                   "Head of the Serpent Bearer; A-type giant"),
        StarRecord("Sabik",      "\u03b7 Oph", "Ophiuchus", 257.595, -15.724, "A2V",        2.43,  84,
                   "Double A-type system"),
        StarRecord("Yed Prior",  "\u03b4 Oph", "Ophiuchus", 243.586,  -3.694, "M1III",      2.74, 171,
                   "Red giant, northern of the Hand stars"),
        StarRecord("Yed Posterior","\u03b5 Oph","Ophiuchus",244.580,  -4.692, "G9.5IIIb",   3.24, 107,
                   "G-type giant, southern Hand star"),
        StarRecord("Cebalrai",   "\u03b2 Oph", "Ophiuchus", 265.868,   4.570, "K2III",      2.77,  82,
                   "K-type giant"),
        StarRecord("Marfik",     "\u03bb Oph", "Ophiuchus", 258.836,   1.984, "A1Vnn",      3.82, 166,
                   "Rapid rotator, A-type"),
    ],

    # ------------------------------------------------------------------
    "Centaurus": [
        StarRecord("Rigil Kentaurus", "\u03b1 Cen A", "Centaurus", 219.899, -60.835, "G2V",  -0.01,   4.4,
                   "Closest star system to Sun; yellow dwarf, solar twin"),
        StarRecord("Toliman",         "\u03b1 Cen B", "Centaurus", 219.899, -60.835, "K1V",   1.33,   4.4,
                   "Companion to Rigil Kentaurus; K-type main sequence"),
        StarRecord("Hadar",           "\u03b2 Cen",   "Centaurus", 210.956, -60.373, "B1III",  0.61, 390,
                   "Agena; blue giant with Beta Cephei pulsation"),
        StarRecord("Muhlifain",       "\u03b3 Cen",   "Centaurus", 190.379, -48.960, "A1IV",   2.17, 130,
                   "A-type subgiant"),
        StarRecord("Menkent",         "\u03b8 Cen",   "Centaurus", 211.671, -36.370, "K0IIIb", 2.06,  61,
                   "Shoulder of Centaurus; K-type giant"),
    ],

    # ------------------------------------------------------------------
    "Crux": [
        StarRecord("Acrux",    "\u03b1 Cru", "Crux", 186.650, -63.100, "B0.5IV+B1V",  0.77, 320,
                   "Brightest Crux; double B-type system"),
        StarRecord("Mimosa",   "\u03b2 Cru", "Crux", 191.930, -59.689, "B0.5III",      1.25, 280,
                   "Beta Crucis; Beta Cephei pulsator"),
        StarRecord("Gacrux",   "\u03b3 Cru", "Crux", 187.791, -57.113, "M3.5III",      1.59,  88,
                   "Nearest red giant to the Sun"),
        StarRecord("Imai",     "\u03b4 Cru", "Crux", 183.786, -58.749, "B2IV",         2.79, 364,
                   "B-type subgiant"),
    ],

    # ------------------------------------------------------------------
    "Piscis Austrinus": [
        StarRecord("Fomalhaut", "\u03b1 PsA", "Piscis Austrinus", 344.413, -29.622, "A3V",   1.16,  25,
                   "Bright debris-disk star with confirmed exoplanet candidate"),
        StarRecord("Epsilon PsA","\u03b5 PsA","Piscis Austrinus", 340.649, -27.044, "B8V",   4.17, 247,
                   "B-type main sequence"),
    ],

    # ------------------------------------------------------------------
    "Draco": [
        StarRecord("Eltanin",   "\u03b3 Dra", "Draco", 269.151,  51.489, "K5III",    2.24, 154,
                   "Head of Draco; bright K-type giant"),
        StarRecord("Rastaban",  "\u03b2 Dra", "Draco", 262.608,  52.301, "G2Ib-IIa", 2.79, 380,
                   "G-type bright giant"),
        StarRecord("Thuban",    "\u03b1 Dra", "Draco", 211.097,  64.376, "A0III",    3.65, 303,
                   "Former North Pole star (~2700 BCE); A-type giant"),
        StarRecord("Edasich",   "\u03b9 Dra", "Draco", 231.232,  58.966, "K2III",    3.29, 101,
                   "K-type giant with confirmed exoplanet"),
        StarRecord("Aldhibah",  "\u03b6 Dra", "Draco", 257.196,  65.714, "A2V",      3.17, 330,
                   "A-type main sequence"),
    ],

    # ------------------------------------------------------------------
    "Lyra": [
        StarRecord("Vega",     "\u03b1 Lyr", "Lyra", 279.235,  38.784, "A0Va",     0.03,  25,
                   "5th brightest; standard photometric reference, pole star ~14000 CE"),
        StarRecord("Sulafat",  "\u03b3 Lyr", "Lyra", 284.736,  32.690, "B9III",    3.24, 620,
                   "B-type giant"),
        StarRecord("Sheliak",  "\u03b2 Lyr", "Lyra", 282.520,  33.363, "B8.5IIIv", 3.52, 960,
                   "Prototype eclipsing binary with mass transfer"),
        StarRecord("Epsilon Lyr","ε Lyr","Lyra", 283.626,  39.670, "A4Vwvar",  4.59, 162,
                   "Double-double: two pairs of A-type stars"),
    ],

    # ------------------------------------------------------------------
    "Cygnus": [
        StarRecord("Deneb",      "\u03b1 Cyg", "Cygnus", 310.358,  45.280, "A2Ia",    1.25, 2600,
                   "19th brightest; white supergiant, among most luminous known"),
        StarRecord("Sadr",       "\u03b3 Cyg", "Cygnus", 305.557,  40.257, "F8Ib",    2.23, 1500,
                   "Heart of the Swan; yellow-white supergiant"),
        StarRecord("Gienah Cyg", "\u03b5 Cyg", "Cygnus", 311.553,  33.970, "K0III",   2.46,  73,
                   "Wing of the Swan; K-type giant"),
        StarRecord("Albireo",    "\u03b2 Cyg", "Cygnus", 292.680,  27.960, "K3II",    3.05, 430,
                   "Gold-blue double, finest colour contrast in sky"),
        StarRecord("Delta Cyg",  "\u03b4 Cyg", "Cygnus", 296.244,  45.131, "B9.5III", 2.87, 165,
                   "B-type giant"),
    ],

    # ------------------------------------------------------------------
    "Aquila": [
        StarRecord("Altair",    "\u03b1 Aql", "Aquila", 297.696,   8.868, "A7V",   0.77,  17,
                   "12th brightest; rapid rotator, oblate, Summer Triangle vertex"),
        StarRecord("Tarazed",   "\u03b3 Aql", "Aquila", 296.565,  10.613, "K3II",  2.72, 461,
                   "K-type bright giant"),
        StarRecord("Alshain",   "\u03b2 Aql", "Aquila", 298.828,   6.407, "G8IV",  3.71,  45,
                   "G-type subgiant"),
        StarRecord("Okab",      "\u03b6 Aql", "Aquila", 286.353,  13.864, "A0Vn",  2.99,  83,
                   "Rapid rotator, A-type main sequence"),
    ],

    # ------------------------------------------------------------------
    "Delphinus": [
        StarRecord("Sualocin",  "\u03b1 Del", "Delphinus", 309.909,  15.913, "B9IVn",  3.77, 254,
                   "Named by Niccolò Cacciatore (his name reversed)"),
        StarRecord("Rotanev",   "\u03b2 Del", "Delphinus", 309.386,  14.595, "F5IV",   3.63, 101,
                   "F-type subgiant; name reversed from Venator"),
        StarRecord("Gamma Del", "\u03b3 Del", "Delphinus", 308.651,  16.124, "K1IV",   3.87, 101,
                   "K-type subgiant double"),
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
        f"{'EXTENDED ZODIAC & BELT STAR CATALOG':^80}",
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
