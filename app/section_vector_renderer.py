import FreeCAD
import math
import Part
import ArchCommands
import Draft
import DraftVecUtils
import DraftGeomUtils

MAXLOOP = 10  # the max number of loop before abort

DEBUG = FreeCAD.ParamGet(
    "User parameter:BaseApp/Preferences/Mod/Arch").GetBool("ShowVRMDebug")

DEFAULT_PATTERN_TEMPLATE = """
<pattern
    id="PATTERN_ID"
    patternUnits="userSpaceOnUse"
    x="0" y="0" width="100" height="100">
        <g>
            <rect width="100" height="100"
                style="stroke:none; fill:#ffffff" />
            <path style="stroke:PATTERN_COLOR; stroke-width:10; stroke-linecap:butt; stroke-linejoin:miter; fill:none; opacity:PATTERN_OPACITY" 
                  d="M0,0 l100,100" />
        </g>
</pattern>
"""

INSULATION_HARD_PATTERN_TEMPLATE = """
<pattern
    id="PATTERN_ID"
    patternUnits="userSpaceOnUse"
    x="0" y="0" width="100" height="100">
        <g>
            <rect width="100" height="100"
                style="stroke:none; fill:#ffffff" />
            <path style="stroke:PATTERN_COLOR; stroke-width:10; stroke-linecap:butt; stroke-linejoin:miter; fill:none; opacity:PATTERN_OPACITY" 
                  d="M 0,0 100,25 0,50 100,75 0,100" />
        </g>
</pattern>
"""

INSULATION_SOFT_PATTERN_TEMPLATE = """
<pattern
    id="PATTERN_ID"
    patternUnits="userSpaceOnUse"
    x="0" y="0" width="100" height="100">
        <g>
            <rect width="100" height="100"
                style="stroke:none; fill:#ffffff" />
            <path style="stroke:PATTERN_COLOR; stroke-width:10; stroke-linecap:butt; stroke-linejoin:miter; fill:none; opacity:PATTERN_OPACITY" 
                  d="M 25,0 75,25 25,50 75,75 25,100 M 25,0 C 25,0 0,9.9768635 0,24.999995 0,40.023126 25,50 25,50 m 0,0 C 25,50 0,59.976863 0,74.999995 0,90.023126 25,100.00001 25,100.00001 M 75,75 c 0,0 25,9.976865 25,24.999997 C 100,115.02313 75,125 75,125 m 0,-150 c 0,0 25,9.976868 25,25 0,15.023131 -25,25 -25,25 m 0,0 c 0,0 25,9.976869 25,25 0,15.023131 -25,25 -25,25" />
        </g>
</pattern>
"""

WINDOW_PATTERN_TEMPLATE = """
<pattern
    id="PATTERN_ID"
    patternUnits="userSpaceOnUse"
    x="0" y="0" width="100" height="100">
        <g>
            <rect width="100" height="100"
                style="stroke:none; fill:#ffffff" />
            <path style="stroke:PATTERN_COLOR; stroke-width:10; stroke-linecap:butt; stroke-linejoin:miter; fill:none; opacity:PATTERN_OPACITY" 
                  d="M 0,100 100,0 M 0,0 100,100" />
        </g>
</pattern>
"""

PATH_TEMPLATE = """
<path d="PATH_DATA" stroke="#000000" stroke-width="STROKE_WIDTH"
      style="fill:PATH_FILL; fill-rule: evenodd; stroke-width:STROKE_WIDTH; stroke-miterlimit:1; stroke-linejoin:round; stroke-dasharray:none;"/>
"""

PATTERN_TEMPLATES = {
    'DEFAULT': DEFAULT_PATTERN_TEMPLATE,
    "INSULATION_HARD": INSULATION_HARD_PATTERN_TEMPLATE,
    "INSULATION_SOFT": INSULATION_SOFT_PATTERN_TEMPLATE,
    "WINDOW": WINDOW_PATTERN_TEMPLATE
}


def toNumberString(val, precision=None):
    if precision is None:
        precision = DraftVecUtils.precision()

    rounded = round(val, precision)

    if precision == 0:
        rounded = int(rounded)

    return str(rounded)


def getProj(vec, plane):
    if not plane:
        return vec

    return plane.getLocalCoords(vec)


def getPatternType(o):
    if not hasattr(o, "Material") or not o.Material:
        return None

    mat = o.Material.Material

    if not "PatternType" in mat:
        return None

    return mat["PatternType"]


class BoundBox():
    def __init__(self, plane):
        self.initialized = False
        self.plane = plane

        self.minx = 0
        self.miny = 0
        self.maxx = 0
        self.maxy = 0

    def calculateOffset(self, scale, width, height):
        scaledWidth = width / scale
        scaledHeight = height / scale

        # So we are in the top left corner of the viewport
        x = self.minx
        y = -self.maxy

        x -= (scaledWidth - self.overallWidth()) / 2
        y -= (scaledHeight - self.overallHeight()) / 2

        return (scaledWidth, scaledHeight, x, y)

    def buildViewbox(self, scale, width, height):
        scaledWidth, scaledHeight, x, y = self.calculateOffset(
            scale, width, height)

        return '%s %s %s %s' % (toNumberString(x), toNumberString(y), toNumberString(scaledWidth), toNumberString(scaledHeight))

    def adaptFromShapes(self, objects):
        for s in objects:
            bb = s.BoundBox

            self.update(bb.XMin, bb.YMin, bb.XMax, bb.YMax)

    def adaptFromDrafts(self, objects):
        for o in objects:
            objectType = Draft.getType(o)
            if objectType == "Dimension":
                start = o.ViewObject.Proxy.p2
                end = o.ViewObject.Proxy.p3
                start = getProj(start, self.plane)
                end = getProj(end, self.plane)

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


class FaceData:
    def __init__(self, originalFace, color, pattern_type, reorientedFace=None):
        self.originalFace = originalFace
        self.color = color
        self.pattern_type = pattern_type
        self.reorientedFace = reorientedFace

    def matches(self, otherFace):
        if not self.reorientedFace or not otherFace.reorientedFace:
            return False

        selfPoints = [(round(v.Point.x, 5), round(v.Point.y, 5))
                      for v in self.reorientedFace.Vertexes]
        otherPoints = [(round(v.Point.x, 5), round(v.Point.y, 5))
                       for v in otherFace.reorientedFace.Vertexes]

        if len(selfPoints) != len(otherPoints):
            return False

        # Find the first point, that is not in the other Faces points.
        # When no point is missing, the faces can be considered as equals
        for p in selfPoints:
            if not p in otherPoints:
                return False

        return True

    def correctlyOriented(self):
        if not self.reorientedFace:
            return True

        yValues = set([round(v.Point.y, 5)
                       for v in self.reorientedFace.Vertexes])
        xValues = set([round(v.Point.x, 5)
                       for v in self.reorientedFace.Vertexes])

        # When all y values or x for the vertices are the same, the face will be a single line in the SVG. So we can skip it entirely

        return len(yValues) > 1 and len(xValues) > 1


def indexOfFace(faceList, face):
    if not faceList:
        return None

    for i, f in enumerate(faceList):
        if face.matches(f):
            return i

    return None


class Renderer:
    def __init__(self, placement):
        import WorkingPlane

        self.reset()
        self.wp = WorkingPlane.plane()
        self.wp.setFromPlacement(placement, rebase=True)

        if DEBUG:
            print("Renderer initialized on %s. %s, %s" %
                  (self.wp, self.wp.getPlacement().Base, self.wp.getNormal()))

    def reset(self):
        "removes all faces from this renderer"
        self.objectShapes = []
        self.windowShapes = []
        self.resetFlags()

    def resetFlags(self):
        "resets all flags of this renderer"
        self.oriented = False
        self.trimmed = False
        self.sorted = False
        self.iscut = False
        self.joined = False
        self.secondaryFaces = []
        self.sections = []
        self.windows = []
        self.hiddenEdges = []

    def addObjects(self, objs):
        "add objects to this renderer"

        for o in objs:
            if o.isDerivedFrom("Part::Feature"):
                color = o.ViewObject.ShapeColor
                if o.Shape.Faces:
                    self.objectShapes.append(
                        [o.Shape, color, getPatternType(o)])

        self.resetFlags()

    def addWindows(self, objs):
        "add objects to this renderer"

        for o in objs:
            if o.isDerivedFrom("Part::Feature"):
                color = o.ViewObject.ShapeColor
                if o.Shape.Faces:
                    self.windowShapes.append(
                        [o.Shape, color, getPatternType(o)])

        self.resetFlags()

        if DEBUG:
            print("adding ", len(self.objects), " objects, ")

    def reorient(self):
        "reorients the faces on the WP"

        if self.secondaryFaces:
            self.secondaryFaces = [self.projectFace(
                f) for f in self.secondaryFaces]
        if self.sections:
            self.sections = [self.projectFace(f) for f in self.sections]
        if self.windows:
            self.windows = [self.projectFace(f) for f in self.windows]
        if self.hiddenEdges:
            self.hiddenEdges = [self.projectEdge(e) for e in self.hiddenEdges]

        self.oriented = True

    def removeDuplicates(self):
        if not self.secondaryFaces:
            return

        newSecondaryFaces = []

        for face in self.secondaryFaces:
            # If the face is already in a section, do not add it to the secondary faces
            if not face or indexOfFace(self.sections, face) is not None:
                continue

            i = indexOfFace(newSecondaryFaces, face)

            # if the face already exists, remove it from the list
            # Adding the new face again preserves the original face order
            if i is not None:
                del newSecondaryFaces[i]

            newSecondaryFaces.append(face)

        self.secondaryFaces = newSecondaryFaces

    def filterWrongOrientedFaces(self):
        if self.secondaryFaces:
            self.secondaryFaces = [
                f for f in self.secondaryFaces if f and f.correctlyOriented()]
        if self.sections:
            self.sections = [
                f for f in self.sections if f and f.correctlyOriented()]
        if self.windows:
            self.windows = [
                f for f in self.windows if f and f.correctlyOriented()]

    def sort(self):
        if self.secondaryFaces:
            self.sortFaces(self.secondaryFaces)
        if self.sections:
            self.sortFaces(self.sections)
        if self.windows:
            self.sortFaces(self.windows)
        if self.hiddenEdges:
            self.sortFaces(self.hiddenEdges)

    def sortFaces(self, faces):
        def sortX(entry):
            shape = entry.originalFace

            return shape.BoundBox.XMax

        def sortY(entry):
            shape = entry.originalFace

            return shape.BoundBox.YMax

        def sortZ(entry):
            shape = entry.originalFace

            return shape.BoundBox.ZMax

        normal = self.wp.getNormal()

        normalx = round(normal.x, 3)
        normaly = round(normal.y, 3)
        normalz = round(normal.z, 3)

        if normalz > 0:
            faces.sort(key=sortZ)
        elif normalx > 0:
            faces.sort(key=sortX)
        elif normaly > 0:
            faces.sort(key=sortY)
        elif normalz < 0:
            faces.sort(key=sortZ, reverse=True)
        elif normalx < 0:
            faces.sort(key=sortX, reverse=True)
        elif normaly < 0:
            faces.sort(key=sortY, reverse=True)

    def projectFace(self, face):
        "projects a single face on the WP"

        wires = []
        if not face.originalFace.Wires:
            if DEBUG:
                print("Error: Unable to project face on the WP")
            return None
        norm = face.originalFace.normalAt(0, 0)
        for w in face.originalFace.Wires:
            verts = []
            edges = Part.__sortEdges__(w.Edges)
            for e in edges:
                v = e.Vertexes[0].Point
                v = self.wp.getLocalCoords(v)
                verts.append(v)
            verts.append(verts[0])
            if len(verts) > 2:
                wires.append(Part.makePolygon(verts))
        try:
            sh = ArchCommands.makeFace(wires)
        except:
            if DEBUG:
                print("Error: Unable to project face on the WP")
            return None
        else:
            # restoring flipped normals
            vnorm = self.wp.getLocalCoords(norm)
            if vnorm.getAngle(sh.normalAt(0, 0)) > 1:
                sh.reverse()

            return FaceData(face.originalFace, face.color, face.pattern_type, sh)

    def projectEdge(self, edge):
        "projects a single edge on the WP"
        if len(edge.Vertexes) > 1:
            v1 = self.wp.getLocalCoords(edge.Vertexes[0].Point)
            v2 = self.wp.getLocalCoords(edge.Vertexes[-1].Point)
            return Part.LineSegment(v1, v2).toShape()
        return edge

    def doCut(self, cutplane, hidden, clip, clipDepth, shapes):
        objectShapes = []
        sections = []
        faces = []

        shps = []

        for sh in shapes:
            shps.append(sh[0])

        cutface, cutvolume, invcutvolume = ArchCommands.getCutVolume(
            cutplane, shps, clip=clip)

        if not cutvolume:
            cutface = cutplane
            cutnormal = cutplane.normalAt(0.5, 0.5)
            cutvolume = cutplane.extrude(cutnormal)
            cutnormal = cutnormal.negative()
            invcutvolume = cutplane.extrude(cutnormal)

        if DEBUG:
            print('cutface: %s, cutvolume: %s, invcutvolume: %s' %
                  (cutface, cutvolume, invcutvolume))

        if cutface and cutvolume:

            for sh in shapes:
                for sol in sh[0].Solids:
                    c = sol.cut(cutvolume)
                    objectShapes.append([c]+sh[1:])

                    for f in c.Faces:
                        if DraftGeomUtils.isCoplanar([f, cutface]):
                            sections.append(FaceData(f, sh[1], sh[2]))
                        else:
                            faces.append(FaceData(f, sh[1], sh[2]))

                    if hidden:
                        c = sol.cut(invcutvolume)
                        self.hiddenEdges.extend(c.Edges)

        if clipDepth > 0:
            faces = [f for f in faces if self.isInRange(
                f.originalFace, clipDepth)]

        return (objectShapes, sections, faces)

    def cut(self, cutplane, hidden=False, clip=False, clipDepth=0):
        "Cuts through the objectShapes with a given cut plane and builds section faces"
        if DEBUG:
            print("\n\n======> Starting cut\n\n")

        if self.iscut:
            return

        if not self.objectShapes:
            if DEBUG:
                print("No objects to make sections")
        else:
            objectShapes, sections, faces = self.doCut(
                cutplane, hidden, clip, clipDepth, self.objectShapes)

            self.objectShapes = objectShapes
            self.sections = sections
            self.secondaryFaces = faces

            if DEBUG:
                print("Built ", len(self.sections), " sections")

        if not self.windowShapes:
            if DEBUG:
                print("No objects to make windows")
        else:
            windowShapes, windows, faces = self.doCut(
                cutplane, hidden, clip, clipDepth, self.windowShapes)

            self.windowShapes = windowShapes
            self.windows = windows

            if DEBUG:
                print("Built ", len(self.sections), " windows")

        self.sort()

        self.iscut = True
        self.oriented = False
        self.trimmed = False
        self.sorted = False
        self.joined = False

        if DEBUG:
            print("\n\n======> Finished cut\n\n")

    def getFill(self, fill):
        "Returns a SVG fill value"
        r = str(hex(int(fill[0]*255)))[2:].zfill(2)
        g = str(hex(int(fill[1]*255)))[2:].zfill(2)
        b = str(hex(int(fill[2]*255)))[2:].zfill(2)

        return "#" + r + g + b

    def getPatternTemplate(self, fill, opacity, pattern_type):
        if pattern_type is None:
            pattern_type = "DEFAULT"

        if not pattern_type in PATTERN_TEMPLATES:
            print("Unknown PatternType " + pattern_type)
            pattern_type = "DEFAULT"

        pattern_id = "%s-%s-%s" % (pattern_type.lower(),
                                   fill.replace("#", ""), str(opacity))

        return (PATTERN_TEMPLATES[pattern_type], pattern_id)

    def getPattern(self, color, pattern_type, opacity=1):
        fill = self.getFill(color)
        pattern, pattern_id = self.getPatternTemplate(
            fill, opacity, pattern_type)

        if not pattern_id in self.patterns:
            pattern = pattern.replace("PATTERN_ID", pattern_id)
            pattern = pattern.replace("PATTERN_COLOR", fill)
            pattern = pattern.replace("PATTERN_OPACITY", str(opacity))

            self.patterns[pattern_id] = pattern

        return pattern_id

    def getPathData(self, w):
        """Returns a SVG path data string from a 2D wire
        The Y Axis in the SVG Coordinate system is reversed from the FreeCAD Coordinate System.
        So we change the y coordinates accordingly
        """
        def toCommand(command, x, y):
            return '%s %s %s ' % (command, toNumberString(x), toNumberString(-y))

        edges = Part.__sortEdges__(w.Edges)

        v = edges[0].Vertexes[0].Point
        svg = toCommand('M', v.x, v.y)

        for e in edges:
            if (DraftGeomUtils.geomType(e) == "Line") or (DraftGeomUtils.geomType(e) == "BSplineCurve"):
                v = e.Vertexes[-1].Point
                svg += toCommand('L', v.x, v.y)
            elif DraftGeomUtils.geomType(e) == "Circle":
                r = e.Curve.Radius
                v = e.Vertexes[-1].Point

                svg += 'A %s %s 0 0 1 %s %s ' % (toNumberString(r),
                                                 toNumberString(r), toNumberString(v.x), toNumberString(-v.y))

        if len(edges) > 1:
            svg += 'Z '

        return svg

    def getPatternSVG(self):
        if not hasattr(self, "patterns"):
            return ''

        patternsvg = ''

        for pattern in self.patterns.values():
            patternsvg += pattern + '\n'

        return patternsvg

    def getSectionSVG(self, linewidth):
        sectionsvg = ''

        for f in self.sections:
            if f:
                fill = 'url(#' + self.getPattern(f.color, f.pattern_type) + ')'

                pathdata = ''

                for w in f.reorientedFace.Wires:
                    pathdata += self.getPathData(w)

                current = PATH_TEMPLATE.replace("PATH_FILL", fill)
                current = current.replace("STROKE_WIDTH", str(linewidth))
                current = current.replace("PATH_DATA", pathdata)

                sectionsvg += current + "\n"

        return sectionsvg

    def getWindowSVG(self, linewidth):
        windowsvg = ''

        for f in self.windows:
            if f:
                fill = 'url(#' + self.getPattern(f.color, f.pattern_type) + ')'

                pathdata = ''

                for w in f.reorientedFace.Wires:
                    pathdata += self.getPathData(w)

                current = PATH_TEMPLATE.replace("PATH_FILL", fill)
                current = current.replace("STROKE_WIDTH", str(linewidth))
                current = current.replace("PATH_DATA", pathdata)

                windowsvg += current + "\n"

        return windowsvg

    def isInRange(self, face, maxDistance):
        if maxDistance <= 0:
            return False

        distance = face.CenterOfMass.distanceToPlane(
            self.wp.getPlacement().Base, self.wp.getNormal())

        if distance < 0:
            distance *= -1

        if distance <= maxDistance:
            return True

        return False

    def getSecondaryFacesSVG(self, linewidth, faceHighlightDistance, highlightLineWith):
        secondaryFacesSvg = ''

        for f in self.secondaryFaces:
            if f:
                patternOpacity = 0.1
                shouldHightlight = self.isInRange(
                    f.originalFace, faceHighlightDistance)

                if shouldHightlight:
                    linewidth = highlightLineWith
                    patternOpacity = 1

                fill = 'url(#' + self.getPattern(f.color,
                                                 f.pattern_type, patternOpacity) + ')'

                pathdata = ''

                for w in f.reorientedFace.Wires:
                    pathdata += self.getPathData(w)

                current = PATH_TEMPLATE.replace("PATH_FILL", fill)
                current = current.replace("STROKE_WIDTH", str(linewidth))
                current = current.replace("PATH_DATA", pathdata)

                secondaryFacesSvg += current + "\n"

        return secondaryFacesSvg

    def getSvgParts(self, faceHighlightDistance=0):
        "Returns all svg parts we cut"
        if not self.oriented:
            self.reorient()
            self.filterWrongOrientedFaces()
            self.removeDuplicates()

        self.patterns = {}

        sectionSvg = self.getSectionSVG("SECTION_STROKE_WIDTH")
        windowSvg = self.getWindowSVG("WINDOW_STROKE_WIDTH")
        secondaryFacesSvg = self.getSecondaryFacesSVG(
            "SECONDARY_STROKE_WIDTH", faceHighlightDistance, "SECTION_STROKE_WIDTH")
        patternSvg = self.getPatternSVG()

        boundBox = self.buildBoundBox()

        return {
            "patterns": patternSvg,
            "sections": sectionSvg,
            "secondaryFaces": secondaryFacesSvg,
            "windows": windowSvg,
            "boundBox": boundBox
        }

    def buildBoundBox(self):
        boundBox = BoundBox(self.wp)

        if self.secondaryFaces:
            boundBox.adaptFromShapes(
                [f.reorientedFace for f in self.secondaryFaces if f])
        if self.sections:
            boundBox.adaptFromShapes(
                [f.reorientedFace for f in self.sections if f])
        if self.windows:
            boundBox.adaptFromShapes(
                [f.reorientedFace for f in self.windows if f])
        if self.hiddenEdges:
            boundBox.adaptFromShapes(
                [f.reorientedFace for f in self.hiddenEdges if f])

        return boundBox

    # def getHiddenSVG(self, linewidth=0.02):
    #     "Returns a SVG fragment from cut geometry"
    #     if DEBUG:
    #         print("Printing ", len(self.sections), " hidden faces")
    #     if not self.oriented:
    #         self.reorient()
    #     svg = '<g stroke="#000000" stroke-width="' + \
    #         str(linewidth) + '" style="stroke-width:' + str(linewidth)
    #     svg += ';stroke-miterlimit:1;stroke-linejoin:round;stroke-dasharray:0.09,0.05;fill:none;">\n'
    #     for e in self.hiddenEdges:
    #         svg += '<path '
    #         svg += 'd="'
    #         svg += self.getPathData(e)
    #         svg += '"/>\n'
    #     svg += '</g>\n'
    #     return svg


if __name__ == "__main__":
    def calculateCutPlane(pl, l=10000, h=10000):
        import Part

        p = Part.makePlane(l, h, FreeCAD.Vector(
            l/2, -h/2, 0), FreeCAD.Vector(0, 0, -1))

        # make sure the normal direction is pointing outwards, you never know what OCC will decide...
        if p.normalAt(0, 0).getAngle(pl.Rotation.multVec(FreeCAD.Vector(0, 0, 1))) > 1:
            p.reverse()

        p.Placement = pl

        # Part.show(p)

        return p

    # Top
    # pl = FreeCAD.Placement(
    #     FreeCAD.Vector(0, 0, 1200), FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 0))
    # Front
    # pl = FreeCAD.Placement(
    #     FreeCAD.Vector(0, -1000, 0), FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90))
    # Right
    pl = FreeCAD.Placement(
        FreeCAD.Vector(16000, 0, 0), FreeCAD.Rotation(FreeCAD.Vector(0.577, 0.577, 0.577), 120))
    # Back
    # pl = FreeCAD.Placement(
    #     FreeCAD.Vector(0, 15000, 0), FreeCAD.Rotation(FreeCAD.Vector(0, -0.71, -0.71), 180))

    # print(pl)

    cutplane = calculateCutPlane(pl)

    DEBUG = True

    render = Renderer(pl)
    render.addObjects([FreeCAD.ActiveDocument.Wall100,
                       FreeCAD.ActiveDocument.Wall015])
    # render.addObjects(FreeCAD.ActiveDocument.Objects)
    render.cut(cutplane, clip=False)

    parts = render.getSvgParts(0)

    boundBox = parts["boundBox"]
    # boundBox.adaptFromDrafts([FreeCAD.ActiveDocument.Dimension005])

    width = 420
    height = 297

    # print("---patterns---")
    # print(parts["patterns"])
    # print("---sections---")
    # print(parts["sections"])
    # print("---windows---")
    # print(parts["windows"])
    # print("---secondaryFaces---")
    # print(parts["secondaryFaces"])

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

            <g id="secondary">
                SECONDARY_SVG
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

            <g id="information">
                INFORMATION_SVG
            </g>
        </g>
    </g>
</svg>
"""

    template = template.replace(
        "VIEWBOX_VALUES", boundBox.buildViewbox(1/50, width, height))
    template = template.replace("WIDTH", toNumberString(width))
    template = template.replace("HEIGHT", toNumberString(height))
    template = template.replace("PATTERN_SVG", parts["patterns"])
    template = template.replace("SECONDARY_SVG", parts["secondaryFaces"])
    template = template.replace("SECTION_SVG", parts["sections"])
    template = template.replace("WINDOW_SVG", parts["windows"])
    template = template.replace("TEXT_FONT_SIZE", str(240))
    template = template.replace("SECTION_STROKE_WIDTH", str(3))
    template = template.replace("WINDOW_STROKE_WIDTH", str(1))
    template = template.replace("SECONDARY_STROKE_WIDTH", str(1))

    file_object = open(
        "C:\\Meine Daten\\freecad\\samples\\SectionPlane\\Export.svg", "w")
    file_object.write(template)
    file_object.close()
