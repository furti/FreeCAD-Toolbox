import FreeCAD
import FreeCADGui

from app.section_plane import SimpleSectionPlane
from gui.section_plane_viewprovider import ViewProviderSimpleSectionPlane


def select():
    sectionPlane = None
    objects = []

    for o in FreeCADGui.Selection.getSelection():
        if hasattr(o, 'Proxy') and hasattr(o.Proxy, 'Type') and o.Proxy.Type == 'SimpleSectionPlane':
            sectionPlane = o
        else:
            objects.append(o)

    return (sectionPlane, objects)


class ExcludeFromSectionCommand:
    toolbarName = 'Arch_Tools'
    commandName = 'Exclude_From_Section_Svg'

    def GetResources(self):
        return {'MenuText': "Exclude Objects from Section",
                'ToolTip': "Exclude the selected objects from the selected section plane",
                # 'Pixmap': iconPath('CreateConfig.svg')
                }

    def Activated(self):
        section_plane, objects = select()

        excludeFromSection(section_plane, objects)

    def IsActive(self):
        """If there is no active document we can't do anything."""
        return not FreeCAD.ActiveDocument is None


def excludeFromSection(section, objects):
    excludes = []

    excludes.extend(section.ExcludeObjects)
    excludes.extend(objects)

    section.ExcludeObjects = excludes


if __name__ == "__main__":
    command = ExcludeFromSectionCommand()

    if command.IsActive():
        command.Activated()
    else:
        qtutils.showInfo("No open Document", "There is no open document")
else:
    from gui import toolbar_manager
    toolbar_manager.toolbarManager.registerCommand(ExcludeFromSectionCommand())
