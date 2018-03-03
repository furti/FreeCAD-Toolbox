class ToolboxWorkbench (Workbench):
    "Collection of different useful tools for FreeCAD"

    def __init__(self):
        # TODO: Add icon self.__class__.Icon = "path/to/icon"
        self.__class__.MenuText = "Toolbox"
        self.__class__.ToolTip = "Collection of useful Tools"

    def Initialize(self):
        # Initialize the module
        import ToolboxSketchTools

        self.sketchTools = ToolboxSketchTools.tools

        self.appendToolbar("Sketcher Tools", self.sketchTools)

#    def Activated(self):

#   def Deactivated(self):

Gui.addWorkbench(ToolboxWorkbench())