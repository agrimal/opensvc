import provisioning

class Prov(provisioning.Prov):
    def __init__(self, r):
        provisioning.Prov.__init__(self, r)
    
    def is_provisioned(self):
        return True

