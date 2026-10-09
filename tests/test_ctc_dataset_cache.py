import zipfile

from ai4s_io import (
    CTC_PHC_C2DL_PSC_URL,
    PHC_C2DL_PSC_VOXEL_SIZE_UM,
    ensure_ctc_phc_psc_dataset,
)


def test_phc_dataset_adapter_extracts_cached_training_archive(tmp_path):
    archive = tmp_path / "PhC-C2DL-PSC.zip"
    with zipfile.ZipFile(archive, "w") as zf:
        zf.writestr("PhC-C2DL-PSC/fixture.txt", "cache fixture")

    dataset = ensure_ctc_phc_psc_dataset(tmp_path)

    assert dataset == tmp_path / "dataset" / "PhC-C2DL-PSC"
    assert (dataset / "fixture.txt").read_text() == "cache fixture"


def test_phc_dataset_metadata_is_explicit():
    assert CTC_PHC_C2DL_PSC_URL.endswith("/PhC-C2DL-PSC.zip")
    assert PHC_C2DL_PSC_VOXEL_SIZE_UM == (1.0, 1.6, 1.6)
