import FreeCAD
import FreeCADGui
from app import section_vector_renderer
from PySide2 import QtGui, QtCore, QtWidgets

SVG_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<svg xmlns="http://www.w3.org/2000/svg"
     xmlns:sodipodi="http://sodipodi.sourceforge.net/DTD/sodipodi-0.dtd"
     xmlns:inkscape="http://www.inkscape.org/namespaces/inkscape"
     width="210mm" height="297mm" viewBox="0 0 210 297"
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
        <g id="patterns">
            PATTERN_SVG
        </g>

        LEGEND_CONTENT
    </g>
</svg>
"""

MATERIAL_TEMPLATE = """
<g>
    <rect x="RECT_X" y="RECT_Y" height="10" width="20" stroke="#000000" stroke-width="0.5" 
        style="fill:PATH_FILL; fill-rule: evenodd; stroke-width:0.5; stroke-miterlimit:1; stroke-linejoin:round; stroke-dasharray:none;"/>
    <text
            x="TEXT_POSITION_X"
            y="TEXT_POSITION_Y"
            style="font-size:5;font-family:Arial;letter-spacing:0px;word-spacing:0px;fill:#000000;text-anchor:start;text-align:center;stroke:none;">
                TEXT_CONTENT
    </text>
</g>
"""

TOP_LEFT = FreeCAD.Vector(20, 20, 0)

def getMaterials():
    allMaterials = FreeCAD.ActiveDocument.findObjects('App::MaterialObjectPython')
    materials = []

    for mat in allMaterials:
        data = mat.Material

        if not "IGNORE_LEGEND" in data or data["IGNORE_LEGEND"] != "True":
            materials.append(mat)

    return materials

def getPatternType(mat):
    data = mat.Material

    if not "PatternType" in data:
        return None

    return data["PatternType"]

def getMaterialSvg(index, material, renderer):
    offset = FreeCAD.Vector(0, index * 12, 0)
    base = TOP_LEFT.add(offset)

    fill = "url(#%s)" % (renderer.getPattern(material.Color, getPatternType(material)), )

    svg = MATERIAL_TEMPLATE.replace("RECT_X", str(base.x))
    svg = svg.replace("RECT_Y", str(base.y))
    svg = svg.replace("PATH_FILL", fill)

    svg = svg.replace("TEXT_CONTENT", material.Label)
    svg = svg.replace("TEXT_POSITION_X", str(base.x + 30))
    svg = svg.replace("TEXT_POSITION_Y", str(base.y + 7))

    return svg


class BuildLegendCommand:
    toolbarName = 'Arch_Tools'
    commandName = 'Build_Legend'

    def GetResources(self):
        return {'MenuText': "Build Legend",
                'ToolTip': "Builds a SVG Legend of the available materials",
                # 'Pixmap': iconPath('CreateConfig.svg')
                }

    def Activated(self):
        materials = getMaterials()
        renderer = section_vector_renderer.Renderer(FreeCAD.Placement())
        renderer.patterns = {}
        content = ""

        for index, material in enumerate(materials):
            content += getMaterialSvg(index, material, renderer)
        
        svg = SVG_TEMPLATE.replace("LEGEND_CONTENT", content)
        svg = svg.replace("PATTERN_SVG", section_vector_renderer.scalePatterns(renderer.getPatternSVG(), 1))

        selectedFile = QtWidgets.QFileDialog.getSaveFileName(
            QtWidgets.QApplication.activeWindow(), caption='Export Location', filter="SVG Files (*.svg)")[0]
        file_object = open(selectedFile, "w")

        try:
            file_object.write(svg)
        finally:
            file_object.close()
            

    def IsActive(self):
        """If there is no active document we can't do anything."""
        return not FreeCAD.ActiveDocument is None


if __name__ == "__main__":
    command = BuildLegendCommand()

    if command.IsActive():
        command.Activated()
    else:
        qtutils.showInfo("No open Document", "There is no open document")
else:
    from gui import toolbar_manager
    toolbar_manager.toolbarManager.registerCommand(
        BuildLegendCommand())
