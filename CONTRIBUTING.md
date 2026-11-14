# Contributing

- **Sample rolls wanted.** If you shoot a 450D, open an issue with a few CR2
  files (a grey card + a colour chart shot is perfect) so the stocks can be tuned.
- **New stocks:** add a `FilmStock(...)` in `kfilm/stocks.py`, run
  `kfilm print <id> sample.CR2`, and attach before/after images to the PR.
- **Darkrooms:** if Darkrooms opens (or refuses) a K-Film roll, tell us what it said.
- **Other cameras:** any camera LibRaw reads works already. Add sensor size
  info in `process.py` if grain scale looks off.
- Run `pytest -q` before opening a pull request.
