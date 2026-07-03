"""Entity resolution (Phase 1-2).

Strategy: exact UEI match > normalized-name + postal-code match > flagged
fuzzy candidates for human confirmation. Automated merges only on exact keys;
fuzzy matches become RelationshipEdge(relation="possible_same_entity").
"""


def match_key(normalized_name: str, postal_code: str | None) -> str:
    return f"{normalized_name}|{postal_code or ''}"
