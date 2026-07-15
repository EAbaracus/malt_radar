class FlavorMapper:
    def __init__(self):
        # 7-axis canonical mapping dictionary
        self.mapping = {
            "bonfire": "Smoke",
            "peat": "Smoke",
            "iodine": "Medicinal",
            "seaweed": "Medicinal",
            "apple": "Fruity",
            "raisin": "Fruity",
            "vanilla": "Sweetness",
            "honey": "Sweetness",
            "cinnamon": "Spicy",
            "clove": "Spicy",
            "heather": "Floral",
            "oak": "Woody"
        }
        
    def get_axis(self, descriptor):
        return self.mapping.get(descriptor.lower().strip())
