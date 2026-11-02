# RUN: %{python} %s
#
# END.


import os
import tempfile
import unittest
from unittest import mock

from lit.llvm.subst import FindTool


class _LitConfig(object):
    def __init__(self, params):
        self.params = params


class _Config(object):
    def __init__(self, params=None):
        self.lit_config = _LitConfig(params or {})


class TestFindToolMachineVerifier(unittest.TestCase):
    """LLVM_ENABLE_MACHINE_VERIFIER is documented in llvm/docs/TestingGuide.rst."""

    @classmethod
    def setUpClass(cls):
        cls.tmpdir = tempfile.TemporaryDirectory()
        cls.dir = cls.tmpdir.name
        # lit.util.which only checks for existence; ".exe" covers PATHEXT on
        # Windows.
        for name in ("llc", "llc.exe", "opt", "opt.exe"):
            with open(os.path.join(cls.dir, name), "w"):
                pass

    @classmethod
    def tearDownClass(cls):
        cls.tmpdir.cleanup()

    def resolve(self, name, env, params=None):
        with mock.patch.dict(os.environ, env, clear=False):
            if "LLVM_ENABLE_MACHINE_VERIFIER" not in env:
                os.environ.pop("LLVM_ENABLE_MACHINE_VERIFIER", None)
            return FindTool(name).resolve(_Config(params), self.dir)

    def test_unset_leaves_llc_unchanged(self):
        command = self.resolve("llc", {})
        self.assertIsNotNone(command)
        self.assertNotIn("-verify-machineinstrs", command)

    def test_set_to_one_appends_verifier_to_llc(self):
        command = self.resolve("llc", {"LLVM_ENABLE_MACHINE_VERIFIER": "1"})
        self.assertTrue(command.endswith(" -verify-machineinstrs"))

    def test_other_values_have_no_effect(self):
        for value in ("0", "ON", "true", ""):
            command = self.resolve("llc", {"LLVM_ENABLE_MACHINE_VERIFIER": value})
            self.assertNotIn("-verify-machineinstrs", command, value)

    def test_only_llc_is_affected(self):
        command = self.resolve("opt", {"LLVM_ENABLE_MACHINE_VERIFIER": "1"})
        self.assertNotIn("-verify-machineinstrs", command)

    def test_applies_to_dllc_override(self):
        command = self.resolve(
            "llc",
            {"LLVM_ENABLE_MACHINE_VERIFIER": "1"},
            params={"llc": "my-llc -O0"},
        )
        self.assertEqual(command, "my-llc -O0 -verify-machineinstrs")


if __name__ == "__main__":
    unittest.main()
