import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class PriceTrackrDatabaseDriverContractTests(unittest.TestCase):
    def test_frontend_database_driver_supports_aiven_postgres(self):
        package = json.loads(
            (ROOT / "apps/pricetrackr/frontend/package.json").read_text(encoding="utf-8")
        )
        source = (
            ROOT / "apps/pricetrackr/frontend/src/lib/db.ts"
        ).read_text(encoding="utf-8")
        deploy_script = (ROOT / "scripts/deploy-all.ps1").read_text(encoding="utf-8")

        self.assertIn("postgres", package["dependencies"])
        self.assertNotIn("@neondatabase/serverless", package["dependencies"])
        self.assertIn("import postgres from 'postgres'", source)
        self.assertNotIn("from '@neondatabase/serverless'", source)
        self.assertIn("process.env.AIVEN_CA_CERT", source)
        self.assertIn("rejectUnauthorized: true", source)
        self.assertIn('Set-VercelEnvVar -ProjectId $project.id -Key "AIVEN_CA_CERT"', deploy_script)
        self.assertIn("/kms/ca", deploy_script)


if __name__ == "__main__":
    unittest.main()
