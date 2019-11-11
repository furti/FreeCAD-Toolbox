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
    
    def onChanged(self, vobj, prop):
        if prop == 'Visibility':
            self.toggleSlabs(vobj)

    def toggleSlabs(self, vobj):
        floorBuilder = vobj.Object

        if not floorBuilder.Slabs:
            return
        
        for slab in floorBuilder.Slabs:
            if vobj.Visibility:
                slab.ViewObject.show()
            else:
                slab.ViewObject.hide()

    def getDisplayModes(self, obj):
        return ["Standard"]

    def getDefaultDisplayMode(self):
        return "Standard"
        
    def __getstate__(self):
        return None

    def __setstate__(self,state):
        return None