# Repository Audit — Security & Git Hygiene

Scope: secrets exposure and git/repo hygiene only (no code-quality or scientific-methodology review). Read-only audit — no fixes applied. Repo: `github.com/Quintinlf/Spectroscopy` (**public**, confirmed via GitHub API, last pushed 2026-06-28).

## 1. Critical: live secret exposed in a public repo

`nuclear_magnetic_resonance_spectrospy/fall_semester_2025/chem_tools/credentials.json` contains a real Google OAuth **`client_secret`** (`GOCSPX-...`), tracked since commit `6d02a07` ("rearranged some things in the repo"). Because the repo is public, this secret has been fetchable by anyone since that commit and still is today.

A `.gitignore` sits right next to it (`chem_tools/.gitignore`) and was clearly *meant* to exclude the file:

```
credentials_file=./credentials.json
data/
```

That first line is not valid `.gitignore` syntax — gitignore patterns are just paths/globs, not `key=value` pairs. Git reads it as "ignore a file literally named `credentials_file=./credentials.json`", which doesn't exist, so it's a no-op. The file was committed despite the apparent intent to keep it out.

**Recommended remediation (not performed in this pass):**
1. Rotate the OAuth client secret in Google Cloud Console immediately — treat the current value as compromised regardless of any other cleanup.
2. Fix `chem_tools/.gitignore` to a real pattern (`credentials.json`, plus `token.json` — see §4).
3. Once rotated, decide whether to scrub the old secret from git history (`git filter-repo` or BFG Repo-Cleaner). This rewrites history and force-pushes, so it should be a separate, explicit, confirmed action — not bundled into routine cleanup.

## 2. Low-risk secret-adjacent finding

- Root `.env` is tracked (added in `48467ba`, never touched since) but is **0 bytes** in both the working tree and `HEAD` — nothing is leaking today. Risk is purely that it's tracked at all: a future edit could silently commit real secrets into it since nothing is gitignoring it.
- A repo-wide `git grep` for `api[_-]?key|secret|password|token|client_secret|AKIA[0-9A-Z]{16}` across all tracked `.py/.ipynb/.json/.md/.cfg/.ini` files found no other embedded secrets. Remaining hits are placeholders (`API_KEY = 'your_nrel_api_key'` in `solar_project/solar_spec.ipynb`) or unrelated identifiers named `token`/`mode_token` in `stellar_spectrospy/planetary_spectra/*.py`.
- `credentials.json` is the only credential-shaped tracked filename in the repo (checked for `credential|secret|*.pem|*.key|token.json` patterns).

## 3. Repository bloat

`.git` is **467MB**. Breakdown by contributor:

| Source | Size | Detail |
|---|---|---|
| ML checkpoints | 153MB | 43 tracked `.pth` files under `nuclear_magnetic_resonance_spectrospy/fall_semester_2025/checkpoints/` |
| Oversized notebooks | ~130MB+ | `project_1.ipynb` (33MB), `Main_project.ipynb` (33MB), `project_1_spring_2025.ipynb` committed twice as distinct blobs (33MB each) — all from embedded output images never cleared before commit |
| Large NMR data files | up to 53MB each | `.asc` files under `fall_semester_2025/data/correctly_processed_fid/krishna_data/2d_nmr_data/` |
| Misc | 9MB | `nuclear_magnetic_resonance_spectrospy/spring_semester_2025/pen.gif` |
| Stellar/planetary caches | 15MB | `stellar_spectrospy/` (spectral cache CSVs + 3 tracked `.db` files) |

17 notebooks and 32 tracked `.pyc` files are also in the repo, compounding the size.

**Recommendation:** move checkpoints and raw large data files to Git LFS or an external store (not git); strip notebook outputs before committing (`nbstripout` or `jupyter nbconvert --clear-output`) — this alone accounts for a large share of the bloat since the same notebook exists twice at 33MB.

## 4. Tracked files/artifacts that shouldn't be versioned

- **No root `.gitignore` exists anywhere in this repo.** The only `.gitignore` present is the broken one in `chem_tools/` (§1).
- **32 `__pycache__/*.pyc` files** tracked across 4 module directories: `machine_learning/`, `nuclear_magnetic_resonance_spectrospy/`, `stellar_spectrospy/`, `stellar_spectrospy/planetary_spectra/`.
- **`desktop.ini`** (Windows Explorer folder-metadata file) tracked at repo root — has no reason to be versioned.
- **3 tracked SQLite `.db` files** (query-result caches, not source data): `stellar_spectrospy/spectral_results.db`, `stellar_spectrospy/planetary_spectra/planetary_results.db`, and a duplicate at the nested path below.
- **Stray mirrored-URL directory**: `raw.githubusercontent.com/Quintinlf/NMR-Project/main/spring_semester_2025/13_03_11_indst_1H%20fid.asc` exists both at repo root and nested under `nuclear_magnetic_resonance_spectrospy/spring_semester_2025/` — the path shape (`raw.githubusercontent.com/<user>/<repo>/main/...`) is the default output layout of `wget -r` or `curl -O` run against a raw GitHub URL, and looks like it was committed by accident rather than intentionally added.
- **Duplicated nested path**: `stellar_spectrospy/planetary_spectra/notebooks/stellar_spectrospy/planetary_spectra/...` re-creates the full project path a second time inside itself (containing its own copy of `planetary_results.db`, `planetary_temporal_results.csv`, and a `spectral_cache/` tree). This is the signature of a script or notebook writing relative output paths while its working directory was already inside `stellar_spectrospy/planetary_spectra/` — the output landed one level too deep and got committed as-is.

**Recommendation:** add a root `.gitignore` covering at minimum:
```
__pycache__/
*.pyc
.venv/
.env
desktop.ini
*.pth
*.db
```
then `git rm --cached` the currently-tracked files that newly match it (this untracks going forward without touching working-tree copies). Also remove the stray `raw.githubusercontent.com/` directories and the duplicated nested `stellar_spectrospy/planetary_spectra/notebooks/stellar_spectrospy/...` path, and fix whatever script produced the latter to write outputs relative to a stable root.

## 5. Minor: documentation/structure mismatch

Root `README.md`'s repository-tree diagram lists `machine_learning/checkpoints/`, but no `checkpoints/` directory exists under `machine_learning/` — the actual 43 checkpoint files live under `nuclear_magnetic_resonance_spectrospy/fall_semester_2025/checkpoints/`. Not a security or hygiene issue, but worth fixing so the README reflects reality.

## Summary — priority order

1. **Rotate the exposed Google OAuth client secret now**, independent of everything else here.
2. Add a root `.gitignore`; fix the broken one in `chem_tools/`.
3. Untrack `__pycache__`, `desktop.ini`, `.env`, and the `.db` caches going forward (`git rm --cached`).
4. Move/strip large binaries (checkpoints, notebook outputs, big `.asc` files) out of history to shrink `.git` from 467MB.
5. Clean up the stray `raw.githubusercontent.com/` mirror directories and the duplicated nested `stellar_spectrospy/planetary_spectra/notebooks/...` path.
6. Fix the `machine_learning/checkpoints/` reference in the README.

None of the above was executed in this pass — this file is a findings report only.
