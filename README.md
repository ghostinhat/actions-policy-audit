# Actions Policy Audit

An offline preflight for GitHub Actions workflow policy. It flags common cost-control and supply-chain gaps without uploading workflow contents or repository metadata.

This is an experimental `v0.1.0` validation release. It is intentionally small: no account, hosted service, telemetry, or paid plan is required.

## Use in a workflow

Check out the repository before running the audit:

```yaml
name: Actions policy audit

on:
  pull_request:
  workflow_dispatch:

permissions:
  contents: read

jobs:
  audit:
    runs-on: ubuntu-latest
    timeout-minutes: 5
    steps:
      - uses: actions/checkout@v4
      - uses: ghostinhat/actions-policy-audit@v0.1.0
        with:
          path: .
          format: text
          fail-on: high
```

For stronger supply-chain control, replace version tags with the full commit SHA you reviewed. Mutable external Action references are intentionally reported by this tool, including the example tags above.

## Run locally

Python 3.10 or newer is recommended. The CLI uses only the Python standard library.

```bash
python3 actions_policy_audit.py /path/to/repository
python3 actions_policy_audit.py . --format json --fail-on any
```

`--fail-on` accepts `high`, `any`, or `none`. The default is `high`.

## Checks

- explicit workflow or job permissions
- job timeouts
- full-SHA pinning for external Actions
- use of `pull_request_target`
- artifact retention limits

Findings are review signals, not proof that a workflow is vulnerable. In particular, intentional tag use by official or same-owner Actions is still reported.

## Privacy and limits

- Runs locally in the caller's runner with no network calls made by the audit code.
- Does not require a token or write permission.
- Does not transmit source, workflow contents, repository names, secrets, personal data, or telemetry.
- Does not modify the repository being checked.
- Uses a lightweight line-oriented parser. It does not fully resolve YAML anchors, expression expansion, or effective permissions in called reusable workflows.
- Zero scanned workflow files means there was nothing to inspect; it does not mean the repository was proven safe.

This experimental release has no SLA or guaranteed support response. GitHub Issues, wiki, and projects are disabled during the bounded validation period.

## License

[MIT](LICENSE)
