
import FreeCAD,FreeCADGui

class DiamondCommand:
    """Cread a rows of diamonds in a sketch"""

    def GetResources(self):
        # Add pixmap some time 'Pixmap'  : 'My_Command_Icon
        return {'MenuText': "Create Diamonds",
                'ToolTip' : "Create a Sketch of connected diamonds"}

    def Activated(self):
        FreeCAD.Console.PrintMessage("Hello there")

        return

    def IsActive(self):
        """If there is no active document we can't add a sketch to it."""
        return not FreeCAD.ActiveDocument is None

FreeCADGui.addCommand('Diamond_Sketch', DiamondCommand()) 