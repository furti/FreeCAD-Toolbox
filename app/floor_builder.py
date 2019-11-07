import FreeCAD
import Arch

class FloorBuilder:
    def __init__(self, obj, base):
        obj.Proxy = self
        self.setupProperties(obj)

        obj.Base = base
        
    def setupProperties(self, obj):
        pl = obj.PropertiesList

        if not "Base" in pl:
            obj.addProperty("App::PropertyLink",   "Base",
                "FloorBuilder", "Base profile for the floor")
        if not "Slabs" in pl:
            obj.addProperty("App::PropertyLinkList",   "Slabs",
                "FloorBuilder", "List of generated slabs")
        if not "NumberOfSlabs" in pl:
            obj.addProperty("App::PropertyInteger",   "NumberOfSlabs",
                "FloorBuilder", "Number of slabs to generate")
            obj.NumberOfSlabs = 1
        
    def execute(self, obj):
        numberOfSlabs = len(obj.Slabs)

        if numberOfSlabs < 2:
            return

        for i in range(numberOfSlabs - 1):
            actualSlab = obj.Slabs[i]
            nextSlab = obj.Slabs[i+1]

            correctZ = actualSlab.Placement.Base.z + actualSlab.Height.Value

            if nextSlab.Placement.Base.z != correctZ:
                nextSlab.Placement.Base.z = correctZ

    def onChanged(self, obj, prop):
        if prop == "NumberOfSlabs":
            self.adjustSlabCount(obj)
        elif prop == "Base":
            self.updateBase(obj)

    def onDocumentRestored(self,obj):
        self.setupProperties(obj)

    def adjustSlabCount(self, obj):
        newNumberOfSlabs = obj.NumberOfSlabs
        actualNumberOfSlabs = len(obj.Slabs)
        
        if newNumberOfSlabs == actualNumberOfSlabs:
            return
        
        if newNumberOfSlabs < actualNumberOfSlabs:
            obj.Slabs = obj.Slabs[:newNumberOfSlabs]
        else:
            numberOfMissingElements = newNumberOfSlabs - actualNumberOfSlabs
            slabs = obj.Slabs

            for i in range(numberOfMissingElements):
                slabs.append(Arch.makeStructure(obj.Base))

            obj.Slabs = slabs
        
    def updateBase(self, obj):
        for slab in obj.Slabs:
            slab.Base = obj.Base