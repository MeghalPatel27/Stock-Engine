# Configuration

Layer order (highest wins):

1. `default.yaml` (committed)
2. `local.yaml` (optional, gitignored)
3. Environment variables / `.env` (secrets and path overrides)

Every engine run must record `config_version` and `config_hash` of the effective merged config.
