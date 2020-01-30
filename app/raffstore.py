import FreeCAD
import Part

Z_ROTATION = FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 90)
UEBERLAGER_HEIGHT = 70


class Raffstore:
    def __init__(self, obj):
        obj.Proxy = self

        self.Parts = ["", "", "", ""]

        self.setupProperties(obj)

    def setupProperties(self, obj):
        pl = obj.PropertiesList

        if not "Base" in pl:
            obj.addProperty("App::PropertyLink",   "Base",
                            "Raffstore", "The outer edge of the raffstore")
        if not "RaffstoreWidth" in pl:
            obj.addProperty("App::PropertyDistance",   "RaffstoreWidth",
                            "Raffstore", "The width of the raffstore")
            obj.RaffstoreWidth = 165
        if not "RaffstoreHeight" in pl:
            obj.addProperty("App::PropertyDistance",   "RaffstoreHeight",
                            "Raffstore", "The height of the raffstore")
            obj.RaffstoreHeight = 260
        if not "InsulationThickness" in pl:
            obj.addProperty("App::PropertyDistance",   "InsulationThickness",
                            "Raffstore", "The thickness of the insulation behind the raffstore")
            obj.InsulationThickness = 85
        if not "TopInsulationThickness" in pl:
            obj.addProperty("App::PropertyDistance",   "TopInsulationThickness",
                            "Raffstore", "The thickness of the insulation above the raffstore")
            obj.TopInsulationThickness = 80
        if not "FrontInsulationThickness" in pl:
            obj.addProperty("App::PropertyDistance",   "FrontInsulationThickness",
                            "Raffstore", "The thickness of the insulation in front of the Überleger")
            obj.TopInsulationThickness = 80
        if not "InsulationMaterial" in pl:
            obj.addProperty("App::PropertyLink",   "InsulationMaterial",
                            "Raffstore", "The material for the insulation")
        if not "RaffstoreMaterial" in pl:
            obj.addProperty("App::PropertyLink",   "RaffstoreMaterial",
                            "Raffstore", "The material for the Raffstore")
        
        if len(self.Parts) == 3:
            self.Parts.append("")

        self.Type = "Raffstore"

    def execute(self, obj):
        raffstore = self.buildRaffstore(obj)
        insulationTop = self.buildTopInsulation(obj)
        insulationBack = self.buildBackInsulation(obj)
        insulationFront = self.buildFrontInsulation(obj)

        allParts = [insulationTop, insulationBack]

        if insulationFront:
            allParts.append(insulationFront)

        shape = raffstore.copy().fuse(allParts)
        shape = shape.removeSplitter()
        obj.Shape = shape

        raffstoreObject = self.ensure(0, obj.Label + '_Kasten')
        insulationTopObject = self.ensure(1, obj.Label + '_Daemmung_Oben')
        insulationBackObject = self.ensure(2, obj.Label + '_Daemmung_Hinten')
        insulationFrontObject = None

        raffstoreObject.Shape = raffstore
        insulationTopObject.Shape = insulationTop
        insulationBackObject.Shape = insulationBack

        if insulationFront:
            insulationFrontObject = self.ensure(
                3, obj.Label + '_Daemmung_Ueberleger')
            insulationFrontObject.Shape = insulationFront

        if obj.InsulationMaterial:
            insulationTopObject.Material = obj.InsulationMaterial
            insulationBackObject.Material = obj.InsulationMaterial

            if insulationFrontObject:
                insulationFrontObject.Material = obj.InsulationMaterial

        if obj.RaffstoreMaterial:
            raffstoreObject.Material = obj.RaffstoreMaterial

    def ensure(self, index, name):
        partName = self.Parts[index]
        part = FreeCAD.ActiveDocument.getObject(partName)

        if part is None:
            part = FreeCAD.ActiveDocument.addObject('Part::Feature', name)
            part.addProperty('App::PropertyLink', 'Material')

            self.Parts[index] = part.Name

        part.Label = name

        return part

    def buildRaffstore(self, obj):
        baseNormal = self.getBaseNormal(obj)
        baseEdge = self.getBaseEdge(obj)

        raffstoreWidth = obj.RaffstoreWidth.Value
        raffstoreHeight = obj.RaffstoreHeight.Value

        plane = baseEdge.extrude(baseNormal.multiply(raffstoreWidth))
        extrutionDir = plane.normalAt(0.5, 0.5).negative()

        return plane.extrude(extrutionDir.multiply(raffstoreHeight))

    def buildTopInsulation(self, obj):
        baseNormal = self.getBaseNormal(obj)
        baseEdge = self.getBaseEdge(obj)

        raffstoreWidth = obj.RaffstoreWidth.Value
        raffstoreHeight = obj.RaffstoreHeight.Value
        insulationThickness = obj.TopInsulationThickness.Value

        plane = baseEdge.extrude(baseNormal.multiply(raffstoreWidth))
        extrutionDir = plane.normalAt(0.5, 0.5).negative()

        plane.translate(FreeCAD.Vector(extrutionDir).multiply(raffstoreHeight))

        return plane.extrude(extrutionDir.multiply(insulationThickness))

    def buildBackInsulation(self, obj):
        baseNormal = self.getBaseNormal(obj)
        baseEdge = self.getBaseEdge(obj)

        raffstoreWidth = obj.RaffstoreWidth.Value
        raffstoreHeight = obj.RaffstoreHeight.Value
        insulationThickness = obj.InsulationThickness.Value
        topInsulationThickness = obj.TopInsulationThickness.Value

        baseEdge.translate(FreeCAD.Vector(
            baseNormal).multiply(raffstoreWidth))

        plane = baseEdge.extrude(baseNormal.multiply(insulationThickness))
        extrutionDir = plane.normalAt(0.5, 0.5).negative()

        return plane.extrude(extrutionDir.multiply(topInsulationThickness + raffstoreHeight))

    def buildFrontInsulation(self, obj):
        if not hasattr(obj, "FrontInsulationThickness") or obj.FrontInsulationThickness.Value == 0:
            return None

        baseNormal = self.getBaseNormal(obj)
        baseEdge = self.getBaseEdge(obj)

        raffstoreWidth = obj.RaffstoreWidth.Value
        raffstoreHeight = obj.RaffstoreHeight.Value
        insulationThickness = obj.FrontInsulationThickness.Value
        topInsulationThickness = obj.TopInsulationThickness.Value

        plane = baseEdge.extrude(baseNormal.multiply(insulationThickness))
        extrutionDir = plane.normalAt(0.5, 0.5).negative()

        plane.translate(FreeCAD.Vector(extrutionDir).multiply(raffstoreHeight + topInsulationThickness))

        return plane.extrude(extrutionDir.multiply(UEBERLAGER_HEIGHT))

    def getBaseEdge(self, obj):
        return obj.Base.Shape.Edges[0].copy()

    def getBaseNormal(self, obj):
        base = obj.Base
        direction = base.End - base.Start
        direction.normalize()

        return Z_ROTATION.multVec(direction)

    def onChanged(self, obj, prop):
        pass

    def onDocumentRestored(self, obj):
        self.setupProperties(obj)


if __name__ == "__main__":
    if FreeCAD.ActiveDocument is None:
        print('Create a document to continue.')
    else:
        raffstore = FreeCAD.ActiveDocument.addObject(
            "Part::FeaturePython", "Raffstore")
        Raffstore(raffstore)
        raffstore.Base = FreeCAD.ActiveDocument.Line

        FreeCAD.ActiveDocument.recompute()
