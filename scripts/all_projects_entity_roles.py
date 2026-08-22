"""Entity-role contract for the all-projects registry.

`entity_grain` answers whether a row is a project or a physical building.
`entity_role` answers what kind of public entity the row represents and which
fields are meaningful for its completeness check. Keeping those axes separate
prevents copying a host building's GBA/GLA into an operator site.
"""

ENTITY_ROLES = {"office_project", "coworking_site", "host_building"}
ROLE_DECISION_DATE = "2026-08-22"

ROLE_REQUIRED_FIELDS = {
    "office_project": (
        "address", "latitude", "longitude", "gba", "gla",
        "construction_start_year", "sales_start_year", "input_year",
    ),
    "coworking_site": ("address", "latitude", "longitude", "developer", "canonical_building_id"),
    "host_building": (
        "address", "latitude", "longitude", "cls", "gba", "gla",
        "construction_start_year", "input_year",
    ),
}


def derive_entity_role(source, channels):
    channels = list(channels or [])
    if source == "coworking_host_lookup":
        return "host_building"
    if channels == ["coworking"]:
        return "coworking_site"
    return "office_project"


def role_assignment_note(role):
    return (
        f"entity_role={role} assigned {ROLE_DECISION_DATE}; source: user decision to keep "
        "coworking_site and host_building as distinct public entities; rule: "
        "scripts/all_projects_entity_roles.py."
    )


def role_completeness_issues(record):
    role = record.get("entity_role")
    if role not in ENTITY_ROLES:
        return [f"invalid entity_role: {role!r}"]
    return [
        f"{field} is required for entity_role={role}"
        for field in ROLE_REQUIRED_FIELDS[role]
        if record.get(field) is None or record.get(field) == ""
    ]
