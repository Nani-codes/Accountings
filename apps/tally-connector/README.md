# TallyPrime Hosted Connector

A Windows dial-out connector that bridges your local TallyPrime installation with the Accountings cloud platform.

## Prerequisites

- **Python 3.11 or later** installed on your Windows machine
- **TallyPrime** running with XML/ODBC port enabled (default: port 9000)
- **Pairing code** from Accountings Settings → Tally

## Installation

### Step 1: Install Python

Download and install Python 3.11+ from [python.org](https://www.python.org/downloads/). During installation, **check the box "Add Python to PATH"**.

### Step 2: Install the Connector

Open Command Prompt (cmd.exe) and run:

```bash
pip install -e .
```

This installs the connector and makes the `accountings-tally-connector` command available.

### Step 3: Enable TallyPrime XML/ODBC Port

1. Open TallyPrime
2. Go to **Gateway of Tally** → **F12: Configure**
3. Enable **XML/ODBC** port (default: 9000)
4. Keep TallyPrime running

### Step 4: Run the Connector

Open Command Prompt and run:

```bash
accountings-tally-connector
```

On first run, you'll be prompted to:
1. Enter the **pairing code** from Accountings Settings → Tally
2. Confirm Tally host (default: `localhost`)
3. Confirm Tally port (default: `9000`)

The connector will:
- Verify Tally is reachable
- Pair with the cloud API
- Save your device token locally
- Start sending heartbeats and handling requests

### Step 5: Keep Running

The connector must stay running for the cloud platform to communicate with your local Tally. Consider:
- Running it in a dedicated Command Prompt window
- Setting it up as a Windows Service (advanced)
- Using Task Scheduler to auto-start on login

## Troubleshooting

### "Could not reach Tally"

- Verify TallyPrime is running
- Check that XML/ODBC port is enabled in TallyPrime
- Verify the port number (default: 9000)
- Try `ping localhost` to verify network connectivity

### "Authentication failed"

- Go to Accountings Settings → Tally
- Click "Re-pair" to get a new pairing code
- Delete `~/.accountings/tally-connector.json` on your machine
- Run `accountings-tally-connector` again and enter the new code

### "Connection refused"

- Verify the API URL is correct (check `ACCOUNTINGS_API_URL` environment variable)
- Ensure you have internet connectivity
- Check firewall settings

## Configuration

The connector stores its configuration in:

```
~/.accountings/tally-connector.json
```

This file contains:
- `device_token`: Your unique device identifier
- `api_url`: Cloud API URL
- `tally_host`: Local Tally host
- `tally_port`: Local Tally port

To re-pair, delete this file and run the connector again.

## Environment Variables

- `ACCOUNTINGS_API_URL`: Cloud API URL (default: `http://127.0.0.1:8000`)

Example:

```bash
set ACCOUNTINGS_API_URL=https://api.accountings.example.com
accountings-tally-connector
```

## Support

For issues or questions, contact support@accountings.example.com

## Building the Windows `.exe` (maintainers)

Non-technical firms download a prebuilt single-file executable instead of
installing Python. The exe is built with **PyInstaller on Windows** (PyInstaller
is not a cross-compiler, so it must run on a Windows host).

**Automated (recommended):** push a tag to trigger the `Connector Release`
GitHub Action, which builds on `windows-latest` and attaches the exe to a
GitHub Release:

```bash
git tag connector-v0.1.0
git push origin connector-v0.1.0
```

The asset is then served at a stable URL:

```
https://github.com/<owner>/<repo>/releases/latest/download/AccountingsConnector.exe
```

Point `TALLY_CONNECTOR_DOWNLOAD_URL` at that so the app's download button works.

**Manual (on a Windows machine):**

```bash
cd apps/tally-connector
pip install -e ".[build]"
pyinstaller build.spec
# -> dist/AccountingsConnector.exe
dist\AccountingsConnector.exe --version
```

> **Note on SmartScreen:** unsigned exes trigger a Windows "unknown publisher"
> warning. To remove it, code-sign the exe with an OV/EV certificate — see the
> commented signing step in `.github/workflows/connector-release.yml`.
