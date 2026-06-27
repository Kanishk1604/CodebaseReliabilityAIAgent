from tree_sitter import Parser
from tree_sitter_language_pack import get_language
from pathlib import Path


def find_child_by_type(node, child_type: str) :
    
    if node.type == child_type:
        return node

    for child in node.children:
       result = find_child_by_type(child, child_type)

       if result:
        return result
    
    return None
    


#getting the node text
def get_node_text(node, source_bytes: bytes) -> str:
    
    node_text = source_bytes[node.start_byte: node.end_byte].decode("utf-8",errors = "ignore")
    # preview = " ".join(node_text.strip().split())[:80]      #get the text for the node

    return node_text
    
#printing the entire tree / source file using AST retrieval
def print_tree(node, source_bytes: bytes, indent:int = 0, max_depth :int =4) -> None:
    if indent > max_depth:
        return 

    node_text = source_bytes[node.start_byte: node.end_byte].decode("utf-8",errors = "ignore")
    
    # #strip() -> removes trailaing and beigninig whitespaces
    # #split() -> splits on any whitespace: spaces, tabs, newlines and creates list of elements
    # #join() -> joins the list of element with the specified character, here " "
    preview = " ".join(node_text.strip().split())[:80]

    print(
        f"{' ' * indent}"
        f"type={node.type}, "
        f"start={node.start_point}, "
        f"end={node.end_point}, "
        f"text='{preview}'"
    )

    for child in node.children:
        print_tree(child,source_bytes,indent+1,max_depth)


def collect_symbol(node, source_bytes: bytes, symbols: list[dict]) -> None:
    
    if node.type == None:
        return None 

    if node.type == "class_declaration":
        class_node = find_child_by_type(node, "type_identifier")

        if class_node:
            symbols.append({
                "name": get_node_text(class_node,source_bytes),
                "type": "class",
            }) 

    if node.type == "method_definition":
        method_node = find_child_by_type(node, "property_identifier")

        if method_node:
            symbols.append({
                "name": get_node_text(method_node,source_bytes),
                "type": "method",
            }) 

    if node.type == "interface_declaration":
        interface_node = find_child_by_type(node, "type_identifier")

        if interface_node:
            symbols.append({
                "name": get_node_text(interface_node,source_bytes),
                "type": "interface",
            }) 

    if node.type == "function_declaration":
        function_node = find_child_by_type(node, "identifier")

        if function_node:
            symbols.append({
                "name": get_node_text(function_node,source_bytes),
                "type": "function",
            }) 

    for child in node.children:
        collect_symbol(child, source_bytes, symbols)

def main() -> None:

    file_path = Path("/Users/knotbott/Projects/Codebase_reliability_agent/scripts/sample.tsx")

    source_bytes = file_path.read_bytes()

    language = get_language("typescript")
    parser = Parser(language)

    tree = parser.parse(source_bytes)

    # print("TREE TYPE:", type(tree))
    # print("TREE DIR HAS:", [name for name in dir(tree) if "root" in name])
    # print("ROOT_NODE RAW:", tree.root_node)
    # print("ROOT_NODE TYPE:", type(tree.root_node))

    root = tree.root_node

    # print("ROOT TYPE:", type(root))

    # print("ROOT RAW:", root)
    # print("ROOT STR:", str(root))
    # print("ROOT REPR:", repr(root))

    # print("ROOT DIR TYPE-ISH:", [name for name in dir(root) if "type" in name])
    # print("ROOT DIR POINT-ISH:", [name for name in dir(root) if "point" in name])
    # print("ROOT DIR BYTE-ISH:", [name for name in dir(root) if "byte" in name])
    # print("ROOT DIR CHILD-ISH:", [name for name in dir(root) if "child" in name])

    print("ROOT NODE")
    print(f"type={root.type}")
    print(f"start={root.start_point}")
    print(f"end={root.end_point}")
    print()

    print("TREE")
    print_tree(root, source_bytes)
    
    symbols = []
    # collect_symbol(root,source_bytes,symbols)

    # for symbol in symbols:
    #     print(f"{symbol['type']:10} : {symbol['name']}")


if __name__ == "__main__":
    main()