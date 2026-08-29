"""Explicit, versioned contracts; never infer an unrequested scientific analysis."""

from __future__ import annotations

from dataclasses import dataclass

STEPS = (
    "prepare-data",
    "quality-control",
    "rarefaction-analysis",
    "metataxonomy",
    "diversity-analysis",
    "abundance-analysis",
    "lefse-analysis",
    "picrust2-analysis",
    "ancombc2-analysis",
    "report",
)
TEMPLATES = {step: f"{index:02d}-{step}.ipynb" for index, step in enumerate(STEPS, 1)}


class PlanningError(ValueError):
    def __init__(self, code, message):
        super().__init__(message)
        self.code = code


@dataclass(frozen=True)
class StepContract:
    requires: tuple[str, ...]
    produces: tuple[str, ...]


# Later steps remain deliberately undefined until their scientific migration.
CONTRACTS = {
    "prepare-data": StepContract((), ("demultiplexed_sequences",)),
    "quality-control": StepContract(
        ("demultiplexed_sequences",), ("table", "representative_sequences", "denoising_stats")
    ),
}
EVIDENCE_OUTPUTS = {
    "prepare-data": {"quality_summary": "figures/prepare-data/demultiplexed_sequences.qzv"},
}


def build_plan(parameters):
    selected = parameters["pipeline"]["steps"]
    if len(set(selected)) != len(selected):
        raise PlanningError("duplicate_step", "Steps must be unique")
    for step in selected:
        if step not in CONTRACTS:
            raise PlanningError("unsupported_contract", f"Contract not yet migrated: {step}")
    layout = parameters.get("sequencing", {}).get("read_layout")
    if layout not in ("single-end", "paired-end"):
        raise PlanningError(
            "read_layout", "sequencing.read_layout must be single-end or paired-end"
        )
    types = {
        "demultiplexed_sequences": (
            "SampleData[PairedEndSequencesWithQuality]"
            if layout == "paired-end"
            else "SampleData[SequencesWithQuality]"
        ),
        "table": "FeatureTable[Frequency]",
        "representative_sequences": "FeatureData[Sequence]",
        "denoising_stats": "SampleData[DADA2Stats]",
    }
    external = parameters["inputs"].get("artifacts", {})
    required = {role for step in selected for role in CONTRACTS[step].requires}
    if set(external) - required:
        raise PlanningError(
            "unused_artifact", "An explicit artifact is not consumed by selected steps"
        )
    providers = {}
    for step in selected:
        for role in CONTRACTS[step].produces:
            if role in providers or role in external:
                raise PlanningError("ambiguous_provider", f"Multiple providers for {role}")
            providers[role] = step
    dependencies = {}
    for step in selected:
        dependencies[step] = []
        for role in CONTRACTS[step].requires:
            if role in providers:
                dependencies[step].append(providers[role])
            elif role not in external:
                raise PlanningError("missing_dependency", f"{step} requires {role}")
    ordered = []
    pending = list(selected)
    while pending:
        ready = next((s for s in pending if set(dependencies[s]) <= set(ordered)), None)
        if ready is None:
            raise PlanningError("dependency_cycle", "Selected step contracts contain a cycle")
        ordered.append(ready)
        pending.remove(ready)
    plan = {"contract_version": 2, "requested_steps": list(selected), "steps": []}
    for step in ordered:
        inputs = {}
        for role in CONTRACTS[step].requires:
            if role in external:
                inputs[role] = {"source": "external", "type": types[role], **external[role]}
            else:
                provider = providers[role]
                inputs[role] = {
                    "source": provider,
                    "type": types[role],
                    "path": f"artifacts/{provider}/{role}.qza",
                }
        outputs = {
            role: {"path": f"artifacts/{step}/{role}.qza", "type": types[role]}
            for role in CONTRACTS[step].produces
        }
        plan["steps"].append(
            {
                "id": step,
                "template": TEMPLATES[step],
                "depends_on": dependencies[step],
                "inputs": inputs,
                "outputs": outputs,
                "evidence_outputs": {
                    role: {"path": path} for role, path in EVIDENCE_OUTPUTS.get(step, {}).items()
                },
                "report_contribution": f"reports/contributions/{step}.json",
                "kernel": "python3",
            }
        )
    return plan
