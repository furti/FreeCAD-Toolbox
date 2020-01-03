import FreeCAD
import Draft
import app.section_vector_renderer as section_vector_renderer

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

        return '%s %s %s %s' % (section_vector_renderer.toNumberString(x), section_vector_renderer.toNumberString(y), section_vector_renderer.toNumberString(scaledWidth), section_vector_renderer.toNumberString(scaledHeight))

    def adaptFromShapes(self, objects):
        for o in objects:
            if hasattr(o, "Shape") and o.Shape:
                bb = o.Shape.BoundBox

                self.update(bb.XMin, bb.YMin, bb.XMax, bb.YMax)

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


class SimpleSectionPlane:
    def __init__(self, obj):
        obj.Proxy = self
        self.sectionSVG = ''
        self.windowSVG = ''

        self.setupProperties(obj)

    def setupProperties(self, obj):
        pl = obj.PropertiesList
        self.Object = obj

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
        self.setProperties(obj)

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

        self.buildSectionsSvg(obj, render)
        self.buildBoundBox(obj, groups)

    def buildBoundBox(self, obj, groups):
        self.boundBox = BoundBox()

        self.boundBox.adaptFromShapes(groups["objects"])
        # self.boundBox.adaptFromShapes(groups["drafts"])

    def buildSectionsSvg(self, obj, render):
        self.sectionSVG = render.getSectionSVG(linewidth=25)
        self.windowSVG = render.getWindowSVG(linewidth=5)

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
        
        SECTION_SVG
        WINDOW_SVG
    </g>
</svg>
"""
        template = template.replace(
            "WIDTH", section_vector_renderer.toNumberString(width))
        template = template.replace(
            "HEIGHT", section_vector_renderer.toNumberString(height))
        template = template.replace("SECTION_SVG", self.sectionSVG)
        template = template.replace("WINDOW_SVG", self.windowSVG)
        # template = template.replace("SCALE_VALUE", str(scale))
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

        svg = simpleSectionPlaneObject.Proxy.getSvg(scale=0.1)

        file_object = open(
            "C:\\Meine Daten\\freecad\\samples\\SectionPlane\\Export.svg", "w")
        file_object.write(svg)
        file_object.close()
