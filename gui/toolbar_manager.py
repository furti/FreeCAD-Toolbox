from collections import OrderedDict
import FreeCAD, FreeCADGui

class ToolbarManager:
    Toolbars =  OrderedDict()

    def registerCommand(self, command):
        FreeCADGui.addCommand(command.commandName, command)
        self.Toolbars.setdefault(command.toolbarName, []).append(command)

toolbarManager = ToolbarManager()

# import commands here
import commands.create_floor_builder
import commands.create_wood_extract
import commands.create_section_plane
import commands.export_section_svg
import commands.include_in_section
import commands.exclude_from_section
import commands.create_raffstore
import commands.meshify
import commands.build_legend