"""Prevent noisy validation regressions without disabling real CI checks."""
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


class ValidationWorkflowTests(unittest.TestCase):
    def test_pr_runs_cancel_superseded_revisions(self):
        text = (ROOT / ".github/workflows/validation.yml").read_text()
        self.assertIn("pull_request:", text)
        self.assertIn("workflow_call:", text)
        self.assertIn("workflow_dispatch:", text)
        self.assertIn("concurrency:", text)
        self.assertIn("cancel-in-progress: ${{ github.event_name == 'pull_request' }}", text)

    def test_main_release_is_the_single_validation_pipeline(self):
        validation = (ROOT / ".github/workflows/validation.yml").read_text()
        release = (ROOT / ".github/workflows/release.yml").read_text()
        # Release invokes the same validator, so no second standalone main run.
        self.assertNotIn("\n  push:\n    branches: [main]", validation)
        self.assertIn("uses: ./.github/workflows/validation.yml", release)
        self.assertIn("needs: validate", release)
        for required in ("ruff check", "unittest discover", "pytest tests/ha",
                         "npm test", "hassfest@master", "hacs/action@main"):
            self.assertIn(required, validation)


if __name__ == "__main__":
    unittest.main()
