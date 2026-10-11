"""Tests for scripts/validate_skills.py. Run: python3 -m unittest discover -s tests -v"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent / "scripts"))
import validate_skills as vs  # noqa: E402


def skill(name="good-skill", desc="Does a thing. Use when asked.", extra="", body="# Body\n"):
    fm = "---\n"
    if name is not None:
        fm += f"name: {name}\n"
    if desc is not None:
        fm += f'description: "{desc}"\n'
    fm += extra + "---\n"
    return fm + body


class RepoTestCase(unittest.TestCase):
    def setUp(self):
        self._tmp = tempfile.TemporaryDirectory()
        self.repo = Path(self._tmp.name) / "my-repo"
        self.repo.mkdir()

    def tearDown(self):
        self._tmp.cleanup()

    def add(self, rel, text):
        p = self.repo / rel
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(text)
        return p

    def errors_for(self, rel):
        results = vs.validate_repo(self.repo)
        return [r for r in results if r.path == self.repo / rel][0]


class TestValid(RepoTestCase):
    def test_valid_skill_passes(self):
        self.add("good-skill/SKILL.md", skill())
        r = self.errors_for("good-skill/SKILL.md")
        self.assertEqual(r.errors, [])

    def test_folded_multiline_description_passes(self):
        self.add("good-skill/SKILL.md",
                 "---\nname: good-skill\ndescription: >\n  Line one\n  line two.\n---\nbody\n")
        self.assertEqual(self.errors_for("good-skill/SKILL.md").errors, [])

    def test_unknown_field_is_warning_not_error(self):
        self.add("good-skill/SKILL.md", skill(extra="version: 2\n"))
        r = self.errors_for("good-skill/SKILL.md")
        self.assertEqual(r.errors, [])
        self.assertTrue(any("version" in w for w in r.warnings))


class TestNameRules(RepoTestCase):
    def test_folder_mismatch_fails(self):
        self.add("wrong-folder/SKILL.md", skill(name="good-skill"))
        r = self.errors_for("wrong-folder/SKILL.md")
        self.assertTrue(any("folder" in e for e in r.errors), r.errors)

    def test_uppercase_fails(self):
        self.add("Good-Skill/SKILL.md", skill(name="Good-Skill"))
        self.assertTrue(self.errors_for("Good-Skill/SKILL.md").errors)

    def test_consecutive_hyphens_fail(self):
        self.add("good--skill/SKILL.md", skill(name="good--skill"))
        self.assertTrue(self.errors_for("good--skill/SKILL.md").errors)

    def test_leading_hyphen_fails(self):
        self.add("-good/SKILL.md", skill(name="-good"))
        self.assertTrue(self.errors_for("-good/SKILL.md").errors)

    def test_name_over_64_fails(self):
        long = "a" * 65
        self.add(f"{long}/SKILL.md", skill(name=long))
        self.assertTrue(self.errors_for(f"{long}/SKILL.md").errors)

    def test_missing_name_fails(self):
        self.add("good-skill/SKILL.md", skill(name=None))
        r = self.errors_for("good-skill/SKILL.md")
        self.assertTrue(any("name" in e for e in r.errors), r.errors)


class TestDescriptionRules(RepoTestCase):
    def test_missing_description_fails(self):
        self.add("good-skill/SKILL.md", skill(desc=None))
        r = self.errors_for("good-skill/SKILL.md")
        self.assertTrue(any("description" in e for e in r.errors), r.errors)

    def test_empty_description_fails(self):
        self.add("good-skill/SKILL.md", skill(desc=""))
        self.assertTrue(self.errors_for("good-skill/SKILL.md").errors)

    def test_description_over_1024_fails(self):
        self.add("good-skill/SKILL.md", skill(desc="x" * 1025))
        r = self.errors_for("good-skill/SKILL.md")
        self.assertTrue(any("1024" in e for e in r.errors), r.errors)

    def test_description_exactly_1024_passes(self):
        self.add("good-skill/SKILL.md", skill(desc="x" * 1024))
        self.assertEqual(self.errors_for("good-skill/SKILL.md").errors, [])


class TestFrontmatterShape(RepoTestCase):
    def test_no_frontmatter_fails(self):
        self.add("good-skill/SKILL.md", "# Just markdown\n")
        r = self.errors_for("good-skill/SKILL.md")
        self.assertTrue(any("frontmatter" in e for e in r.errors), r.errors)

    def test_unclosed_frontmatter_fails(self):
        self.add("good-skill/SKILL.md", "---\nname: good-skill\ndescription: x\n")
        self.assertTrue(self.errors_for("good-skill/SKILL.md").errors)

    def test_malformed_yaml_fails(self):
        self.add("good-skill/SKILL.md", "---\nname: [unclosed\ndescription: x\n---\n")
        r = self.errors_for("good-skill/SKILL.md")
        self.assertTrue(any("YAML" in e for e in r.errors), r.errors)

    def test_compatibility_over_500_fails(self):
        self.add("good-skill/SKILL.md", skill(extra=f'compatibility: "{"c" * 501}"\n'))
        self.assertTrue(self.errors_for("good-skill/SKILL.md").errors)

    def test_long_body_is_warning(self):
        self.add("good-skill/SKILL.md", skill(body="line\n" * 501))
        r = self.errors_for("good-skill/SKILL.md")
        self.assertEqual(r.errors, [])
        self.assertTrue(any("500" in w for w in r.warnings))


class TestColdCheckRegressions(RepoTestCase):
    """Edge cases found by the double-check panel (2026-10-11)."""

    def test_utf8_bom_is_accepted(self):
        p = self.repo / "good-skill" / "SKILL.md"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"\xef\xbb\xbf" + skill().encode())
        self.assertEqual(self.errors_for("good-skill/SKILL.md").errors, [])

    def test_non_utf8_file_reports_error_not_crash(self):
        p = self.repo / "good-skill" / "SKILL.md"
        p.parent.mkdir(parents=True)
        p.write_bytes(b"---\nname: good-skill\ndescription: \xff\xfe\n---\n")
        r = self.errors_for("good-skill/SKILL.md")
        self.assertTrue(any("UTF-8" in e for e in r.errors), r.errors)

    def test_indented_dashes_in_block_scalar_do_not_close_frontmatter(self):
        text = "---\nname: good-skill\ndescription: |\n  hi\n  ---\n  more\n---\nbody\n"
        fm, body, err = vs.split_frontmatter(text)
        self.assertIsNone(err)
        self.assertIn("more", fm)
        self.assertEqual(body.strip(), "body")

    def test_duplicate_key_fails(self):
        self.add("good-skill/SKILL.md",
                 "---\nname: other\nname: good-skill\ndescription: x\n---\n")
        r = self.errors_for("good-skill/SKILL.md")
        self.assertTrue(any("duplicate" in e for e in r.errors), r.errors)

    def test_non_string_name_fails(self):
        self.add("123/SKILL.md", "---\nname: 123\ndescription: x\n---\n")
        r = self.errors_for("123/SKILL.md")
        self.assertTrue(any("must be a string" in e for e in r.errors), r.errors)

    def test_trailing_hyphen_fails(self):
        self.add("good-/SKILL.md", skill(name="good-"))
        self.assertTrue(self.errors_for("good-/SKILL.md").errors)

    def test_non_mapping_frontmatter_fails(self):
        self.add("good-skill/SKILL.md", "---\n- a\n- b\n---\n")
        r = self.errors_for("good-skill/SKILL.md")
        self.assertTrue(any("mapping" in e for e in r.errors), r.errors)

    def test_empty_frontmatter_fails(self):
        self.add("good-skill/SKILL.md", "---\n---\nbody\n")
        self.assertTrue(self.errors_for("good-skill/SKILL.md").errors)

    def test_whitespace_only_description_fails(self):
        self.add("good-skill/SKILL.md", skill(desc="   "))
        self.assertTrue(self.errors_for("good-skill/SKILL.md").errors)

    def test_non_string_or_empty_compatibility_fails(self):
        for extra in ("compatibility: 5\n", 'compatibility: ""\n'):
            with self.subTest(extra=extra):
                self.add("good-skill/SKILL.md", skill(extra=extra))
                self.assertTrue(self.errors_for("good-skill/SKILL.md").errors)


class TestRootSkillAndInstallMap(RepoTestCase):
    INSTALL = (
        '#!/usr/bin/env bash\nSK="$HOME/.claude/skills"\n'
        'mkdir -p "$SK/root-skill"\ncp "$HERE/SKILL.md" "$SK/root-skill/SKILL.md"\n'
    )

    def test_root_skill_uses_install_sh_target(self):
        self.add("install.sh", self.INSTALL)
        self.add("SKILL.md", skill(name="root-skill"))
        self.assertEqual(self.errors_for("SKILL.md").errors, [])

    def test_root_skill_mismatching_install_target_fails(self):
        self.add("install.sh", self.INSTALL)
        self.add("SKILL.md", skill(name="other-name"))
        r = self.errors_for("SKILL.md")
        self.assertTrue(any("root-skill" in e for e in r.errors), r.errors)

    def test_root_skill_without_install_sh_falls_back_to_repo_dir(self):
        self.add("SKILL.md", skill(name="my-repo"))
        self.assertEqual(self.errors_for("SKILL.md").errors, [])


class TestCli(RepoTestCase):
    def test_exit_codes(self):
        self.add("good-skill/SKILL.md", skill())
        self.assertEqual(vs.main([str(self.repo)]), 0)
        self.add("bad-folder/SKILL.md", skill(name="good-skill"))
        self.assertEqual(vs.main([str(self.repo)]), 1)

    def test_git_dir_ignored(self):
        self.add(".git/hooks/SKILL.md", "garbage")
        self.add("good-skill/SKILL.md", skill())
        paths = [r.path for r in vs.validate_repo(self.repo)]
        self.assertNotIn(self.repo / ".git/hooks/SKILL.md", paths)


if __name__ == "__main__":
    unittest.main()
