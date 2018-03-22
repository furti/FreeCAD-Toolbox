
import FreeCAD, FreeCADGui, os
from PySide import QtGui

uipath = os.path.join(os.path.dirname(os.path.abspath(__file__)), '../Resources/ui')

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

def createPad(body, sketch):
    pad = body.newObject("PartDesign::Pad","Pad")
    pad.Profile = sketch
    pad.Length = 10.0
    pad.Reversed = 0

    FreeCAD.ActiveDocument.recompute()
    FreeCADGui.activeDocument().hide(sketch.Name)

    viewBody = body.ViewObject
    pad.ViewObject.ShapeColor=viewBody.ShapeColor
    pad.ViewObject.LineColor=viewBody.LineColor
    pad.ViewObject.PointColor=viewBody.PointColor
    pad.ViewObject.Transparency=viewBody.Transparency
    pad.ViewObject.DisplayMode=viewBody.DisplayMode
    
    FreeCAD.ActiveDocument.recompute()
    
    FreeCAD.ActiveDocument.recompute()

    return pad

def createMultiPattern(body, pad, sketch, width, height, columnCount, rowCount):
    multiPattern = body.newObject("PartDesign::MultiTransform","MultiTransform")

    FreeCAD.ActiveDocument.recompute()

    multiPattern.Originals = [pad,]
    multiPattern.Shape = pad.Shape

    FreeCAD.ActiveDocument.recompute()

    viewBody = body.ViewObject
    viewPattern = multiPattern.ViewObject

    viewPattern.ShapeColor=viewBody.ShapeColor
    viewPattern.LineColor=viewBody.LineColor
    viewPattern.PointColor=viewBody.PointColor
    viewPattern.Transparency=viewBody.Transparency
    viewPattern.DisplayMode=viewBody.DisplayMode

    body.Tip = multiPattern

    FreeCAD.ActiveDocument.recompute()

    # we have to substract the width of a single column because the first object is already there
    # And substract 1 so that the duplicates overlap
    columnPatternLength = width - width / columnCount - 1

    columnPattern = body.newObject("PartDesign::LinearPattern","LinearPattern")
    columnPattern.Direction = (sketch, ["H_Axis"])
    columnPattern.Length = columnPatternLength
    columnPattern.Occurrences = columnCount
    columnPattern.ViewObject.Visibility=False

    # we have to substract the height of a single row because the first object is already there
    # And substract 1 so that the duplicates overlap
    rowPatternLength = height - height / rowCount - 1

    rowPattern = body.newObject("PartDesign::LinearPattern","LinearPattern")
    rowPattern.Direction = (sketch, ["V_Axis"])
    rowPattern.Length = rowPatternLength
    rowPattern.Occurrences = rowCount
    rowPattern.ViewObject.Visibility=False

    multiPattern.Transformations = [columnPattern, rowPattern,]
    FreeCADGui.activeDocument().hide(pad.Name)

    FreeCAD.ActiveDocument.recompute()

def createLinearPattern(body, pad, sketch, width, columnCount):
    linearPattern = body.newObject("PartDesign::LinearPattern","LinearPattern")

    FreeCAD.ActiveDocument.recompute()

    # we have to substract the width of a single column because the first object is already there
    # And substract 1 so that the duplicates overlap
    length = width - width / columnCount - 1

    linearPattern.Originals = [pad,]
    linearPattern.Direction = (sketch, ["H_Axis"])
    linearPattern.Length = length
    linearPattern.Occurrences = columnCount

    FreeCAD.ActiveDocument.recompute()

    viewBody = body.ViewObject
    linearPattern.ViewObject.ShapeColor=viewBody.ShapeColor
    linearPattern.ViewObject.LineColor=viewBody.LineColor
    linearPattern.ViewObject.PointColor=viewBody.PointColor
    linearPattern.ViewObject.Transparency=viewBody.Transparency
    linearPattern.ViewObject.DisplayMode=viewBody.DisplayMode

    FreeCADGui.activeDocument().hide(pad.Name)

    body.Tip = linearPattern

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

    FreeCAD.ActiveDocument.recompute()

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

    FreeCAD.ActiveDocument.recompute()


class DiamondCommand:
    """Cread a rows of diamonds in a sketch"""

    def GetResources(self):
        # Add pixmap some time 'Pixmap'  : 'My_Command_Icon
        return {'MenuText': "Create Diamonds",
                'ToolTip' : "Create a Sketch of connected diamonds"}

    def Activated(self):
        selectedBody = findSelectedBody()

        if selectedBody is not None:
            dialog = DiamondDialog(selectedBody)
            FreeCADGui.Control.showDialog(dialog)

    def IsActive(self):
        """If there is no active document we can't add a sketch to it."""
        return not FreeCAD.ActiveDocument is None

class DiamondDialog:
    def __init__(self, selectedBody):
        self.selectedBody = selectedBody
        self.form = FreeCADGui.PySideUic.loadUi("%s/Diamond.ui"%uipath)

    def accept(self):
        width = float(self.form.WidthBox.text())
        height = float(self.form.HeightBox.text())
        columns = self.form.ColumnsBox.value()
        rows = self.form.RowsBox.value()

        sketch = createSketch(self.selectedBody)
        
        lastLineNumber = drawConstructionGeometry(sketch, width, height, columns, rows)
        drawDiamond(sketch, lastLineNumber + 1, width, height, columns, rows)

        pad = createPad(self.selectedBody, sketch)

        if rows > 1:
            createMultiPattern(self.selectedBody, pad, sketch, width, height, columns, rows)
        else:
            createLinearPattern(self.selectedBody, pad, sketch, width, columns)
        
        FreeCADGui.Control.closeDialog()

    def reject(self):
        FreeCADGui.Control.closeDialog()

if __name__ == "__main__":
    command = DiamondCommand();
    
    if command.IsActive():
        command.Activated()
    else:
        QtGui.QMessageBox.information(  QtGui.qApp.activeWindow(), "No open Document", "There is no open document")
else:
    FreeCADGui.addCommand('Diamond_Sketch', DiamondCommand()) 