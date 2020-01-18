import FreeCAD
from pivy import coin


class ViewProviderSimpleSectionPlane():
    def __init__(self, vobj):
        vobj.Proxy = self

    def attach(self, vobj):
        self.ViewObject = vobj
        self.Object = vobj.Object

        self.coinNode = coin.SoGroup()
        self.material = coin.SoMaterial()
        self.material.transparency.setValue(0.7)
        self.material.diffuseColor.setValue([0.66, 0, 0.5])

        self.plane_coords = coin.SoCoordinate3()
        self.updatePlaneCoordinates(vobj)

        fs = coin.SoIndexedFaceSet()
        fs.coordIndex.setValues(0, 7, [0, 1, 2, -1, 0, 2, 3])
        # self.drawstyle = coin.SoDrawStyle()
        # self.drawstyle.style = coin.SoDrawStyle.LINES

        sep = coin.SoSeparator()

        sep.addChild(self.plane_coords)
        sep.addChild(self.material)
        sep.addChild(fs)

        self.coinNode.addChild(sep)

        vobj.addDisplayMode(self.coinNode, "Standard")

    def onChanged(self, vobj, prop):
        pass

    def updateData(self, obj, prop):
        if prop == "Placement":
            self.updatePlaneCoordinates(obj.ViewObject)
        elif prop in ["PlaneLength", "PlaneHeight"]:
            self.updatePlaneCoordinates(obj.ViewObject)

    def updatePlaneCoordinates(self, vobj):
        obj = vobj.Object
        
        plane_length = 100000
        plane_height = 100000

        if hasattr(obj, "PlaneLength") and obj.PlaneLength.Value > 0:
            plane_length = obj.PlaneLength.Value
        
        if hasattr(obj, "PlaneHeight") and obj.PlaneHeight.Value > 0:
            plane_height = obj.PlaneHeight.Value

        r = obj.Placement
        p1 = FreeCAD.Vector(-plane_length, -plane_height, 0)
        p2 = FreeCAD.Vector(plane_length, -plane_height, 0)
        p3 = FreeCAD.Vector(plane_length, plane_height, 0)
        p4 = FreeCAD.Vector(-plane_length, plane_height, 0)

        verts = []
        verts.append([p1.x, p1.y, 0])
        verts.append([p2.x, p2.y, 0])
        verts.append([p3.x, p3.y, 0])
        verts.append([p4.x, p4.y, 0])

        self.plane_coords.point.setValues(verts)

    def getDisplayModes(self, obj):
        return ["Standard"]

    def getDefaultDisplayMode(self):
        return "Standard"

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None


if __name__ == "__main__":
    from app.section_plane import SimpleSectionPlane

    if FreeCAD.ActiveDocument is None:
        print('Create a document to continue.')
    else:
        simpleSectionPlaneObject = FreeCAD.ActiveDocument.addObject(
            "App::FeaturePython", "SectionPlane")
        SimpleSectionPlane(simpleSectionPlaneObject)
        ViewProviderSimpleSectionPlane(simpleSectionPlaneObject.ViewObject)

        # simpleSectionPlaneObject.IncludeObjects = [
        #     FreeCAD.ActiveDocument.Wall003]
        # simpleSectionPlaneObject.IncludeObjects = [
        #     FreeCAD.ActiveDocument.BuildingPart]

        simpleSectionPlaneObject.Placement = FreeCAD.Placement(
            FreeCAD.Vector(0, 0, 1000), FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 0))

        FreeCAD.ActiveDocument.recompute()
