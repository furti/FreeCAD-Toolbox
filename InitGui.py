import FreeCAD
import FreeCADGui

class ToolboxWorkbench (FreeCADGui.Workbench):
    "Collection of different useful tools for FreeCAD"
    
    MenuText = "Toolbox"
    ToolTip = "Collection of useful Tools"
        # TODO: Add icon self.__class__.Icon = "path/to/icon"        

    def Initialize(self):
        # Initialize the module
        import gui.toolbar_manager as toolbar_manager

        for name,commands in toolbar_manager.toolbarManager.Toolbars.items():
            self.appendToolbar(name,[command.commandName for command in commands])

#    def Activated(self):

#   def Deactivated(self):

FreeCADGui.addWorkbench(ToolboxWorkbench())