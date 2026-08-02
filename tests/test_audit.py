import tempfile
import unittest
from pathlib import Path

from actions_policy_audit import audit


class AuditTests(unittest.TestCase):
    def make_repo(self, workflow: str) -> Path:
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        root = Path(temp.name)
        directory = root / ".github" / "workflows"
        directory.mkdir(parents=True)
        (directory / "ci.yml").write_text(workflow, encoding="utf-8")
        return root

    def test_reports_mutable_action_and_missing_bounds(self):
        result = audit(self.make_repo("name: CI\non: [push]\njobs:\n  test:\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@v4\n"))
        rules = {item["rule"] for item in result["findings"]}
        self.assertEqual(result["files_scanned"], 1)
        self.assertTrue({"explicit-permissions", "job-timeout", "immutable-action"}.issubset(rules))

    def test_accepts_bounded_sha_pinned_workflow(self):
        sha = "a" * 40
        workflow = f"name: CI\non: [push]\npermissions:\n  contents: read\njobs:\n  test:\n    timeout-minutes: 10\n    runs-on: ubuntu-latest\n    steps:\n      - uses: actions/checkout@{sha}\n"
        result = audit(self.make_repo(workflow))
        self.assertEqual(result["findings"], [])

    def test_reports_artifact_retention(self):
        sha = "b" * 40
        workflow = f"permissions: read-all\njobs:\n  build:\n    timeout-minutes: 5\n    steps:\n      - uses: actions/upload-artifact@{sha}\n"
        result = audit(self.make_repo(workflow))
        self.assertEqual([item["rule"] for item in result["findings"]], ["artifact-retention"])

    def test_composite_action_metadata_keeps_inputs_out_of_shell_source(self):
        metadata = (Path(__file__).resolve().parents[1] / "action.yml").read_text(encoding="utf-8")
        self.assertIn('using: "composite"', metadata)
        self.assertIn('AUDIT_TARGET: ${{ inputs.path }}', metadata)
        self.assertIn('AUDIT_FORMAT: ${{ inputs.format }}', metadata)
        self.assertIn('AUDIT_FAIL_ON: ${{ inputs.fail-on }}', metadata)
        self.assertIn('"$AUDIT_TARGET"', metadata)
        self.assertNotIn('python3 ${{ inputs.', metadata)

    def test_publication_assets_describe_bounded_offline_probe(self):
        product_root = Path(__file__).resolve().parents[1]
        readme_path = product_root / "PUBLIC_README.md"
        if not readme_path.exists():
            readme_path = product_root / "README.md"
        readme = readme_path.read_text(encoding="utf-8")
        license_text = (product_root / "LICENSE").read_text(encoding="utf-8")
        self.assertIn("offline preflight", readme)
        self.assertIn("no SLA", readme)
        self.assertIn("Does not transmit", readme)
        self.assertIn("MIT License", license_text)


if __name__ == "__main__":
    unittest.main()
