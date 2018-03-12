
import FreeCAD,FreeCADGui

import FreeCAD
from PySide import QtGui

def findSelectedBody():
    selection = [o for o in FreeCADGui.Selection.getSelection(FreeCAD.ActiveDocument.Name) if o.TypeId == "PartDesign::Body"]

    if len(selection) == 1:
        return selection[0]
    else:
           QtGui.QMessageBox.information(  QtGui.qApp.activeWindow(), "Selection Error", "Select a single Body to perform the Operation")

           return None

def createSketch(body):
    sketch = body.newObject('Sketcher::SketchObject','Sketch')
    sketch.Support = (FreeCAD.activeDocument().XY_Plane, [''])
    sketch.MapMode = 'FlatFace'
    FreeCAD.ActiveDocument.recompute()

    return sketch

def drawConstructionGeometry(sketch, width, height, columnCount, rowCount):
    halfHeight = height / 2
    halfWidth = width / 2

    # Draw the grid
    gridLines = []
    gridConstraints = []

    rowHeight = height / rowCount
    columnWidth = width / columnCount

    bottomLeft = App.Vector(-columnWidth / 2, -rowHeight / 2, 0)
    topLeft = App.Vector(-columnWidth / 2, rowHeight / 2, 0)
    topRight = App.Vector(columnWidth / 2, rowHeight / 2, 0)
    bottomRight = App.Vector(columnWidth / 2, -rowHeight / 2, 0)

    gridLines.append(Part.LineSegment(bottomLeft, topLeft))
    gridLines.append(Part.LineSegment(topLeft, topRight))
    gridLines.append(Part.LineSegment(topRight, bottomRight))
    gridLines.append(Part.LineSegment(bottomLeft, bottomRight))

    # Connect the lines together
    gridConstraints.append(Sketcher.Constraint('Coincident', 0, 2, 1, 1))
    gridConstraints.append(Sketcher.Constraint('Coincident', 1, 2, 2, 1))
    gridConstraints.append(Sketcher.Constraint('Coincident', 2, 2, 3, 1))
    gridConstraints.append(Sketcher.Constraint('Coincident', 3, 2, 0, 1))

    # Equals for vertical and horizontal lines
    gridConstraints.append(Sketcher.Constraint('Equal', 0, 2))
    gridConstraints.append(Sketcher.Constraint('Equal', 1, 3))

    # Legth constraints
    gridConstraints.append(Sketcher.Constraint('DistanceY', 0, 1, 0, 2, rowHeight))
    gridConstraints.append(Sketcher.Constraint('DistanceX', 3, 2, 3, 1, columnWidth))

    # Symmetric constraint for top line
    gridConstraints.append(Sketcher.Constraint('Symmetric', 1, 1, 1, 2, -2))

    # Symmetric constraint right line
    gridConstraints.append(Sketcher.Constraint('Symmetric', 2, 1, 2, 2, -1))

    sketch.addGeometry(gridLines,True)
    sketch.addConstraint(gridConstraints)

    return 3

def drawDiamond(sketch, startLineNumber, width, height, columnCount, rowCount):
    halfWidth = width / 2
    halfHeight = height / 2
    
    rowHeight = height / rowCount
    columnWidth = width / columnCount
    bottomLeftPoint = App.Vector(-columnWidth / 2, -rowHeight / 2, 0)
    leftMiddle = App.Vector(0, rowHeight / 2, 0)
    topMiddle = App.Vector(columnWidth / 2, rowHeight, 0)
    rightMiddle = App.Vector(columnWidth, rowHeight / 2, 0)
    bottomMiddle = App.Vector(columnWidth / 2, 0, 0)

    lines = []
    constraints = []
    
    lines.append(Part.LineSegment(bottomLeftPoint.add(leftMiddle), bottomLeftPoint.add(topMiddle)))
    lines.append(Part.LineSegment(bottomLeftPoint.add(topMiddle), bottomLeftPoint.add(rightMiddle)))
    lines.append(Part.LineSegment(bottomLeftPoint.add(rightMiddle), bottomLeftPoint.add(bottomMiddle)))
    lines.append(Part.LineSegment(bottomLeftPoint.add(bottomMiddle), bottomLeftPoint.add(leftMiddle)))

    leftLine = 0
    topLine = 1
    rightLine = 2
    bottomLine = 3
    # Connect points of the diamond to the construction geometry
    constraints.append(Sketcher.Constraint('Symmetric', leftLine, 1, leftLine, 2, startLineNumber, 1))
    constraints.append(Sketcher.Constraint('Symmetric', topLine, 1, topLine, 2, startLineNumber, 2))
    constraints.append(Sketcher.Constraint('Symmetric', topLine, 1, topLine, 2, startLineNumber + 1, 1))
    constraints.append(Sketcher.Constraint('Symmetric', rightLine, 1, rightLine, 2, startLineNumber + 1, 2))
    constraints.append(Sketcher.Constraint('Symmetric', rightLine, 1, rightLine, 2, startLineNumber + 2, 1))
    constraints.append(Sketcher.Constraint('Symmetric', bottomLine, 1, bottomLine, 2, startLineNumber + 2, 2))
    constraints.append(Sketcher.Constraint('Symmetric', bottomLine, 1, bottomLine, 2, startLineNumber + 3, 1))
    constraints.append(Sketcher.Constraint('Symmetric', leftLine, 1, leftLine, 2, startLineNumber + 3, 2))

    sketch.addGeometry(lines,False)
    sketch.addConstraint(constraints)


class DiamondCommand:
    """Cread a rows of diamonds in a sketch"""

    def GetResources(self):
        # Add pixmap some time 'Pixmap'  : 'My_Command_Icon
        return {'MenuText': "Create Diamonds",
                'ToolTip' : "Create a Sketch of connected diamonds"}

    def Activated(self):
        selectedBody = findSelectedBody()
        sketch = createSketch(selectedBody)
        
        lastLineNumber = drawConstructionGeometry(sketch, 50, 20, 5, 1)
        drawDiamond(sketch, lastLineNumber + 1, 50, 20, 5, 1)

        FreeCAD.ActiveDocument.recompute()

    def IsActive(self):
        """If there is no active document we can't add a sketch to it."""
        return not FreeCAD.ActiveDocument is None

if __name__ == "__main__":
    command = DiamondCommand();
    
    if command.IsActive():
        command.Activated()
    else:
        QtGui.QMessageBox.information(  QtGui.qApp.activeWindow(), "No open Document", "There is no open document")
else:
    FreeCADGui.addCommand('Diamond_Sketch', DiamondCommand()) 