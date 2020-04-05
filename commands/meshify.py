import FreeCAD
import FreeCADGui
import Part


class MeshifyCommand:
    toolbarName = 'Arch_Tools'
    commandName = 'Meshify'

    def GetResources(self):
        return {'MenuText': "Meshify",
                'ToolTip': "Creates a cleaned up mesh of the selected shape",
                # 'Pixmap': iconPath('CreateConfig.svg')
                }

    def Activated(self):
        selection = FreeCADGui.Selection.getSelection()

        if len(selection) == 0:
            return
        
        shape = selection[0].Shape.copy()
        shape = shape.removeSplitter()

        Part.show(shape)

    def IsActive(self):
        """If there is no active document we can't do anything."""
        return not FreeCAD.ActiveDocument is None


if __name__ == "__main__":
    command = MeshifyCommand()

    if command.IsActive():
        command.Activated()
    else:
        qtutils.showInfo("No open Document", "There is no open document")
else:
    from gui import toolbar_manager
    toolbar_manager.toolbarManager.registerCommand(
        MeshifyCommand())
