import FreeCAD
import FreeCADGui

from app.wood_extract import WoodExtract
from gui.wood_extract_viewprovider import ViewProviderWoodExtract

class CreateWoodExtractCommand:
    toolbarName = 'Lumber_Tools'
    commandName = 'Create_Wood_Extract'

    def GetResources(self):
        return {'MenuText': "Create Wood Extract",
                'ToolTip' : "Create a new WoodExtract object",
                #'Pixmap': iconPath('CreateConfig.svg')
                }

    def Activated(self):
        createWoodExtract() 

    def IsActive(self):
        """If there is no active document we can't do anything."""
        return not FreeCAD.ActiveDocument is None

def createLumberSheet():
    lumber = FreeCAD.ActiveDocument.addObject("Spreadsheet::Sheet", "Lumber")
    
    lumber.set('A1', 'Name')
    lumber.set('B1', 'Width')
    lumber.set('C1', 'Height')
    lumber.set('D1', 'Overall Length')

    lumber.setStyle('A1:D1', 'bold', 'add')

    return lumber

def createLogsSheet():
    logs = FreeCAD.ActiveDocument.addObject("Spreadsheet::Sheet", "Logs")
    
    logs.set('A1', 'Diameter')
    logs.set('B1', 'Length')
    logs.set('C1', 'Amount')
    logs.set('E1', 'Delta')

    logs.setStyle('A1:E1', 'bold', 'add')

    return logs

def createWoodExtract():
    import Spreadsheet
    import Sketcher

    woodExtractObject = FreeCAD.ActiveDocument.addObject(
        "App::FeaturePython", "WoodExtract")
    woodExtract = WoodExtract(woodExtractObject)

    woodExtractObject.Lumber = createLumberSheet()
    woodExtractObject.Logs = createLogsSheet()

    ViewProviderWoodExtract(woodExtractObject.ViewObject)

    FreeCAD.ActiveDocument.recompute()

    return woodExtractObject

if __name__ == "__main__":
    command = CreateWoodExtractCommand();
    
    if command.IsActive():
        command.Activated()
    else:
        qtutils.showInfo("No open Document", "There is no open document")
else:
    from gui import toolbar_manager
    toolbar_manager.toolbarManager.registerCommand(CreateWoodExtractCommand()) 