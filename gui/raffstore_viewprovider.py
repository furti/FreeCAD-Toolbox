import FreeCAD

raffstoreColor = (0.204, 0.243, 0.259)
insulationColor = (0.486, 0.0, 0.365)


class ViewProviderRaffstore:
    def __init__(self, vobj):
        vobj.Proxy = self

        self.setProperties(vobj)

    def attach(self, vobj):
        self.Object = vobj.Object
        self.setProperties(vobj)

    def setProperties(self, vobj):
        self.ViewObject = vobj

    def updateData(self, obj, prop):
        pass

    def claimChildren(self):
        children = [self.Object.Base]

        return children

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None
