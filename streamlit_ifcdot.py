import streamlit as st
import ifcopenshell
import ifcopenshell.util.element
import tempfile
import os
import graphviz as gv
from PIL import Image
import io

# Function to write .dot file from IFC file
def write_dot(ifc_file, path_dot, interest=set()):
    ifc_objects = {}
    new_interest = interest.copy()

    with open(path_dot, "w") as dot:
        dot.write("strict graph G {\n")
        dot.write("graph [overlap=false,splines=true,rankdir=TB];\n")  # Change rankdir to TB for Top to Bottom layout

        for ifc_object in ifc_file.by_type("IfcObject"):
            if ifc_object.is_a("IfcVirtualElement"):
                continue

            ifc_objects[ifc_object.id()] = (
                "#" + str(ifc_object.id()) + "=" + str(ifc_object.is_a())
            )

            if interest and not ifc_object.id() in interest:
                continue

            if ifc_object.is_a("IfcGroup"):
                fill = "#ff99ff"
            elif ifc_object.is_a("IfcSpatialElement"):
                fill = "#ff99cc"
            elif ifc_object.is_a("IfcElementAssembly"):
                fill = "#ccff99"
            elif ifc_object.is_a("IfcOpeningElement"):
                fill = "#cc99ff"
            elif ifc_object.is_a("IfcDoor") or ifc_object.is_a("IfcWindow"):
                fill = "#99ccff"
            elif ifc_object.is_a("IfcElement"):
                fill = "#9999ff"
            elif ifc_object.is_a("IfcStructuralItem"):
                fill = "#99ff99"
            else:
                fill = "#ff9999"

            dot.write(
                '"'
                + ifc_objects[ifc_object.id()]
                + '" [color="'
                + fill
                + '",style=filled];\n'
            )

        for ifc_rel in ifc_file.by_type("IfcRelationship"):

            relating_object = None
            related_objects = []
            weight = "1"
            style = "solid"

            if ifc_rel.is_a("IfcRelAggregates"):
                relating_object = ifc_rel.RelatingObject
                related_objects = ifc_rel.RelatedObjects
                weight = "9"
            elif ifc_rel.is_a("IfcRelNests"):
                relating_object = ifc_rel.RelatingObject
                related_objects = ifc_rel.RelatedObjects
                weight = "9"
            elif ifc_rel.is_a("IfcRelAssignsToGroup"):
                relating_object = ifc_rel.RelatingGroup
                related_objects = ifc_rel.RelatedObjects
            elif ifc_rel.is_a("IfcRelConnectsElements"):
                relating_object = ifc_rel.RelatingElement
                related_objects = [ifc_rel.RelatedElement]
                weight = "9"
                style = "dashed"
            elif ifc_rel.is_a("IfcRelConnectsStructuralMember"):
                relating_object = ifc_rel.RelatingStructuralMember
                related_objects = [ifc_rel.RelatedStructuralConnection]
            elif ifc_rel.is_a("IfcRelContainedInSpatialStructure"):
                relating_object = ifc_rel.RelatingStructure
                related_objects = ifc_rel.RelatedElements
            elif ifc_rel.is_a("IfcRelFillsElement"):
                relating_object = ifc_rel.RelatingOpeningElement
                related_objects = [ifc_rel.RelatedBuildingElement]
                weight = "9"
            elif ifc_rel.is_a("IfcRelVoidsElement"):
                relating_object = ifc_rel.RelatingBuildingElement
                related_objects = [ifc_rel.RelatedOpeningElement]
                weight = "9"
            elif ifc_rel.is_a("IfcRelSpaceBoundary"):
                relating_object = ifc_rel.RelatingSpace
                related_objects = [ifc_rel.RelatedBuildingElement]
                weight = "9"
                style = "dotted"
            else:
                continue

            for related_object in related_objects:
                if (
                    relating_object.id() in ifc_objects
                    and related_object.id() in ifc_objects
                ):

                    if interest:
                        if (
                            not relating_object.id() in interest
                            and not related_object.id() in interest
                        ):
                            continue
                        if (
                            relating_object.id() in interest
                            and not related_object.id() in interest
                        ):
                            new_interest.add(related_object.id())
                            continue
                        if (
                            related_object.id() in interest
                            and not relating_object.id() in interest
                        ):
                            new_interest.add(relating_object.id())
                            continue

                    dot.write(
                        '"'
                        + ifc_objects[relating_object.id()]
                        + '"--"'
                        + ifc_objects[related_object.id()]
                        + '" ['
                        + "weight="
                        + weight
                        + ",style="
                        + style
                        + "];\n"
                    )

        for ifc_object in ifc_file.by_type("IfcSite"):
            cluster(dot, ifc_object, ifc_objects, interest)

        dot.write("}\n")
    return new_interest

def cluster(dot, ifc_object, ifc_objects, interest=set()):
    if ifc_object.is_a("IfcVirtualElement"):
        return
    if interest and not ifc_object.id() in interest:
        return
    children = ifcopenshell.util.element.get_decomposition(ifc_object)
    if children:
        dot.write("subgraph id_" + str(ifc_object.id()) + " {\n")
        dot.write("cluster=true;\n")
        dot.write('"' + ifc_objects[ifc_object.id()] + '";\n')

        for child in children:
            if child.is_a("IfcVirtualElement"):
                continue
            if interest and not child.id() in interest:
                continue
            dot.write('"' + ifc_objects[child.id()] + '";\n')
            cluster(dot, child, ifc_objects, interest=interest)
        dot.write("}\n")

st.title('Graph Visualisation of IFC Files')
st.markdown("""
App based on the [ifcdot from Bruno Postle](https://github.com/brunopostle/ifcdot/tree/main)
""")
st.markdown("""
with the use of the powerful libraries [IfcOpenShell](https://ifcopenshell.org/) and [Graphviz](https://graphviz.org/).
""")

uploaded_file = st.file_uploader("Choose an IFC file", type=["ifc"])
if uploaded_file is not None:
    st.write("File uploaded successfully")
    
    # Create a temporary file to save the uploaded IFC file
    with tempfile.NamedTemporaryFile(delete=False) as tmp_file:
        tmp_file.write(uploaded_file.read())
        tmp_file_path = tmp_file.name
    
    # Open the IFC file using ifcopenshell
    ifc_file = ifcopenshell.open(tmp_file_path)
    
    # Define the path for the output .dot file
    dot_path = os.path.join(tempfile.gettempdir(), "output_graph.dot")
    
    # Write the .dot file
    write_dot(ifc_file, dot_path)

    with open(dot_path, 'r') as file:
        dot_content = file.read()
    
    # Provide a download button for the .dot file
    st.download_button(label="Download .dot file", data=dot_content, file_name="output_graph.dot", mime="text/plain")
    
    # Generate Graphviz source object
    graph = gv.Source(dot_content)
    
    # Provide a download button for the PNG file
    try:
        png_path = os.path.join(tempfile.gettempdir(), "output_graph.png")
        graph.format = 'png'
        graph.render(filename=png_path, format='png')

        with open(png_path + '.png', 'rb') as file:
            png_content = file.read()
        
        st.download_button(label="Download PNG file", data=png_content, file_name="output_graph.png", mime="image/png")
    except gv.backend.ExecutableNotFound as e:
        st.error("Graphviz executable not found. Ensure that Graphviz is installed and added to the system PATH.")
        st.error(str(e))

    st.graphviz_chart(graph.source)

st.markdown("""
Web App prepared as part of the course [Digital Structural Design on the FH Campus Wien](https://aiztok.github.io/DiTWP/100_Informationen/120_Datenstruktur/121_VO#datenstruktur-ifc)
""")
