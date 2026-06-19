# NemoClaw Connectors

Pluggable data-source adapters for monthly ingestion.

## Connector field

Set `connector:` in the tenant's ingestion section (or as a top-level field):

```yaml
ingestion:
  connector: manual_folder   # default — reads CSV/XLSX files dropped in data_root
  # connector: plaid         # Plaid /transactions/sync for live bank feeds
```

## manual_folder

No configuration needed. Drop CSV or XLSX files in `data_root`. The existing
ingestion/loader handles parsing and deduplication.

## plaid

Cursor-based incremental sync via `/transactions/sync`. Requires:

1. Create a Plaid account at https://dashboard.plaid.com and obtain a
   `client_id` and `secret` for the Sandbox or Production environment.
2. Use Plaid Link (https://plaid.com/docs/link/) to connect the bank and
   obtain an `access_token` for that institution.
3. Set environment variables in the tenant's `.env` file (outside this repo):

```
PLAID_CLIENT_ID=your_client_id
PLAID_SECRET=your_secret
PLAID_ACCESS_TOKEN=access-sandbox-xxxxxxxx
PLAID_ENV=sandbox   # or production
```

4. Install the optional dep: `pip install 'nemoclaw-smb[plaid]'`
5. Set `connector: plaid` in the tenant config.

State (the Plaid cursor) is persisted to `data_root/state/connector.json`.

## Scheduling (do not install cron — these are reference lines)

```
# Weekly cycle — every Monday at 06:00
0 6 * * 1  cd /path/to/repo && PYTHONPATH=. python3 scripts/tenant_loop.py <slug> weekly

# Monthly cycle — first day of month at 07:00
0 7 1 * *  cd /path/to/repo && PYTHONPATH=. python3 scripts/tenant_loop.py <slug> monthly
```

### launchd (macOS)

```xml
<!-- ~/Library/LaunchAgents/com.nemoclaw.tenant-loop-weekly.plist -->
<key>StartCalendarInterval</key>
<dict>
  <key>Weekday</key><integer>2</integer>  <!-- Monday -->
  <key>Hour</key><integer>6</integer>
  <key>Minute</key><integer>0</integer>
</dict>
<key>ProgramArguments</key>
<array>
  <string>/usr/bin/python3</string>
  <string>/path/to/scripts/tenant_loop.py</string>
  <string>your-tenant-slug</string>
  <string>weekly</string>
</array>
```

Real tenant `.env` files live outside this repo under `$NEMOCLAW_TENANTS_ROOT`.
Never commit access tokens or secrets.
