
import FreeCAD,FreeCADGui

import FreeCAD
from PySide import QtGui

def findSelectedSketch():
    selection = [o for o in FreeCADGui.Selection.getSelection(FreeCAD.ActiveDocument.Name) if o.TypeId == "Sketcher::SketchObject"]

    if len(selection) == 1:
        return selection[0]
    else:
           QtGui.QMessageBox.information(  QtGui.qApp.activeWindow(), "Selection Error", "Select a single Sketch to perform the Operation")

           return None

def activateSketch(sketch):
    FreeCADGui.activeDocument().setEdit(sketch.Name)

def deactivateSketch(sketch):
    FreeCADGui.activeDocument().resetEdit()

def drawConstructionGeometry(sketch, width, height, columnCount, rowCount):
    halfHeight = height / 2
    halfWidth = width / 2

    # Draw the grid
    gridLines = []
    gridConstraints = []

    vector = App.Vector(-halfWidth, -halfHeight, 0)
    rowHeight = height / rowCount
    columnWidth = width / columnCount
    lineNumber = 0

    for row in range(0, rowCount):
        for column in range(0, columnCount):
            numberOfLinesAdded = 0
            base = App.Vector(column * columnWidth, row * rowHeight, 0)
            vertical = App.Vector(column * columnWidth, (row + 1) * rowHeight, 0)
            horizontal = App.Vector((column + 1) * columnWidth, row * rowHeight, 0)

            gridLines.append(Part.LineSegment(vector.add(base), vector.add(vertical)))
            gridLines.append(Part.LineSegment(vector.add(base), vector.add(horizontal)))
            numberOfLinesAdded = 2

            gridConstraints.append(Sketcher.Constraint('Vertical', lineNumber))
            gridConstraints.append(Sketcher.Constraint('Horizontal', lineNumber + 1))
            gridConstraints.append(Sketcher.Constraint('Coincident', lineNumber, 1, lineNumber + 1, 1))

            if lineNumber > 0:
                gridConstraints.append(Sketcher.Constraint('Equal', 0 , lineNumber))
                gridConstraints.append(Sketcher.Constraint('Equal', 1 , lineNumber + 1))

            # Connect columns together
            if column > 0:
                previousLine = lineNumber - 1

                # If we are in the last row we add 3 lines per iteration.
                # So we need to account for the top horizontal line here.
                if row == rowCount - 1:
                    previousLine -= 1

                gridConstraints.append(Sketcher.Constraint('Coincident', previousLine , 2, lineNumber, 1))

            # Add the last vertical line at the end of the row
            if column == columnCount - 1:
                lastBase = App.Vector((column + 1) * columnWidth, row * rowHeight, 0)
                lastVertical = App.Vector((column + 1) * columnWidth, (row + 1) * rowHeight, 0)
                
                gridLines.append(Part.LineSegment(vector.add(lastBase), vector.add(lastVertical)))
                gridConstraints.append(Sketcher.Constraint('Vertical', lineNumber + numberOfLinesAdded))

                # Connect the line with the previous horizontal one
                gridConstraints.append(Sketcher.Constraint('Coincident', lineNumber + 1 , 2, lineNumber + 2, 1))

                # Equals to the first vertical one
                gridConstraints.append(Sketcher.Constraint('Equal', 0 , lineNumber + 2))
                
                numberOfLinesAdded += 1

            # Add the horizontal line at the top
            if row == rowCount - 1:
                topBase = App.Vector(column * columnWidth, (row + 1) * rowHeight, 0)
                topHorizontal = App.Vector((column + 1) * columnWidth, (row + 1) * rowHeight, 0)

                gridLines.append(Part.LineSegment(vector.add(topBase), vector.add(topHorizontal)))
                gridConstraints.append(Sketcher.Constraint('Horizontal', lineNumber + numberOfLinesAdded))
                
                gridConstraints.append(Sketcher.Constraint('Coincident', lineNumber + numberOfLinesAdded , 1, lineNumber, 2))

                # Equals to the first horizontal one
                gridConstraints.append(Sketcher.Constraint('Equal', 1 , lineNumber + numberOfLinesAdded))

                numberOfLinesAdded += 1

            lineNumber += numberOfLinesAdded

        # Connect the rows together
        if row > 0:
            previousRow = row - 1
            numberOfLinesInRow = columnCount * 2 + 1 # we add 2 lines per column + the last vertical one at the end

            gridConstraints.append(Sketcher.Constraint('Coincident', previousRow * numberOfLinesInRow, 2, row * numberOfLinesInRow, 1))
    
    # Add the length constraints for the columns and rows
    gridConstraints.append(Sketcher.Constraint('DistanceY', 0, 1, 0, 2, rowHeight))
    gridConstraints.append(Sketcher.Constraint('DistanceX', 1, 1, 1, 2, columnWidth))

    linesPerColumn = columnCount * 2 + 1
    topLeftLine =  linesPerColumn * (rowCount - 1)
    topRightLine = topLeftLine + linesPerColumn + columnCount - 2 # we have to add the columcount - 2 again because we add a additional top line in the last row. But the last top line is after the line we want so -1 and zero based so again -1.
    bottomRightLine = linesPerColumn - 2

    # If the first row is the last row we have to add the additional top lines
    if rowCount == 1:
        bottomRightLine += columnCount

    # Symmetric constraint between top left and top right corner
    gridConstraints.append(Sketcher.Constraint('Symmetric', topLeftLine, 2, topRightLine, 2, -2))

    # Symmetric constraint between top right and bottom right corner
    gridConstraints.append(Sketcher.Constraint('Symmetric', topRightLine, 2, bottomRightLine, 1, -1))

    sketch.addGeometry(gridLines,True)
    sketch.addConstraint(gridConstraints)

    return lineNumber - 1

def drawDiamonds(sketch, startLineNumber, width, height, columnCount, rowCount):
    halfWidth = width / 2
    halfHeight = height / 2
    rowHeight = height / rowCount
    columnWidth = width / columnCount
    bottomLeftPoint = App.Vector(-halfWidth, -halfHeight, 0)
    leftMiddle = App.Vector(0, columnWidth / 2, 0)
    topMiddle = App.Vector(rowHeight / 2, columnWidth, 0)
    rightMiddle = App.Vector(rowHeight, columnWidth / 2, 0)
    bottomMiddle = App.Vector(rowHeight / 2, 0, 0)

    lines = []
    constraints = []
    lineNumber = startLineNumber

    for row in range(0, rowCount):
        for column in range(0, columnCount):
            base = bottomLeftPoint.add(App.Vector(column * columnWidth, row * rowHeight, 0))

            lines.append(Part.LineSegment(base.add(leftMiddle), base.add(topMiddle)))
            lines.append(Part.LineSegment(base.add(topMiddle), base.add(rightMiddle)))
            lines.append(Part.LineSegment(base.add(rightMiddle), base.add(bottomMiddle)))
            lines.append(Part.LineSegment(base.add(bottomMiddle), base.add(leftMiddle)))

            # Connect each Diamond together on its own
            constraints.append(Sketcher.Constraint('Coincident', lineNumber, 2, lineNumber + 1, 1))
            constraints.append(Sketcher.Constraint('Coincident', lineNumber + 1, 2, lineNumber + 2, 1))
            constraints.append(Sketcher.Constraint('Coincident', lineNumber + 2, 2, lineNumber + 3, 1))
            constraints.append(Sketcher.Constraint('Coincident', lineNumber + 3, 2, lineNumber, 1))

            linesPerRow = columnCount * 2 + 1
            leftLine = linesPerRow * row + column * 2
            rightLine = leftLine + 2
            bottomLine = leftLine + 1
            topLine = leftLine + linesPerRow + 1

            # The last row contains a additional top line per column. Add it here
            if row == rowCount - 1:
                leftLine += column
                rightLine += column + 1
                bottomLine += column

                if column == columnCount - 1:
                    topLine = leftLine + 3
                    rightLine = rightLine - 1
                else:
                    topLine = leftLine + 2

            # If we are in the second last row we have to add the additional top line
            if row == rowCount - 2:
                topLine += column

            FreeCAD.Console.PrintMessage("b: %s, line: %s\n"%(bottomLine, lineNumber  + 3))

            # Connect the diamonds to the construction geometry. left top right bottom
            constraints.append(Sketcher.Constraint('Symmetric', leftLine, 1, leftLine, 2, lineNumber, 1))
            constraints.append(Sketcher.Constraint('Symmetric', topLine, 1, topLine, 2, lineNumber + 1, 1))
            constraints.append(Sketcher.Constraint('Symmetric', rightLine, 1, rightLine, 2, lineNumber + 2, 1))
            #constraints.append(Sketcher.Constraint('Symmetric', bottomLine, 1, bottomLine, 2, lineNumber + 3, 1))

            lineNumber += 4

    sketch.addGeometry(lines,False)
    sketch.addConstraint(constraints)


class DiamondCommand:
    """Cread a rows of diamonds in a sketch"""

    def GetResources(self):
        # Add pixmap some time 'Pixmap'  : 'My_Command_Icon
        return {'MenuText': "Create Diamonds",
                'ToolTip' : "Create a Sketch of connected diamonds"}

    def Activated(self):
        selectedSketch = findSelectedSketch()
        
        if selectedSketch is not None:
           activateSketch(selectedSketch)
           lastLineNumber = drawConstructionGeometry(selectedSketch, 50, 20, 5, 1)
           drawDiamonds(selectedSketch, lastLineNumber + 1, 50, 20, 5, 1)

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