"""Manifest-only packaging tests; every fixture is explicitly synthetic."""
from pathlib import Path
import shutil
import tempfile
import unittest

from build_runtime import (COMMON_FILES, EXECUTION_FILES, build, package_frozen, required_inputs,
                           validate_complete)
from runtime import canonical, native, read_json, save, save_bytes, sha
from test_runner import scope, stages


def fixture(root):
    here=Path(__file__).resolve().parent
    for name in EXECUTION_FILES:
        target=root/"execution-001"/name
        target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((here/name).read_bytes())
    for name in COMMON_FILES:
        target=root/name;target.parent.mkdir(parents=True,exist_ok=True)
        target.write_bytes((here.parent/name).read_bytes())
    save_bytes(root/"pilot/renderer.py",b"# SYNTHETIC IMPORT ONLY\n")
    save(root/"pilot/template.json",{"synthetic":True})
    config=scope()
    from test_allocation import binding_fixture
    binding_fixture(root,config,stage_external=False)
    config.update(renderer="pilot/renderer.py",runtime_inputs=["pilot/template.json"])
    for project in ("stdlib","aws"):
        config["projects"][project]={"stages":{}}
    for (project,number),stage in stages().items():
        prefix="inputs/"+project+"/"+str(number)
        stage.native_profile.pop("synthetic")
        save(root/(prefix+"/edit.json"),stage.edit_profile)
        save(root/(prefix+"/native.json"),stage.native_profile)
        bases={}
        for name,data in stage.base_sources.items():
            source_path=prefix+"/sources/"+name
            save_bytes(root/source_path,data)
            bases[name]={"path":source_path,"sha256":sha(data)}
        config["projects"][project]["stages"][str(number)]=dict(
            edit_profile=prefix+"/edit.json",native_profile=prefix+"/native.json",
            base_sources=bases,native_adapter=stage.adapter)
    save(root/"pilot/scope.json",config)
    return config


class BuildTests(unittest.TestCase):
    def test_manifest_only_package_has_all_direct_inputs(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/"source"; root.mkdir();config=fixture(root)
            manifest=root/"execution-001/runtime-freeze.json"
            value=build(root,"pilot/scope.json",manifest)
            self.assertTrue(required_inputs(config,"pilot/scope.json") <= set(value["files"]))
            save_bytes(root/"unlisted-private-looking-file",b"THIS IS NOT A REAL SECRET")
            destination=Path(tmp)/"isolated"
            result=package_frozen(root,manifest,sha(manifest.read_bytes()),destination)
            self.assertEqual(result,value)
            self.assertFalse((destination/"unlisted-private-looking-file").exists())
            validate_complete(destination,"pilot/scope.json",destination/"execution-001/runtime-freeze.json",
                              sha(manifest.read_bytes()))

    def test_native_profile_and_renderer_drift_block_package(self):
        for path in ("inputs/stdlib/1/native.json","pilot/renderer.py","common/guard.py"):
            with self.subTest(path=path),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp)/"source";root.mkdir();fixture(root)
                manifest=root/"execution-001/runtime-freeze.json"
                build(root,"pilot/scope.json",manifest)
                (root/path).write_bytes((root/path).read_bytes()+b" ")
                with self.assertRaises(native.EvidenceError):
                    package_frozen(root,manifest,sha(manifest.read_bytes()),Path(tmp)/"out")

    def test_missing_input_pin_is_rejected_even_when_manifest_hash_matches(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixture(root)
            manifest=root/"execution-001/runtime-freeze.json"
            value=build(root,"pilot/scope.json",manifest)
            value["files"].pop("common/guard.py")
            manifest.write_bytes(canonical(value))
            with self.assertRaisesRegex(native.EvidenceError,"omits"):
                validate_complete(root,"pilot/scope.json",manifest,sha(manifest.read_bytes()))

    def test_symlink_input_cannot_be_packaged(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);fixture(root)
            (root/"pilot/renderer.py").unlink()
            (root/"pilot/renderer.py").symlink_to(root/"pilot/template.json")
            with self.assertRaises(native.EvidenceError):
                build(root,"pilot/scope.json",root/"execution-001/runtime-freeze.json")

    def test_pending_native_profile_and_stale_base_are_not_live_ready(self):
        for mutation in ("pending","source"):
            with self.subTest(mutation=mutation),tempfile.TemporaryDirectory() as tmp:
                root=Path(tmp);fixture(root)
                if mutation=="pending":
                    path=root/"inputs/stdlib/1/native.json"
                    profile=read_json(path);profile["inventory_status"]="pending";path.write_bytes(canonical(profile))
                else:
                    (root/"inputs/aws/1/sources/Base.dfy").write_bytes(b"stale")
                with self.assertRaises(native.EvidenceError):
                    build(root,"pilot/scope.json",root/"execution-001/runtime-freeze.json")


if __name__=="__main__":
    unittest.main(verbosity=2)

