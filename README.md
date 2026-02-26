# clawd-pinterest-multi 📌

Automatický AliExpress Affiliate Pinterest bot pro více profilů.

## Profily

| Profil | Niche | Affiliate |
|--------|-------|-----------|
| @PohadkoveTipyCZ | Hračky, pohádky, děti | AliExpress |

## Pipeline

```
AliExpress API → affiliate link → stažení obrázku → Pinterest pin
```

## Rychlý start

```bash
cd /home/server/clawd-pinterest-multi/scripts

# Test (bez postování):
python3 daily_run.py --dry-run

# Produkce:
python3 daily_run.py
```

## Struktura

```
clawd-pinterest-multi/
├── scripts/
│   ├── aliexpress_api.py      # AliExpress Portals API
│   ├── pinterest_poster.py    # Pinterest Playwright poster
│   └── daily_run.py           # Denní runner (cron entry point)
├── data/
│   ├── config.json            # Konfigurace profilů
│   └── pin-log.json           # Log pinů
├── memory/                    # Denní logy
└── AGENTS.md                  # Instrukce pro agenta
```

## Cron

`pinterest-multi-daily` — každý den 5:00 (OpenClaw cron job)

## Reference

- [PINTEREST_NOTES.md](/home/server/clawd-social/skills/PINTEREST_NOTES.md) — ověřené selektory
- [AliExpress Portals API](https://portals.aliexpress.com/affPortal/home)
