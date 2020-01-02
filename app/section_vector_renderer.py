import FreeCAD
import math
import Part
import ArchCommands
import DraftVecUtils
import DraftGeomUtils

MAXLOOP = 10  # the max number of loop before abort

DEBUG = FreeCAD.ParamGet(
    "User parameter:BaseApp/Preferences/Mod/Arch").GetBool("ShowVRMDebug")

PATTERN_TEMPLATE = """
<pattern
    id="PATTERN_ID"
    patternUnits="userSpaceOnUse"
    patternTransform="matrix(5,0,0,5,0,0)"
    x="0" y="0" width="10" height="10">
        <g>
            <rect width="10" height="10" 
                style="stroke:none; fill:#ffffff" />
                <path style="stroke:PATTERN_COLOR; stroke-width:1" d="M0,0 l10,10" />
        </g>
</pattern>
"""

PATH_TEMPLATE = """
<path d="PATH_DATA" stroke="#000000" stroke-width="STROKE_WIDTH"
      style="fill:PATH_FILL; fill-rule: evenodd; stroke-width:STROKE_WIDTH; stroke-miterlimit:1; stroke-linejoin:round; stroke-dasharray:none;"/>
"""


def toNumberString(val):
    return str(round(val, DraftVecUtils.precision()))


class Renderer:
    def __init__(self, placement):
        import WorkingPlane

        self.reset()
        self.wp = WorkingPlane.plane()
        self.wp.setFromPlacement(placement)

        if DEBUG:
            print("Renderer initialized on " + str(self.wp))

    def __str__(self):
        return "Arch Renderer: " + str(len(self.faces)) + " faces projected on " + str(self.wp)

    def reset(self):
        "removes all faces from this renderer"
        self.objects = []
        self.shapes = []
        self.faces = []
        self.resetFlags()

    def resetFlags(self):
        "resets all flags of this renderer"
        self.oriented = False
        self.trimmed = False
        self.sorted = False
        self.iscut = False
        self.joined = False
        self.sections = []
        self.hiddenEdges = []

    def addObjects(self, objs):
        "add objects to this renderer"

        for o in objs:
            if o.isDerivedFrom("Part::Feature"):
                self.objects.append(o)
                color = o.ViewObject.ShapeColor
                if o.Shape.Faces:
                    self.shapes.append([o.Shape, color])

        self.resetFlags()

        if DEBUG:
            print("adding ", len(self.objects), " objects, ")

    def reorient(self):
        "reorients the faces on the WP"

        if self.sections:
            self.sections = [self.projectFace(f) for f in self.sections]
        if self.hiddenEdges:
            self.hiddenEdges = [self.projectEdge(e) for e in self.hiddenEdges]

        self.oriented = True

    def projectFace(self, face):
        "projects a single face on the WP"
        #print("VRM: projectFace start: ",len(face[0].Vertexes)," verts, ",len(face[0].Edges)," edges")
        wires = []
        if not face[0].Wires:
            if DEBUG:
                print("Error: Unable to project face on the WP")
            return None
        norm = face[0].normalAt(0, 0)
        for w in face[0].Wires:
            verts = []
            edges = Part.__sortEdges__(w.Edges)
            #print(len(edges)," edges after sorting")
            for e in edges:
                v = e.Vertexes[0].Point
                # print(v)
                v = self.wp.getLocalCoords(v)
                verts.append(v)
            verts.append(verts[0])
            if len(verts) > 2:
                #print("new wire with ",len(verts))
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
            #print("VRM: projectFace end: ",len(sh.Vertexes)," verts")
            return [sh]+face[1:]

    def projectEdge(self, edge):
        "projects a single edge on the WP"
        if len(edge.Vertexes) > 1:
            v1 = self.wp.getLocalCoords(edge.Vertexes[0].Point)
            v2 = self.wp.getLocalCoords(edge.Vertexes[-1].Point)
            return Part.LineSegment(v1, v2).toShape()
        return edge

    def cut(self, cutplane, hidden=False):
        "Cuts through the shapes with a given cut plane and builds section faces"
        if DEBUG:
            print("\n\n======> Starting cut\n\n")

        if self.iscut:
            return

        if not self.shapes:
            if DEBUG:
                print("No objects to make sections")
        else:
            shps = []

            for sh in self.shapes:
                shps.append(sh[0])

            cutface, cutvolume, invcutvolume = ArchCommands.getCutVolume(
                cutplane, shps)

            if cutface and cutvolume:
                shapes = []
                sections = []

                for sh in self.shapes:
                    for sol in sh[0].Solids:
                        c = sol.cut(cutvolume)
                        shapes.append([c]+sh[1:])

                        for f in c.Faces:
                            if DraftGeomUtils.isCoplanar([f, cutface]):
                                print("COPLANAR")
                                sections.append([f, sh[1]])

                        if hidden:
                            c = sol.cut(invcutvolume)
                            self.hiddenEdges.extend(c.Edges)

                self.shapes = shapes
                self.sections = sections

                if DEBUG:
                    print("Built ", len(self.sections), " sections, ",
                          len(self.faces), " faces retained")

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

    def getPattern(self, color):
        fill = self.getFill(color)
        pattern_id = "stripes-" + fill.replace("#", "")

        if not pattern_id in self.patterns:
            pattern = PATTERN_TEMPLATE.replace("PATTERN_ID", pattern_id)
            pattern = pattern.replace("PATTERN_COLOR", fill)

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

    def getSectionSVG(self, linewidth=1):
        "Returns a SVG fragment from cut faces"
        if not self.oriented:
            self.reorient()

        self.patterns = {}

        sectionsvg = ''

        for f in self.sections:
            if f:
                fill = 'url(#' + self.getPattern(f[1]) + ')'

                pathdata = ''

                for w in f[0].Wires:
                    pathdata += self.getPathData(w)

                current = PATH_TEMPLATE.replace("PATH_FILL", fill)
                current = current.replace("STROKE_WIDTH", str(linewidth))
                current = current.replace("PATH_DATA", pathdata)

                sectionsvg += current + "\n"

        return self.getPatternSVG() + sectionsvg

    def getHiddenSVG(self, linewidth=0.02):
        "Returns a SVG fragment from cut geometry"
        if DEBUG:
            print("Printing ", len(self.sections), " hidden faces")
        if not self.oriented:
            self.reorient()
        svg = '<g stroke="#000000" stroke-width="' + \
            str(linewidth) + '" style="stroke-width:' + str(linewidth)
        svg += ';stroke-miterlimit:1;stroke-linejoin:round;stroke-dasharray:0.09,0.05;fill:none;">\n'
        for e in self.hiddenEdges:
            svg += '<path '
            svg += 'd="'
            svg += self.getPathData(e)
            svg += '"/>\n'
        svg += '</g>\n'
        return svg
