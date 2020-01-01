import FreeCAD
import Part
import Sketcher
import math

def cell(column, row):
    return '%s%s' % (column, row)

class LumberData:
    def __init__(self, name, width, height, overallLength):
        self.name = name
        self.width = width
        self.height = height
        self.overallLength = overallLength

        self.missingLength = overallLength
    
    def lumberProduced(self, amount, length):
        fullLengthProduced = amount * length

        self.missingLength -= fullLengthProduced

        return self.missingLength
    
    def __repr__(self):
     return "LumberData(name=%s, width=%s, height=%s, overallLength=%s, missing=%s)" % (self.name, self.width, self.height, self.overallLength, self.missingLength)

class LogsData:
    def __init__(self, diameter, length, amount):
        self.diameter = diameter
        self.length = length
        self.amount = amount

        self.remaining = amount
        self.delta = 0
    
    def useLog(self):
        if self.remaining > 0:
            self.remaining -= 1

            return True
        
        return False
    
    def __repr__(self):
     return "LogsData(diameter=%s, length=%s, amount=%s, delta=%s)" % (self.diameter, self.length, self.amount, self.delta)

class WoodExtract:
    def __init__(self, obj):
        obj.Proxy = self
        
        self.setupProperties(obj)
        
    def setupProperties(self, obj):
        pl = obj.PropertiesList

        if not hasattr(obj.Proxy, "Sketches"):
            obj.Proxy.Sketches = []
        if not "Lumber" in pl:
            obj.addProperty("App::PropertyLink",   "Lumber",
                "WoodExtract", "List of lumber needed")
        if not "Logs" in pl:
            obj.addProperty("App::PropertyLink",   "Logs",
                "WoodExtract", "List of Logs you have")
        
    def execute(self, obj):
        try:
            obj.Logs.NoTouch = True
            self.removeSketches()
            
            lumberData = self.readLumber(obj)
            logsData = self.readLogs(obj)

            for lumber in lumberData:
                self.produce(obj, lumber, logsData)
            
            self.calculateDelta(obj, lumberData, logsData)

            self.writeDelta(obj, logsData)
        finally:
            obj.Logs.NoTouch = False

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def removeSketches(self):
        for sketch in self.Sketches:
            FreeCAD.ActiveDocument.removeObject(sketch.Name)
        
        self.Sketches.clear()

    def writeDelta(self, obj, logsData):
        sheet = obj.Logs
        lineNumber = 2

        for logs in logsData:
            amount = sheet.set(cell('E', lineNumber), '%s' % (logs.delta, ))
            lineNumber += 1

    def calculateDelta(self, obj, lumberData, logsData):
        everythingProduced = len([lumber for lumber in lumberData if lumber.missingLength > 0]) == 0

        if everythingProduced:
            # When everything is fully produced, we print the remaining logs as delta.
            # This means we have to much logs for our lumber
            for logs in logsData:
                logs.delta = logs.remaining
        else:
            for logs in logsData:
                for lumber in lumberData:
                    # This lumber entry is fully produced. Skip it
                    if lumber.missingLength <= 0:
                        continue

                    amountOfLumberPerLog = self.calculateAmountOfLumberForLogs(obj, logs, lumber, False)
                    overallLengthPerLog = amountOfLumberPerLog * logs.length

                    if overallLengthPerLog > 0:
                        numberOfMissingLumber = math.ceil(lumber.missingLength / overallLengthPerLog)

                        logs.delta -= numberOfMissingLumber

    def produce(self, obj, lumber, logsData):
        for logs in logsData:
            amountOfLumberPerLog = self.calculateAmountOfLumberForLogs(obj, logs, lumber)

            while logs.useLog():
                missingLength = lumber.lumberProduced(amountOfLumberPerLog, logs.length)

                # When the actual lumber entry is fully produced, we can produce the next one
                if missingLength <= 0:
                    return

    def calculateAmountOfLumberForLogs(self, obj, logs, lumber, saveSketch=True):
        sketch = self.prepareSketch(logs.diameter.Value / 2, lumber.height.Value, saveSketch)

        try:
            widthWithOffset = lumber.width.Value + 5
            lineSegments = sketch.Geometry[1::]
            numberOfLogs = 0

            for i in range(0, len(lineSegments) - 1):
                shortestLine = self.findShortestLine(lineSegments[i], lineSegments[i+1])

                # If the current section is not long enough to fit a single lumber inside, skip it
                if shortestLine.length() < widthWithOffset:
                    continue

                numberOfLogsForSection = math.floor(shortestLine.length() / widthWithOffset)
                numberOfLogs += numberOfLogsForSection
            
            return numberOfLogs
        finally:
            if not saveSketch:
                FreeCAD.ActiveDocument.removeObject(sketch.Name)

    def findShortestLine(self, l1, l2):
        if l1.length() > l2.length():
            return l2
        
        return l1

    def prepareSketch(self, radius, height, saveSketch):
        sketch = FreeCAD.ActiveDocument.addObject('Sketcher::SketchObject','Sketch')

        if saveSketch:
            sketch.ViewObject.hide()
            self.Sketches.append(sketch)

        radiusWithOffset = radius - 20
        heightWithOffset = height + 5

        numberOfLinesToDraw = math.floor(radiusWithOffset * 2 / heightWithOffset) + 1

        # draw circle
        sketch.addGeometry(Part.Circle(FreeCAD.Vector(0, radiusWithOffset , 0), FreeCAD.Vector(0,0,1), radiusWithOffset))
        sketch.addConstraint(Sketcher.Constraint('PointOnObject', 0, 3, -2))
        sketch.addConstraint(Sketcher.Constraint('PointOnObject', -1, 1, 0)) 
        sketch.addConstraint(Sketcher.Constraint('Radius', 0, radiusWithOffset))

        # draw lines starting from top
        y = radiusWithOffset + (numberOfLinesToDraw / 2) * heightWithOffset - heightWithOffset / 2

        for i in range(numberOfLinesToDraw):
            geometryIndex = i + 1

            sketch.addGeometry(Part.LineSegment(FreeCAD.Vector(-radiusWithOffset, y, 0), FreeCAD.Vector(radiusWithOffset, y, 0)))
            sketch.addConstraint(Sketcher.Constraint('Horizontal', geometryIndex))
            sketch.addConstraint(Sketcher.Constraint('DistanceY', -1, 1, geometryIndex, 2, y))
            sketch.addConstraint(Sketcher.Constraint('PointOnObject', geometryIndex, 1, 0))
            sketch.addConstraint(Sketcher.Constraint('PointOnObject', geometryIndex, 2, 0))

            y -= heightWithOffset
        
        sketch.recompute()

        return sketch
    
    def onDocumentRestored(self,obj):
        self.setupProperties(obj)
    
    def readLumber(self, obj):
        sheet = obj.Lumber
        lineNumber = 2
        lumberData = []

        while True:
            try:
                name = sheet.get(cell('A', lineNumber))
                width = sheet.get(cell('B', lineNumber))
                height = sheet.get(cell('C', lineNumber))
                overallLength = sheet.get(cell('D', lineNumber))

                lumberData.append(LumberData(name, width, height, overallLength))

            except ValueError:
                print('no data %s' %(lineNumber, ))
                break

            lineNumber += 1
        
        return lumberData
    
    def readLogs(self, obj):
        sheet = obj.Logs
        lineNumber = 2
        logsData = []

        while True:
            try:
                diameter = sheet.get(cell('A', lineNumber))
                length = sheet.get(cell('B', lineNumber))
                amount = sheet.get(cell('C', lineNumber))

                logsData.append(LogsData(diameter, length, amount))

            except ValueError:
                print('no data %s' %(lineNumber, ))
                break

            lineNumber += 1
        
        return logsData

if __name__ == "__main__":
    if FreeCAD.ActiveDocument is None:
        print('Create a document to continue.')
    else:
        import Spreadsheet

        woodExtractObject = FreeCAD.ActiveDocument.addObject(
            "App::FeaturePython", "WoodExtract")
        woodExtract = WoodExtract(woodExtractObject)

        # sketch = FreeCAD.ActiveDocument.addObject('Sketcher::SketchObject','Sketch')
        # woodExtractObject.Sketch = sketch

        woodExtractObject.Lumber = FreeCAD.ActiveDocument.Lumber
        woodExtractObject.Logs = FreeCAD.ActiveDocument.Logs

        FreeCAD.ActiveDocument.recompute()

# 19 pro log
