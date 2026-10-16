"""Checks of the dataset: it must contain exactly the study's material.
No model call, no Docker: run with  python -m pytest -q inspect_eval/tests/test_dataset.py"""
import json

from dataset import STUDY_DATA, assure_dataset, load_service

# Number of seeded faults per service, as reported in the paper (Table of services).
EXPECTED_FAULTS = {"casestudy_v2": 14, "svc_mistral": 17, "svc_qwen": 15}

# A transcript of the main campaign per service: the Phase A prompt sent to the
# verifier contains the specification the models actually saw.
TRANSCRIPTS = {
    "casestudy_v2": "casestudy_v2/casestudy_docpay-v2",
    "svc_mistral": "svc_mistral/service_mistral-rooms",
    "svc_qwen": "svc_qwen/service_qwen-loans",
}


def test_three_samples_and_46_faults():
    """One sample per service, and the fault counts of the paper."""
    samples = list(assure_dataset())
    assert {s.id: len(s.target) for s in samples} == EXPECTED_FAULTS
    assert sum(len(s.target) for s in samples) == 46


def test_every_fault_is_a_real_edit_of_the_reference():
    """Each faulty program differs from the reference (the patch was applied)."""
    for benchmark in EXPECTED_FAULTS:
        service = load_service(benchmark)
        for fault_id, fault in service["faults"].items():
            assert fault["program"] != service["reference"], fault_id


def test_no_ground_truth_in_the_sample():
    """The sample carries S only: no reference code, no hidden test, no author note."""
    for sample in assure_dataset():
        service = load_service(sample.id)
        assert "<!--" not in sample.input
        assert service["reference"] not in sample.input
        assert "def test" not in sample.input
        assert "program" not in json.dumps(sample.metadata)


def test_spec_is_the_one_the_models_saw():
    """S in the dataset is byte-identical to S in the Phase A prompt of the main campaign."""
    for benchmark, unit in TRANSCRIPTS.items():
        path = STUDY_DATA.parent / "results" / "main_casestudy" / "units" / unit / "run0.transcript.json"
        calls = json.loads(path.read_text(encoding="utf-8"))
        phase_a = next(c for c in calls if c["condition"] == "A" and c["phase"] == "A")
        assert load_service(benchmark)["spec"] in phase_a["prompt"], benchmark
