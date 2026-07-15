class AmbiguityHandler:
    def __init__(self):
        self.ambiguous_queue = []
        
    def check_and_queue(self, descriptor, source_fact_id):
        # Detect broad/unmappable terms
        unmappable = ["rich", "complex", "smooth", "balanced", "intense"]
        desc_lower = descriptor.lower().strip()
        if desc_lower in unmappable:
            self.ambiguous_queue.append({
                "descriptor": descriptor,
                "source_fact_id": source_fact_id,
                "reason": "Vague or subjective intensity modifier."
            })
            return True
        return False
