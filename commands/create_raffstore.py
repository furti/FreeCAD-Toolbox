import FreeCAD
import FreeCADGui

from app.raffstore import Raffstore
from gui.raffstore_viewprovider import ViewProviderRaffstore


class CreateRaffstoreCommand:
    toolbarName = 'Arch_Tools'
    commandName = 'Create_Raffstore'

    def GetResources(self):
        return {'MenuText': "Create Raffstore",
                'ToolTip': "Create a new Raffstore object",
                # 'Pixmap': iconPath('CreateConfig.svg')
                }

    def Activated(self):
        base = FreeCADGui.Selection.getSelection()[0]

        createRaffstore(base)

    def IsActive(self):
        """If there is no active document we can't do anything."""
        return not FreeCAD.ActiveDocument is None


def createRaffstore(base):
    obj = FreeCAD.ActiveDocument.addObject("Part::FeaturePython", "Raffstore")
    obj.Label = "Raffstore"

    Raffstore(obj)

    obj.Base = base

    ViewProviderRaffstore(obj.ViewObject)
    base.ViewObject.hide()

    FreeCAD.ActiveDocument.recompute()

    return obj


if __name__ == "__main__":
    command = CreateRaffstoreCommand()

    if command.IsActive():
        command.Activated()
    else:
        qtutils.showInfo("No open Document", "There is no open document")
else:
    from gui import toolbar_manager
    toolbar_manager.toolbarManager.registerCommand(CreateRaffstoreCommand())
