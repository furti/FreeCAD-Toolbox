import FreeCAD
import FreeCADGui

from app.floor_builder import FloorBuilder
from gui.floor_builder_viewprovider import ViewProviderFloorBuilder

class CreateFloorBuilderCommand:
    toolbarName = 'Arch_Tools'
    commandName = 'Create_Floor_Builder'

    def GetResources(self):
        return {'MenuText': "Create Floor Builder",
                'ToolTip' : "Create a new FloorBuilder object",
                #'Pixmap': iconPath('CreateConfig.svg')
                }

    def Activated(self):
        base = FreeCADGui.Selection.getSelection()[0]

        createFloor(base)        

    def IsActive(self):
        """If there is no active document we can't do anything."""
        return not FreeCAD.ActiveDocument is None

def createFloor(base):
    obj= FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Floor")
    obj.Label = "Floor"
    
    FloorBuilder(obj, base)
    ViewProviderFloorBuilder(obj.ViewObject)

    FreeCAD.ActiveDocument.recompute()

    return obj

if __name__ == "__main__":
    command = CreateFloorBuilderCommand();
    
    if command.IsActive():
        command.Activated()
    else:
        qtutils.showInfo("No open Document", "There is no open document")
else:
    from gui import toolbar_manager
    toolbar_manager.toolbarManager.registerCommand(CreateFloorBuilderCommand()) 