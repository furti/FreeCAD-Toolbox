from pivy import coin

class ViewProviderWoodExtract():
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object
        self.coinNode = coin.SoGroup()
        vobj.addDisplayMode(self.coinNode, "Standard")

    def claimChildren(self):
        children = []

        if self.Object.Lumber:
            children.append(self.Object.Lumber)
        
        if self.Object.Logs:
            children.append(self.Object.Logs)
        
        if len(self.Object.Proxy.Sketches) > 0:
            children.extend(self.Object.Proxy.Sketches)
        
        return children
    
    def onChanged(self, vobj, prop):
        pass

    def getDisplayModes(self, obj):
        return ["Standard"]

    def getDefaultDisplayMode(self):
        return "Standard"
        
    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None