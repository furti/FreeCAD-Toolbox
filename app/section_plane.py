import FreeCAD
import Draft
import math

import app.section_vector_renderer as section_vector_renderer
from app.section_vector_renderer import toNumberString

from FreeCAD import Vector

if FreeCAD.GuiUp:
    import FreeCADGui
    from PySide.QtCore import QT_TRANSLATE_NOOP
else:
    # \cond
    def translate(ctxt, txt):
        return txt

    def QT_TRANSLATE_NOOP(ctxt, txt):
        return txt


def looksLikeDraft(o):
    """Does this object look like a Draft shape? (flat, no solid, etc)"""

    # If there is no shape at all ignore it
    if not hasattr(o, 'Shape') or o.Shape.isNull():
        return False

    # If there are solids in the object, it will be handled later
    # by getCutShapes
    if len(o.Shape.Solids) > 0:
        return False

    # If we have a shape, but no volume, it looks like a flat 2D object
    return o.Shape.Volume < 0.0000001  # add a little tolerance...


def isOriented(obj, plane):
    """determines if an annotation is facing the cutplane or not"""

    norm1 = plane.normalAt(0, 0)

    if hasattr(obj, "Placement"):
        norm2 = obj.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))
    elif hasattr(obj, "Normal"):
        norm2 = obj.Normal
        if norm2.Length < 0.01:
            return True
    else:
        return True

    a = norm1.getAngle(norm2)

    if (a < 0.01) or (abs(a-math.pi) < 0.01):
        return True

    return False


def filterObjects(includeList, excludeList):
    objectsToProcess = []

    for o in includeList:
        if o in excludeList:
            continue

        objectsToProcess.append(o)

        groupObjects = Draft.getGroupContents(
            [o], walls=True, addgroups=True)

        groupObjects.remove(o)

        objectsToProcess.extend(filterObjects(groupObjects, excludeList))

    return objectsToProcess


def groupObjects(objectsToProcess, cutplane):
    groups = {
        "spaces": [],
        "drafts": [],
        "windows": [],
        "objects": []
    }

    typesToIgnore = ["BuildingPart", "Group"]

    for o in objectsToProcess:
        objectType = Draft.getType(o)

        if objectType == "Space":
            groups["spaces"].append(o)
        elif objectType in ["Dimension", "Annotation", "Label", "DraftText"]:
            if isOriented(o, cutplane):
                groups["drafts"].append(o)
        elif o.isDerivedFrom("Part::Part2DObject"):
            groups["drafts"].append(o)
        elif looksLikeDraft(o):
            groups["drafts"].append(o)
        elif objectType == "Window":
            groups["windows"].append(o)
        elif not objectType in typesToIgnore:
            groups["objects"].append(o)

    return groups


class BoundBox():
    def __init__(self):
        self.initialized = False
        self.minx = 0
        self.miny = 0
        self.maxx = 0
        self.maxy = 0

    def buildViewbox(self, scale, width, height):
        print((self.minx, self.miny, self.maxx, self.maxy))
        scaledWidth = width / scale
        scaledHeight = height / scale

        # So we are in the top left corner of the viewport
        x = self.minx
        y = -self.maxy

        x -= (scaledWidth - self.overallWidth()) / 2
        y -= (scaledHeight - self.overallHeight()) / 2

        return '%s %s %s %s' % (toNumberString(x), toNumberString(y), toNumberString(scaledWidth), toNumberString(scaledHeight))

    def adaptFromShapes(self, objects):
        for o in objects:
            if hasattr(o, "Shape") and o.Shape:
                bb = o.Shape.BoundBox

                self.update(bb.XMin, bb.YMin, bb.XMax, bb.YMax)

    def adaptFromDrafts(self, objects):
        for o in objects:
            objectType = Draft.getType(o)
            if objectType == "Dimension":
                start = o.ViewObject.Proxy.p2
                end = o.ViewObject.Proxy.p3

                minx = min(start.x, end.x)
                maxx = max(start.x, end.x)
                miny = min(start.y, end.y)
                maxy = max(start.y, end.y)

                self.update(minx, miny, maxx, maxy)
            else:
                print("Unkown object type " + objectType)

    def update(self, minx, miny, maxx, maxy):
        if not self.initialized:
            self.minx = minx
            self.miny = miny
            self.maxx = maxx
            self.maxy = maxy

            self.initialized = True

            return

        if minx < self.minx:
            self.minx = minx
        if miny < self.miny:
            self.miny = miny
        if maxx > self.maxx:
            self.maxx = maxx
        if maxy > self.maxy:
            self.maxy = maxy

    def overallWidth(self):
        return self.maxx - self.minx

    def overallHeight(self):
        return self.maxy - self.miny


DIMESION_TEMPLATE = """
<g stroke-width="DIMENSION_STROKE_WIDTH"
   style="stroke-width:DIMENSION_STROKE_WIDTH; stroke-miterlimit:1; stroke-linejoin:round; stroke-dasharray:none;"
   stroke="#000000">
    <path d="PATH_DATA" />
    <path d="TICK_LEFT" transform="rotate(TICK_ROTATION_LEFT)" />
    <path d="TICK_RIGHT" transform="rotate(TICK_ROTATION_RIGHT)" />
    TEXT_ELEMENT
</g>
"""

TEXT_TEMPLATE = """
<text
        x="TEXT_POSITION_X"
        y="TEXT_POSITION_Y"
        style="font-size:TEXT_FONT_SIZE;font-family:Arial;letter-spacing:0px;word-spacing:0px;fill:#000000;text-anchor:middle;text-align:center;stroke:none;"
        transform="rotate(TEXT_ROTATION)">
            TEXT_CONTENT
</text>
"""


def calculateDimensionAngle(start, end):
    direction = start.sub(end).normalize()
    xAxis = FreeCAD.Vector(1, 0, 0)

    angleInRad = math.acos(direction.dot(xAxis))
    angle = math.degrees(angleInRad)

    if angle > 90:
        while angle >= 90:
            angle -= 90

    return angle


def getDimensionTextSvg(d, start, end, angle):
    text = toNumberString(d.Distance.Value / 10, d.ViewObject.Decimals)
    tpos = d.ViewObject.Proxy.tbase
    midpoint = start.add(end).multiply(0.5)

    tx = toNumberString(tpos.x)
    ty = toNumberString(-tpos.y)

    textSvg = TEXT_TEMPLATE.replace("TEXT_CONTENT", text)
    textSvg = textSvg.replace("TEXT_POSITION_X", tx)
    textSvg = textSvg.replace("TEXT_POSITION_Y", ty)
    textSvg = textSvg.replace("TEXT_ROTATION", '%s %s %s' % (angle, tx, ty))

    return textSvg


def getDimensionSvg(d):
    start = d.ViewObject.Proxy.p2
    end = d.ViewObject.Proxy.p3

    startx = toNumberString(start.x)
    starty = toNumberString(-start.y)
    endx = toNumberString(end.x)
    endy = toNumberString(-end.y)

    path = "M %s %s L %s %s" % (startx, starty, endx, endy)
    tickLeft = "M %s %s L %s %s" % (
        startx, toNumberString(-start.y - 50), startx, toNumberString(-start.y + 50))
    tickRight = "M %s %s L %s %s" % (
        endx, toNumberString(-end.y - 50), endx, toNumberString(-end.y + 50))

    angle = calculateDimensionAngle(start, end)

    dimensionSvg = DIMESION_TEMPLATE.replace("PATH_DATA", path)
    dimensionSvg = dimensionSvg.replace("TICK_LEFT", tickLeft)
    dimensionSvg = dimensionSvg.replace("TICK_RIGHT", tickRight)
    dimensionSvg = dimensionSvg.replace(
        "TICK_ROTATION_LEFT", '%s %s %s' % (angle, startx, starty))
    dimensionSvg = dimensionSvg.replace(
        "TICK_ROTATION_RIGHT", '%s %s %s' % (angle, endx, endy))
    dimensionSvg = dimensionSvg.replace(
        "TEXT_ELEMENT", getDimensionTextSvg(d, start, end, angle))

    return dimensionSvg


def getDraftSvg(objects):
    svg = ""

    for d in objects:
        objectType = Draft.getType(d)

        if objectType == "Dimension":
            svg += getDimensionSvg(d)
        else:
            print("Unsupported object type " + objectType)

    return svg


class SimpleSectionPlane:
    def __init__(self, obj):
        obj.Proxy = self

        self.setupProperties(obj)

    def setupProperties(self, obj):
        pl = obj.PropertiesList
        self.Object = obj

        self.patternSVG = ''
        self.sectionSVG = ''
        self.windowSVG = ''
        self.draftSvg = ''

        if not "Placement" in pl:
            obj.addProperty("App::PropertyPlacement", "Placement", "SectionPlane", QT_TRANSLATE_NOOP(
                "App::Property", "The placement of this object"))

        if not "Shape" in pl:
            obj.addProperty("Part::PropertyPartShape", "Shape", "SectionPlane", QT_TRANSLATE_NOOP(
                "App::Property", "The shape of this object"))

        if not "IncludeObjects" in pl:
            obj.addProperty("App::PropertyLinkList", "IncludeObjects", "SectionPlane", QT_TRANSLATE_NOOP(
                "App::Property", "The objects that will be considered by this section plane"))

        if not "ExcludeObjects" in pl:
            obj.addProperty("App::PropertyLinkList", "ExcludeObjects", "SectionPlane", QT_TRANSLATE_NOOP(
                "App::Property", "The objects that will be excluded by this section plane, even if they are matched by the IncludeObjects list"))

        if not "TargetFile" in pl:
            obj.addProperty("App::PropertyFile", "TargetFile",
                            "SectionPlane", "Target svg file to write to")

        if not "SkipCompute" in pl:
            obj.addProperty("App::PropertyBool", "SkipCompute",
                            "SectionPlane", "Skip Computing").SkipCompute = True

        if not "Scale" in pl:
            obj.addProperty("App::PropertyFloat", "Scale",
                            "SectionPlane", "Scale to apply to output svg").Scale = 1/50

        self.Type = "SimpleSectionPlane"

    def onDocumentRestored(self, obj):
        self.setupProperties(obj)

    def __getstate__(self):
        return None

    def __setstate__(self, state):
        return None

    def execute(self, obj):
        if obj.SkipCompute:
            return

        self.doExecute(obj)

    def doExecute(self, obj):
        cutplane = self.calculateCutPlane(obj)

        objectsToProcess = filterObjects(
            obj.IncludeObjects, obj.ExcludeObjects)

        if len(objectsToProcess) == 0:
            return

        groups = groupObjects(objectsToProcess, cutplane)
        render = self.render(obj, groups, cutplane)

        self.buildSvgParts(obj, render, groups)
        self.drafts = groups["drafts"]
        self.buildBoundBox(obj, groups)

    def buildBoundBox(self, obj, groups):
        self.boundBox = BoundBox()

        self.boundBox.adaptFromShapes(groups["objects"])
        self.boundBox.adaptFromDrafts(groups["drafts"])

    def buildSvgParts(self, obj, render, groups):
        parts = render.getSvgParts()

        self.sectionSVG = parts["sections"]
        self.windowSVG = parts["windows"]
        self.patternSVG = parts["patterns"]
        self.draftSvg = getDraftSvg(groups["drafts"])

    def render(self, obj, groups, cutplane):
        render = section_vector_renderer.Renderer(obj.Placement)
        render.addObjects(groups["objects"])
        render.addWindows(groups["windows"])
        render.cut(cutplane)

        return render

    def calculateCutPlane(self, obj):
        import Part

        l = 1
        h = 1

        if obj.ViewObject:
            if hasattr(obj.ViewObject, "DisplayLength"):
                l = obj.ViewObject.DisplayLength.Value
                h = obj.ViewObject.DisplayHeight.Value
            elif hasattr(obj.ViewObject, "DisplaySize"):
                # old objects
                l = obj.ViewObject.DisplaySize.Value
                h = obj.ViewObject.DisplaySize.Value

        p = Part.makePlane(l, h, Vector(l/2, -h/2, 0), Vector(0, 0, -1))

        # make sure the normal direction is pointing outwards, you never know what OCC will decide...
        if p.normalAt(0, 0).getAngle(obj.Placement.Rotation.multVec(FreeCAD.Vector(0, 0, 1))) > 1:
            p.reverse()

        p.Placement = obj.Placement

        return p

    def getSvg(self, width=420, height=297, scale=1/50):
        if not self.sectionSVG:
            self.doExecute(self.Object)

        template = """
<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="WIDTHmm" height="HEIGHTmm" viewBox="VIEWBOX_VALUES"
     version="1.1">
    <sodipodi:namedview
        id="base"
        pagecolor="#ffffff"
        bordercolor="#666666"
        borderopacity="1.0"
        inkscape:pageopacity="1"
        inkscape:pageshadow="2"
        inkscape:document-units="mm"
        inkscape:window-maximized="1" />
    <g
        inkscape:label="Layer 1"
        inkscape:groupmode="layer"
        id="layer1">

        <g i="everything">
            <g id="patterns">
                PATTERN_SVG
            </g>

            <g id="sections">
                SECTION_SVG
            </g>

            <g id="windows">
                WINDOW_SVG
            </g>

            <g id="drafts">
                DRAFT_SVG
            </g>
        </g>
    </g>
</svg>
"""
        template = template.replace(
            "WIDTH", toNumberString(width))
        template = template.replace(
            "HEIGHT", toNumberString(height))
        template = template.replace("PATTERN_SVG", self.patternSVG)
        template = template.replace("SECTION_SVG", self.sectionSVG)
        template = template.replace("WINDOW_SVG", self.windowSVG)
        template = template.replace("DRAFT_SVG", self.draftSvg)
        template = template.replace("TEXT_FONT_SIZE", str(240))
        template = template.replace(
            "DIMENSION_STROKE_WIDTH", toNumberString(0.5 / scale))
        template = template.replace(
            "SECTION_STROKE_WIDTH", toNumberString(0.5 / scale))
        template = template.replace(
            "WINDOW_STROKE_WIDTH", toNumberString(0.1 / scale))
        template = template.replace(
            "VIEWBOX_VALUES", self.boundBox.buildViewbox(scale, width, height))

        return template


if __name__ == "__main__":
    if FreeCAD.ActiveDocument is None:
        print('Create a document to continue.')
    else:
        simpleSectionPlaneObject = FreeCAD.ActiveDocument.addObject(
            "App::FeaturePython", "SectionPlane")
        SimpleSectionPlane(simpleSectionPlaneObject)

        # simpleSectionPlaneObject.IncludeObjects = [
        #     FreeCAD.ActiveDocument.Wall003]
        simpleSectionPlaneObject.IncludeObjects = [
            FreeCAD.ActiveDocument.BuildingPart]

        simpleSectionPlaneObject.Placement = FreeCAD.Placement(
            Vector(0, 0, 1000), FreeCAD.Rotation(Vector(0, 0, 1), 0))

        FreeCAD.ActiveDocument.recompute()

        svg = simpleSectionPlaneObject.Proxy.getSvg(scale=0.02)

        file_object = open(
            "C:\\Meine Daten\\freecad\\samples\\SectionPlane\\Export.svg", "w")
        file_object.write(svg)
        file_object.close()
