class AxisReducer:
    def __init__(self, mapper, ambiguity_handler):
        self.mapper = mapper
        self.ambiguity_handler = ambiguity_handler
        
    def reduce_entity_flavor(self, entity_id, descriptors_list):
        vectors = {
            "Smoke": 0, "Medicinal": 0, "Fruity": 0, "Sweetness": 0, "Spicy": 0, "Floral": 0, "Woody": 0
        }
        # Mathematical reduction simulation
        mapped_count = 0
        for d in descriptors_list:
            desc = d.get("descriptor")
            intensity = d.get("intensity", 0) # 1-5 scale
            fact_id = d.get("fact_id", "UNKNOWN")
            
            if self.ambiguity_handler.check_and_queue(desc, fact_id):
                continue
                
            axis = self.mapper.get_axis(desc)
            if axis:
                vectors[axis] = min(100, vectors[axis] + (intensity * 20)) # Convert 1-5 to 1-100 scale
                mapped_count += 1
            else:
                self.ambiguity_handler.ambiguous_queue.append({
                    "descriptor": desc,
                    "source_fact_id": fact_id,
                    "reason": "No canonical axis mapping found."
                })
                
        return {"entity_id": entity_id, "canonical_vectors": vectors}, mapped_count
