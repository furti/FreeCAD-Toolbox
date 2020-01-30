import FreeCAD
import FreeCADGui


class AbsoluteTextPositionCommand:
    toolbarName = 'Arch_Tools'
    commandName = 'Absolute_Text_Position'

    def GetResources(self):
        return {'MenuText': "Absolute Text Position",
                'ToolTip': "Sets the Selected Dimensions Text Position to the actual value",
                # 'Pixmap': iconPath('CreateConfig.svg')
                }

    def Activated(self):
        selection = FreeCADGui.Selection.getSelection()

        for dim in selection:
            tbase = dim.ViewObject.Proxy.tbase

            dim.ViewObject.TextPosition = FreeCAD.Vector(tbase)

    def IsActive(self):
        """If there is no active document we can't do anything."""
        return not FreeCAD.ActiveDocument is None


if __name__ == "__main__":
    command = AbsoluteTextPositionCommand()

    if command.IsActive():
        command.Activated()
    else:
        qtutils.showInfo("No open Document", "There is no open document")
else:
    from gui import toolbar_manager
    toolbar_manager.toolbarManager.registerCommand(
        AbsoluteTextPositionCommand())
