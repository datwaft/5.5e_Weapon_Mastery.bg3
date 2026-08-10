from __future__ import annotations

import subprocess
import sys
import tempfile
import unittest
from pathlib import Path


REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
CHECKER = REPOSITORY_ROOT / "tools" / "check_osiris_database_types.py"
SIGNATURES = REPOSITORY_ROOT / "tools" / "osiris-signatures.json"
NICK_GOAL = (
    REPOSITORY_ROOT
    / "Mods"
    / "WeaponMastery_7a1a5ee1-3060-4c0a-a896-6833734c6617"
    / "Story"
    / "RawFiles"
    / "Goals"
    / "WM55_Nick.txt"
)


def run_checker(goal: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, str(CHECKER), "--signatures", str(SIGNATURES), str(goal)],
        check=False,
        capture_output=True,
        text=True,
    )


class OsirisDatabaseTypeTests(unittest.TestCase):
    def test_current_nick_goal_is_valid(self) -> None:
        result = run_checker(NICK_GOAL)

        self.assertEqual(result.returncode, 0, result.stderr)

    def test_previous_guidstring_character_mismatch_is_rejected(self) -> None:
        source = NICK_GOAL.read_text(encoding="utf-8")
        invalid_source = (
            source.replace("UsingSpell((CHARACTER)_Caster", "UsingSpell(_Caster")
            .replace("StatusApplied((CHARACTER)_Caster", "StatusApplied(_Caster")
            .replace("AttackedBy(_, (CHARACTER)_AttackOwner", "AttackedBy(_, _AttackOwner")
            .replace("CastedSpell((CHARACTER)_Caster", "CastedSpell(_Caster")
            .replace("TurnStarted((CHARACTER)_Caster", "TurnStarted(_Caster")
        )

        with tempfile.TemporaryDirectory() as temporary_directory:
            invalid_goal = Path(temporary_directory) / "WM55_Nick.txt"
            invalid_goal.write_text(invalid_source, encoding="utf-8")
            result = run_checker(invalid_goal)

        self.assertEqual(result.returncode, 1)
        self.assertIn("expects CHARACTER; GUIDSTRING specified", result.stderr)


if __name__ == "__main__":
    unittest.main()
