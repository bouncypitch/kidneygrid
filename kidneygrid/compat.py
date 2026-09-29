"""Donor-patient compatibility: ABO blood type plus virtual crossmatch.

Simplified for demonstration. Real programs also weigh antibody strength (MFI),
donor age/size and logistics; those would run as additional local checks.
"""

from collections.abc import Iterable

# Donor blood type -> patient blood types that can receive it.
ABO_COMPAT: dict[str, frozenset[str]] = {
    "O": frozenset({"O", "A", "B", "AB"}),
    "A": frozenset({"A", "AB"}),
    "B": frozenset({"B", "AB"}),
    "AB": frozenset({"AB"}),
}


def abo_compatible(donor_abo: str, patient_abo: str) -> bool:
    return patient_abo in ABO_COMPAT[donor_abo]


def crossmatch_conflicts(donor_hla: Iterable[str], unacceptable: Iterable[str]) -> set[str]:
    """Donor HLA antigens the patient has antibodies against (virtual crossmatch)."""
    return set(donor_hla) & set(unacceptable)


def incompatibility_reason(donor: dict, patient: dict) -> str | None:
    """Return why `donor` cannot give to `patient`, or None if compatible.

    `donor` needs `abo` and `hla`; `patient` needs `abo` and `unacceptable`.
    """
    if not abo_compatible(donor["abo"], patient["abo"]):
        return f"blood type {donor['abo']}->{patient['abo']}"
    conflicts = crossmatch_conflicts(donor["hla"], patient["unacceptable"])
    if conflicts:
        return "positive crossmatch (" + ", ".join(sorted(conflicts)) + ")"
    return None


def is_compatible(donor: dict, patient: dict) -> bool:
    return incompatibility_reason(donor, patient) is None
