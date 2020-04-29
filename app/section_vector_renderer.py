import FreeCAD
import math
import re
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
    x="0" y="0" width="${5}" height="${5}">
        <g>
            <rect width="${5}" height="${5}"
                style="stroke:none; fill:#ffffff" />
            <path style="stroke:PATTERN_COLOR; stroke-width:${0.2}; stroke-linecap:butt; stroke-linejoin:miter; fill:none; opacity:PATTERN_OPACITY" 
                  d="M0,0 l${5},${5}" />
        </g>
</pattern>
"""

WOOD_PATTERN_TEMPLATE = """
<pattern
    id="PATTERN_ID"
    patternUnits="userSpaceOnUse"
    x="0" y="0" width="${5}" height="${5}">
        <g>
            <rect width="${5}" height="${5}"
                style="stroke:none; fill:#ffffff" />
            <path style="stroke:PATTERN_COLOR; stroke-width:${0.2}; stroke-linecap:butt; stroke-linejoin:miter; fill:none; opacity:PATTERN_OPACITY" 
                  d="M${5},0 L0,${5}" />
        </g>
</pattern>
"""

INSULATION_HARD_PATTERN_TEMPLATE = """
<pattern
    id="PATTERN_ID"
    patternUnits="userSpaceOnUse"
    x="0" y="0" width="${2.5}" height="${2.5}">
        <g>
            <rect width="${2.5}" height="${2.5}"
                style="stroke:none; fill:#ffffff" />
            <path style="stroke:PATTERN_COLOR; stroke-width:${0.2}; stroke-linecap:butt; stroke-linejoin:miter; fill:none; opacity:PATTERN_OPACITY" 
                  d="M 0,0 ${2.5},${0.625} 0,${1.25} ${2.5},${1.875} 0,${2.5}" />
        </g>
</pattern>
"""

INSULATION_SOFT_PATTERN_TEMPLATE = """
<pattern
    id="PATTERN_ID"
    patternUnits="userSpaceOnUse"
    x="0" y="0" width="${5}" height="${5}">
        <g>
            <rect width="${5}" height="${5}"
                style="stroke:none; fill:#ffffff" />
            <path style="stroke:PATTERN_COLOR; stroke-width:${0.2}; stroke-linecap:butt; stroke-linejoin:miter; fill:none; opacity:PATTERN_OPACITY" 
                  d="M ${1.25},0 ${3.75},${1.25} ${1.25},${2.5} ${3.75},${3.75} ${1.25},${5} M ${1.25},0 C ${1.25},0 0,${0.5} 0,${1.25} 0,${2} ${1.25},${2.5} ${1.25},${2.5} m 0,0 C ${1.25},${2.5} 0,${3} 0,${3.75} 0,${4.5} ${1.25},${5} ${1.25},${5} M ${3.75},${3.75} c 0,0 ${1.25},${0.5} ${1.25},${1.25} C ${5},${5.75} ${3.75},${6.25} ${3.75},${6.25} m 0,-${7.5} c 0,0 ${1.25},${0.5} ${1.25},${1.25} 0,${0.75} -${1.25},${1.25} -${1.25},${1.25} m 0,0 c 0,0 ${1.25},${0.5} ${1.25},${1.25} 0,${0.75} -${1.25},${1.25} -${1.25},${1.25}" />
        </g>
</pattern>
"""

WINDOW_PATTERN_TEMPLATE = """
<pattern
    id="PATTERN_ID"
    patternUnits="userSpaceOnUse"
    x="0" y="0" width="${2.5}" height="${2.5}">
        <g>
            <rect width="${2.5}" height="${2.5}"
                style="stroke:none; fill:#ffffff" />
            <path style="stroke:PATTERN_COLOR; stroke-width:${0.2}; stroke-linecap:butt; stroke-linejoin:miter; fill:none; opacity:PATTERN_OPACITY" 
                  d="M 0,${2.5} ${2.5},0 M 0,0 ${2.5},${2.5}" />
        </g>
</pattern>
"""

PATH_TEMPLATE = """
<path d="PATH_DATA" stroke="STROKE_COLOR" stroke-width="STROKE_WIDTH"
      style="fill:PATH_FILL; fill-rule: evenodd; stroke-width:STROKE_WIDTH; stroke-miterlimit:1; stroke-linejoin:round; stroke-dasharray:DASH_ARRAY; fill-opacity:FILL_OPACITY"/>
"""

SECTION_CUT_TEMPLATE = """
<g stroke-width="STROKE_WIDTH"
   style="stroke-width:STROKE_WIDTH; stroke-miterlimit:1; stroke-linejoin:round; stroke-dasharray:105,26,13,26;stroke-dashoffset:0;"
   stroke="#000000">
    <path d="PATH_DATA" />
    <path d="ARROW_START" transform="rotate(ARROW_START_ROTATION)"/>
    <path d="ARROW_END" transform="rotate(ARROW_END_ROTATION)"/>
    TEXT_START
    TEXT_END
</g>
"""

TEXT_TEMPLATE = """
<text
        x="TEXT_POSITION_X"
        y="TEXT_POSITION_Y"
        style="font-size:TEXT_FONT_SIZE;font-family:Arial;letter-spacing:0px;word-spacing:0px;fill:#000000;text-anchor:TEXT_ANCHOR;text-align:center;stroke:none;"
        transform="rotate(TEXT_ROTATION)">
            TEXT_CONTENT
</text>
"""

PATTERN_TEMPLATES = {
    "DEFAULT": DEFAULT_PATTERN_TEMPLATE,
    "WOOD": WOOD_PATTERN_TEMPLATE,
    "INSULATION_HARD": INSULATION_HARD_PATTERN_TEMPLATE,
    "INSULATION_SOFT": INSULATION_SOFT_PATTERN_TEMPLATE,
    "WINDOW": WINDOW_PATTERN_TEMPLATE
}

PATTERN_NUMBER_REGEX = re.compile(r'\$\{([0-9\.]+)\}')


def scalePatterns(patternSVG, scale):
    availableNumbers = set([(n, float(n))
                            for n in PATTERN_NUMBER_REGEX.findall(patternSVG)])

    for text, n in availableNumbers:
        patternSVG = patternSVG.replace(
            '${' + text + '}', toNumberString(n / scale, 6))

    return patternSVG


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


def isEdgeOnPlane(edge, plane):
    precision = DraftVecUtils.precision()
    planeBase = plane.CenterOfMass
    planeNormal = plane.normalAt(0.5, 0.5)

    points = [v.Point for v in edge.Vertexes]

    for p in points:
        distance = p.distanceToPlane(planeBase, planeNormal)

        if distance < 0:
            distance = distance * -1

        if distance > precision:
            return False

    return True


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
        self.points = None

    def matches(self, otherFace):
        selfPoints = self.getPoints()
        otherPoints = otherFace.getPoints()

        if not selfPoints or not otherPoints:
            return False

        if len(selfPoints) != len(otherPoints):
            return False

        # Find the first point, that is not in the other Faces points.
        # When no point is missing, the faces can be considered as equals
        for p in selfPoints:
            if not p in otherPoints:
                return False

        return True
    
    def getPoints(self):
        if self.points:
            return self.points

        if not self.reorientedFace:
            return None
        
        self.points = [(round(v.Point.x, 5), round(v.Point.y, 5))
                        for v in self.reorientedFace.Vertexes]
        
        return self.points

    def correctlyOriented(self, planeNormal):
        if not self.originalFace:
            return True

        faceNormal = self.originalFace.normalAt(0, 0)
        angle = math.degrees(faceNormal.getAngle(planeNormal))
        angle = round(angle, DraftVecUtils.precision())

        return angle != 90

class SectionCutData:
    def __init__(self, face, text):
        self.face = face
        self.text = text

class MarkerData:
    def __init__(self, face, text, color):
        self.face = face
        self.text = text
        self.color = color

class CutResult:
    def __init__(self, objectShapes, sections, faces, cutvolume, cutface):
        self.objectShapes = objectShapes
        self.sections = sections
        self.faces = faces
        self.cutvolume = cutvolume
        self.cutface = cutface


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
        self.sectionCutShapes = []
        self.markerShapes = []
        self.resetFlags()

    def resetFlags(self):
        "resets all flags of this renderer"
        self.duplicatesRemoved = False
        self.sorted = False
        self.iscut = False
        self.secondaryFaces = []
        self.sections = []
        self.windows = []
        self.hiddenEdges = []
        self.sectionCuts = []

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

    def addSectionCuts(self, sections):
        "add objects to this renderer"

        for s in sections:
            label = s.Label

            if hasattr(s, "CutLetter") and s.CutLetter is not None:
                label = s.CutLetter
            
            sectionCutCutPlane = s.Proxy.calculateCutPlane(s)
            data = SectionCutData(sectionCutCutPlane, label)

            self.sectionCutShapes.append(data)

        self.resetFlags()
    
    def addMarkers(self, markers):
        "add objects to this renderer"

        for m in markers:
            color = m.ViewObject.LineColor
            face = m.Shape.Faces[0]
            self.markerShapes.append(MarkerData(face, m.Label, color))

        self.resetFlags()

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

    def sort(self):
        normal = self.wp.getNormal()

        normalx = round(normal.x, 3)
        normaly = round(normal.y, 3)
        normalz = round(normal.z, 3)

        if self.secondaryFaces:
            self.sortFaces(self.secondaryFaces, normalx, normaly, normalz)
        if self.sections:
            self.sortFaces(self.sections, normalx, normaly, normalz)
        if self.windows:
            self.sortFaces(self.windows, normalx, normaly, normalz)
        if self.hiddenEdges:
            self.sortFaces(self.hiddenEdges, normalx, normaly, normalz)

    def sortFaces(self, faces, normalx, normaly, normalz):
        def sortX(entry):
            shape = entry.originalFace

            return shape.BoundBox.XMax

        def sortY(entry):
            shape = entry.originalFace

            return shape.BoundBox.YMax

        def sortZ(entry):
            shape = entry.originalFace

            return shape.BoundBox.ZMax

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

            face.reorientedFace = sh

            return face

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

        # self.reorient()
        # self.filterWrongOrientedFaces()

        for sh in shapes:
            shps.append(sh[0])

        cutface, cutvolume, invcutvolume = ArchCommands.getCutVolume(
            cutplane, shps, clip=clip)
        planeNormal = self.wp.getNormal()
        planeNormal.normalize()

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
                        faceData = FaceData(f, sh[1], sh[2])
                        faceData = self.projectFace(faceData)
                        # TODO: Create temporary face list and filter duplicate faces
                        # Do isCoplanar check later on, when duplicate faces are removed

                        if faceData.correctlyOriented(planeNormal):
                            if DraftGeomUtils.isCoplanar([f, cutface]):
                                sections.append(faceData)
                            else:
                                faces.append(faceData)

                    if hidden:
                        c = sol.cut(invcutvolume)
                        # self.projectEdge(e)
                        self.hiddenEdges.extend(c.Edges)

        if clipDepth > 0:
            faces = [f for f in faces if self.isInRange(
                f.originalFace, clipDepth)]

        return CutResult(objectShapes, sections, faces, cutvolume, cutface)

    def doCutSectionCuts(self, cutvolume, cutface, sectionCutShapes):
        edges = []

        if cutvolume:
            for s in sectionCutShapes:
                sh = s.face
                c = sh.cut(cutvolume)
                normal = sh.normalAt(0.5, 0.5)

                for e in c.Edges:
                    if isEdgeOnPlane(e, cutface):
                        e = self.projectEdge(e)
                        edges.append((e, normal, s.text))

        return edges

    def cut(self, cutplane, hidden=False, clip=False, clipDepth=0):
        "Cuts through the objectShapes with a given cut plane and builds section faces"
        if DEBUG:
            print("\n\n======> Starting cut\n\n")

        if self.iscut:
            return
        
        objectCutVolume = None
        objectCutFace = None

        if not self.objectShapes:
            if DEBUG:
                print("No objects to make sections")
        else:
            # We always use a clipping cut here. The section plane needs to be big enough
            # But we need it clipping for the sectionCutShapes later on
            result = self.doCut(
                cutplane, hidden, True, clipDepth, self.objectShapes)

            self.objectShapes = result.objectShapes
            self.sections = result.sections
            self.secondaryFaces = result.faces
            objectCutVolume = result.cutvolume
            objectCutFace = result.cutface

            if DEBUG:
                print("Built ", len(self.sections), " sections")

        if not self.windowShapes:
            if DEBUG:
                print("No objects to make windows")
        else:
            result = self.doCut(
                cutplane, hidden, clip, clipDepth, self.windowShapes)

            self.windowShapes = result.objectShapes
            self.windows = result.sections

            if DEBUG:
                print("Built ", len(self.windows), " windows")

        if not self.sectionCutShapes:
            if DEBUG:
                print("No objects to make sectionCuts")
        else:
            self.sectionCuts = self.doCutSectionCuts(
                objectCutVolume, objectCutFace, self.sectionCutShapes)

            if DEBUG:
                print("Built ", len(self.sectionCuts), " sectionCuts")

        self.sort()

        self.iscut = True
        self.sorted = True
        self.duplicatesRemoved = False

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
                current = current.replace("FILL_OPACITY", "1")
                current = current.replace("DASH_ARRAY", "none")
                current = current.replace("STROKE_COLOR", "#000000")
                current = current.replace("STROKE_WIDTH", str(linewidth))
                current = current.replace("PATH_DATA", pathdata)

                sectionsvg += current + "\n"

        return sectionsvg
    
    def getMarkerSVG(self, linewidth):
        markersvg = ''

        for m in self.markerShapes:
            # fill = 'url(#' + self.getPattern(f.color, f.pattern_type) + ')'

            pathdata = ''
            fillColor = self.getFill(m.color)

            reorientedFace = self.projectFace(FaceData(m.face, None, None)).reorientedFace
            textPos = reorientedFace.CenterOfMass

            for w in reorientedFace.Wires:
                pathdata += self.getPathData(w)

            path = PATH_TEMPLATE.replace("PATH_FILL", fillColor)
            path = path.replace("FILL_OPACITY", "0.04")
            path = path.replace("DASH_ARRAY", "100,50")
            path = path.replace("STROKE_COLOR", fillColor)
            path = path.replace("STROKE_WIDTH", str(linewidth))
            path = path.replace("PATH_DATA", pathdata)

            text = TEXT_TEMPLATE.replace("TEXT_CONTENT", m.text)
            text = text.replace("TEXT_FONT_SIZE", "SMALL_TEXT_FONT_SIZE")
            text = text.replace("TEXT_ANCHOR", "middle")
            text = text.replace("TEXT_POSITION_X", toNumberString(textPos.x))
            text = text.replace("TEXT_POSITION_Y", toNumberString(-textPos.y))
            text = text.replace("TEXT_ROTATION", "0")

            markersvg += "%s %s\n" % (path, text)

        return markersvg


    def getSectionCutSvg(self, linewidth):
        svg = ''
        arrowSize = 100
        referenceAxis = FreeCAD.Vector(0, -1, 0)

        def rotation(x, y, angle):
            angleString = toNumberString(angle)
            xString = toNumberString(x)
            yString = toNumberString(y)

            return '%s %s %s' % (angleString, xString, yString)

        def arrowPath(basePoint):
            baseX = basePoint.x
            baseY = -basePoint.y
            baseXString = toNumberString(baseX)
            baseYString = toNumberString(baseY)

            return "M %s %s L %s %s L %s %s Z" % (toNumberString(baseX - arrowSize), baseYString, toNumberString(baseX + arrowSize), baseYString, baseXString, toNumberString(baseY + arrowSize))
        
        def text(basePoint, normal, angle, text):
            offset = FreeCAD.Vector(normal.x, normal.y, normal.z).multiply(100)
            actualBase = FreeCAD.Vector(basePoint.x, basePoint.y, basePoint.z).sub(offset)
            baseX = actualBase.x
            baseY = -actualBase.y
            baseXString = toNumberString(baseX)
            baseYString = toNumberString(baseY)

            svg = TEXT_TEMPLATE.replace("TEXT_POSITION_X", baseXString)
            text = text.replace("TEXT_ANCHOR", "middle")
            svg = svg.replace("TEXT_POSITION_Y", baseYString)
            svg = svg.replace("TEXT_CONTENT", text)
            svg = svg.replace("TEXT_ROTATION", rotation(baseX, baseY, angle))

            return svg

        for s in self.sectionCuts:
            edge = s[0]
            normal = s[1]
            normal = normal.negative()
            label = s[2]

            pathdata = self.getPathData(edge)
            rotationAngle = math.degrees(normal.getAngle(referenceAxis))
            start = edge.Vertexes[0].Point
            end = edge.Vertexes[1].Point

            arrowStart = arrowPath(start)
            arrowEnd = arrowPath(end)

            textStart = text(start, normal, rotationAngle, label)
            textEnd = text(end, normal, rotationAngle, label)

            current = SECTION_CUT_TEMPLATE.replace("PATH_DATA", pathdata)
            current = current.replace("STROKE_WIDTH", str(linewidth))
            current = current.replace(
                "ARROW_START_ROTATION", rotation(start.x, -start.y, rotationAngle))
            current = current.replace(
                "ARROW_END_ROTATION", rotation(end.x, -end.y, rotationAngle))
            current = current.replace("ARROW_START", arrowStart)
            current = current.replace("ARROW_END", arrowEnd)
            current = current.replace("TEXT_START", textStart)
            current = current.replace("TEXT_END", textEnd)

            svg += current + "\n"

        return svg

    def getWindowSVG(self, linewidth):
        windowsvg = ''

        for f in self.windows:
            if f:
                fill = 'url(#' + self.getPattern(f.color, f.pattern_type) + ')'

                pathdata = ''

                for w in f.reorientedFace.Wires:
                    pathdata += self.getPathData(w)

                current = PATH_TEMPLATE.replace("PATH_FILL", fill)
                current = current.replace("FILL_OPACITY", "1")
                current = current.replace("DASH_ARRAY", "none")
                current = current.replace("STROKE_COLOR", "#000000")
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
                current = current.replace("FILL_OPACITY", "1")
                current = current.replace("DASH_ARRAY", "none")
                current = current.replace("STROKE_COLOR", "#000000")
                current = current.replace("STROKE_WIDTH", str(linewidth))
                current = current.replace("PATH_DATA", pathdata)

                secondaryFacesSvg += current + "\n"

        return secondaryFacesSvg

    def getSvgParts(self, faceHighlightDistance=0):
        "Returns all svg parts we cut"
        if not self.duplicatesRemoved:
            self.removeDuplicates()

            self.duplicatesRemoved = True

        self.patterns = {}

        sectionSvg = self.getSectionSVG("SECTION_STROKE_WIDTH")
        windowSvg = self.getWindowSVG("WINDOW_STROKE_WIDTH")
        secondaryFacesSvg = self.getSecondaryFacesSVG(
            "SECONDARY_STROKE_WIDTH", faceHighlightDistance, "SECTION_STROKE_WIDTH")
        patternSvg = self.getPatternSVG()
        sectionCutSvg = self.getSectionCutSvg("SECTION_CUT_STROKE_WIDTH")
        markerSvg = self.getMarkerSVG("MARKER_STROKE_WIDTH")
        boundBox = self.buildBoundBox()

        return {
            "patterns": patternSvg,
            "sections": sectionSvg,
            "secondaryFaces": secondaryFacesSvg,
            "windows": windowSvg,
            "boundBox": boundBox,
            "sectionCuts": sectionCutSvg,
            "markers": markerSvg
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
        if self.sectionCuts:
            boundBox.adaptFromShapes([s[0] for s in self.sectionCuts])

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
    import time
    import tracemalloc

    def calculateCutPlane(pl, l=18889, h=14706):
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
    #     FreeCAD.Vector(9440, 7350, 4450), FreeCAD.Rotation(FreeCAD.Vector(0, 0, 1), 0))
    # Front
    # pl = FreeCAD.Placement(
    #     FreeCAD.Vector(0, -1000, 0), FreeCAD.Rotation(FreeCAD.Vector(1, 0, 0), 90))
    # Right
    # pl = FreeCAD.Placement(
    #     FreeCAD.Vector(16000, 0, 0), FreeCAD.Rotation(FreeCAD.Vector(0.577, 0.577, 0.577), 120))
    # Back
    # pl = FreeCAD.Placement(
    #     FreeCAD.Vector(0, 15000, 0), FreeCAD.Rotation(FreeCAD.Vector(0, -0.71, -0.71), 180))
    # custom
    pl = FreeCAD.Placement(
        FreeCAD.Vector(9280, 7348, 1702), FreeCAD.Rotation(FreeCAD.Vector(0.577, 0.577, 0.577), 120))
    # print(pl)

    cutplane = calculateCutPlane(pl, 14706, 10915)

    # Right
    # opl = FreeCAD.Placement(
    #     FreeCAD.Vector(1000, 0, 0), FreeCAD.Rotation(FreeCAD.Vector(0.577, 0.577, 0.577), 120))
    # otherPlane = calculateCutPlane(opl)

    DEBUG = True

    render = Renderer(pl)
    render.addObjects([FreeCAD.ActiveDocument.Roof001])
    # render.addObjects([FreeCAD.ActiveDocument.Structure108])
    # render.addObjects([FreeCAD.ActiveDocument.Box,
    #                    FreeCAD.ActiveDocument.Wall003])
    # render.addObjects(FreeCAD.ActiveDocument.BuildingPart001.Group)
    # render.addObjects(FreeCAD.ActiveDocument.BuildingPart002.Group)

    # render.addSectionCuts([FreeCAD.ActiveDocument.SectionPlane026, FreeCAD.ActiveDocument.SectionPlane027])
    # render.addMarkers([FreeCAD.ActiveDocument.Rectangle033])

    tracemalloc.start()
    startTime = time.time()

    render.cut(cutplane, clip=True)
    parts = render.getSvgParts(0)

    endTime = time.time()
    top_stats = tracemalloc.take_snapshot().statistics("lineno")

    print("Needed %s s, %s MB" %(endTime - startTime, tracemalloc.get_traced_memory()[0] / 1024 / 1024))
    for stat in top_stats[:10]:
        print(stat)
    
    tracemalloc.stop()

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

        <g id="everything">
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

            <g id="section_cuts">
                SECTION_CUT_SVG
            </g>

            <g id="markers">
                MARKER_SVG
            </g>

            <g id="information">
                INFORMATION_SVG
            </g>
        </g>
    </g>
</svg>
"""
    scale = 1/50

    template = template.replace(
        "VIEWBOX_VALUES", boundBox.buildViewbox(scale, width, height))
    template = template.replace("WIDTH", toNumberString(width))
    template = template.replace("HEIGHT", toNumberString(height))
    template = template.replace(
        "PATTERN_SVG", scalePatterns(parts["patterns"], scale))
    template = template.replace("SECONDARY_SVG", parts["secondaryFaces"])
    template = template.replace("SECTION_SVG", parts["sections"])
    template = template.replace("WINDOW_SVG", parts["windows"])
    template = template.replace("SECTION_CUT_SVG", parts["sectionCuts"])
    template = template.replace("MARKER_SVG", parts["markers"])
    template = template.replace("SMALL_TEXT_FONT_SIZE", str(3 / scale))
    template = template.replace("TEXT_FONT_SIZE", str(240))
    template = template.replace("SECTION_STROKE_WIDTH", str(3))
    template = template.replace("MARKER_STROKE_WIDTH", str(0.12 / scale))
    template = template.replace("WINDOW_STROKE_WIDTH", str(1))
    template = template.replace("SECONDARY_STROKE_WIDTH", str(1))
    template = template.replace("SECTION_CUT_STROKE_WIDTH", str(0.05 / scale))

    file_object = open(
        "C:\\Meine Daten\\freecad\\samples\\SectionPlane\\Export.svg", "w")
    file_object.write(template)
    file_object.close()
