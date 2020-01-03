import FreeCAD
import FreeCADGui

from app.section_plane import SimpleSectionPlane
from gui.section_plane_viewprovider import ViewProviderSimpleSectionPlane


class CreateSectionPlaneCommand:
    toolbarName = 'Arch_Tools'
    commandName = 'Create_Section_Plane'

    def GetResources(self):
        return {'MenuText': "Create Section Plane",
                'ToolTip': "Create a new SectionPlane object",
                # 'Pixmap': iconPath('CreateConfig.svg')
                }

    def Activated(self):
        section_plane = FreeCADGui.Selection.getSelection()[0]
        target = section_plane.TargetFile
        scale = section_plane.Scale

        svg = section_plane.Proxy.getSvg(scale=scale)

        file_object = open(target, "w")
        file_object.write(svg)
        file_object.close()

        print("SVG Written to %s" % (target, ))

    def IsActive(self):
        """If there is no active document we can't do anything."""
        return not FreeCAD.ActiveDocument is None


def createSectionPlane():
    obj = FreeCAD.ActiveDocument.addObject(
        "Part::FeaturePython", "SectionPlane")
    obj.Label = "SectionPlane"

    SimpleSectionPlane(obj)

    ViewProviderSimpleSectionPlane(obj.ViewObject)

    FreeCAD.ActiveDocument.recompute()

    return obj


if __name__ == "__main__":
    command = CreateSectionPlaneCommand()

    if command.IsActive():
        command.Activated()
    else:
        qtutils.showInfo("No open Document", "There is no open document")
else:
    from gui import toolbar_manager
    toolbar_manager.toolbarManager.registerCommand(CreateSectionPlaneCommand())
