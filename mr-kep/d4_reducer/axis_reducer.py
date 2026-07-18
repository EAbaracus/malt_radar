"""AxisReducer — canonical 7-axis reduction (P95B-FIX-02 corrected).

Emits ONLY the frozen canonical axes:
    smoky, peaty, fruity, sweet, spicy, maritime, sherry   (0-100 scale)

Previous version used a non-canonical vocabulary (Smoke/Medicinal/Fruity/
Sweetness/Spicy/Floral/Woody) and omitted `maritime` — that was a stale stub
and caused maritime loss. This version uses the canonical FlavorMapper and the
canonical axis set, so the d4 orchestrator chain now produces canonical output
consistent with canonical_flavor_standard.md and canonical_vectors.json.
"""
from __future__ import annotations


class AxisReducer:
    def __init__(self, mapper, ambiguity_handler):
        self.mapper = mapper
        self.ambiguity_handler = ambiguity_handler
        # Canonical frozen axes (canonical_flavor_standard.md).
        self.CANONICAL_AXES = ["smoky", "peaty", "fruity", "sweet", "spicy", "maritime", "sherry"]

    def reduce_entity_flavor(self, entity_id, descriptors_list):
        vectors = {ax: 0 for ax in self.CANONICAL_AXES}
        # Mathematical reduction simulation
        mapped_count = 0
        for d in descriptors_list:
            desc = d.get("descriptor")
            intensity = d.get("intensity", 0)  # 1-5 scale
            fact_id = d.get("fact_id", "UNKNOWN")

            if self.ambiguity_handler.check_and_queue(desc, fact_id):
                continue

            axis = self.mapper.get_axis(desc)
            if axis:
                vectors[axis] = min(100, vectors[axis] + (intensity * 20))  # 1-5 -> 1-100
                mapped_count += 1
            else:
                self.ambiguity_handler.ambiguous_queue.append({
                    "descriptor": desc,
                    "source_fact_id": fact_id,
                    "reason": "No canonical axis mapping found.",
                })

        return {"entity_id": entity_id, "canonical_vectors": vectors}, mapped_count
