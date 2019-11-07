from pivy import coin

class ViewProviderFloorBuilder():
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object
        self.coinNode = coin.SoGroup()
        vobj.addDisplayMode(self.coinNode, "Standard")

    def claimChildren(self):
        children = [self.Object.Base]
        children.extend(self.Object.Slabs)

        return children

    def getDisplayModes(self, obj):
        return ["Standard"]

    def getDefaultDisplayMode(self):
        return "Standard"
        
    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None