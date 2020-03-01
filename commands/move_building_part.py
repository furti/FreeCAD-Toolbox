import FreeCAD
import FreeCADGui
import Draft


class AbsoluteTextPositionCommand:
    toolbarName = 'Arch_Tools'
    commandName = 'Move_Building_Part'

    def GetResources(self):
        return {'MenuText': "Move Building Part",
                'ToolTip': "Moves all entries of the selected building part up 10 cm",
                # 'Pixmap': iconPath('CreateConfig.svg')
                }

    def Activated(self):
        addition = FreeCAD.Vector(0, 0, 100)
        buildingPart = FreeCADGui.Selection.getSelection()[0]
        objects = Draft.getGroupContents(
            [buildingPart], walls=True, addgroups=True)

        for o in objects:
            if not hasattr(o, 'Base') or o.Base is None:
                print('object without base %s:%s' % (o.Name, o))
                continue

            base = o.Base

            if not hasattr(base, 'Placement') or base.Placement is None:
                print('base without placement %s:%s' % (o.Name, o))
                continue

            base.Placement.Base = base.Placement.Base.add(addition)

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
