import json
from flavor_mapper import FlavorMapper
from ambiguity_handler import AmbiguityHandler
from axis_reducer import AxisReducer

class D4Orchestrator:
    def __init__(self):
        self.mapper = FlavorMapper()
        self.ambiguity = AmbiguityHandler()
        self.reducer = AxisReducer(self.mapper, self.ambiguity)
        
    def process(self, staging_inputs):
        vectors_output = []
        stats = {"total_descriptors": 0, "mapped_successfully": 0, "ambiguous_queued": 0}
        
        for entity_data in staging_inputs:
            e_id = entity_data["entity_id"]
            descriptors = entity_data["consensus_descriptors"]
            
            stats["total_descriptors"] += len(descriptors)
            
            result, mapped = self.reducer.reduce_entity_flavor(e_id, descriptors)
            vectors_output.append(result)
            stats["mapped_successfully"] += mapped
            
        stats["ambiguous_queued"] = len(self.ambiguity.ambiguous_queue)
        return vectors_output, self.ambiguity.ambiguous_queue, stats
