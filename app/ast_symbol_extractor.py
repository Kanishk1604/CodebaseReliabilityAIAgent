from tree_sitter import Parser
from tree_sitter_language_pack import get_language
from pathlib import Path

EXTENSION_TO_LANGUAGE = {
    ".ts": "typescript",
    ".tsx": "typescript",
    ".js": "javascript",
    ".jsx": "javascript",
    ".py": "python",
    ".java": "java",
    ".cs": "c_sharp",
}

SYMBOL_RULES ={
    "typescript": {
        "class_declaration": ("type_identifier", "class"),
        "method_definition": ("property_identifier", "method"),
        "interface_declaration": ("type_identifier", "interface"),
        "function_declaration": ("identifier", "function"),
        "lexical_declaration": ("identifier", "constant"),
    },
    "python":{
        "class_definition": ("identifier", "class"),
        "function_definition": ("identifier", "function"),
    },
    "java": {
        "class_declaration": ("identifier", "class"),
        "interface_declaration": ("identifier", "interface"),
        "method_declaration": ("identifier", "method"),
    },
    "c_sharp": {
        "class_declaration": ("identifier", "class"),
        "interface_declaration": ("identifier", "interface"),
        "method_declaration": ("identifier", "method"),

    },
}

IMPORT_RULES ={
    "typescript": {
        "import_statement": {
            "source_type": "string_fragment",
            "symbol_type": "import_specifier",
        }}
}

def get_language_for_extension(extension: str) -> str:
    return EXTENSION_TO_LANGUAGE.get(extension, None)

#helper
def find_child_by_type(node, child_type: str) :
    if node.type == child_type:
        return node
    
    for child in node.children:
        result = find_child_by_type(child, child_type)
        if result:
            return result

    return None

#helper
def get_node_text(node, source_bytes: bytes) -> str:
    node_text = source_bytes[node.start_byte: node.end_byte].decode("utf-8",errors = "ignore")

    return node_text

#helper
def collect_children_text_by_import(node, child_type: str, import_symbols: list[str], source_bytes: bytes):
    if node.type == child_type:
        child_str = get_node_text(node, source_bytes)
        import_symbols.append(child_str)

    for child in node.children:
        collect_children_text_by_import(child, child_type, import_symbols, source_bytes)
            
#get imports and modules used
def collect_imports(node, imports:list[dict], source_bytes: bytes, language: str):
    if node.type == None:
        return None

    rules = IMPORT_RULES.get(language, {})
    import_symbols = []

    if node.type in rules:
        name_source_type = rules[node.type]["source_type"]
        name_symbol_type = rules[node.type]["symbol_type"]

        node_source = find_child_by_type(node, name_source_type)
        collect_children_text_by_import(node, name_symbol_type, import_symbols, source_bytes)
        
        if import_symbols and node_source:
            imports.append({
                "source": get_node_text(node_source, source_bytes),
                "imported_symbols": import_symbols,
            })
    
    for child in node.children:
        collect_imports(child, imports, source_bytes, language)


#returns semantic symbols
def semantic_collector(node, symbols: list[dict], source_bytes: bytes, language: str):
    if node.type == None:
        return None

    rules = SYMBOL_RULES.get(language, {})
    if node.type in rules:
        #tuple unpacking
        #"method_definition": ("property_identifier", "method")
        # property_identifier -> name_node_type
        #method -> symbol_type
        name_node_type, symbol_type = rules[node.type]      

        node_child = find_child_by_type(node, name_node_type)

        if node_child:
            symbols.append({
                "name": get_node_text(node_child, source_bytes),
                "type": symbol_type,    
            })
    
    for child in node.children:
        semantic_collector(child, symbols, source_bytes,language)

#parse file and retireve symbols and imports
def extract_ast_symbols(file_path: Path, content: str) -> dict:
    source_bytes = content.encode()
    symbols = []
    imports = []
    language = get_language_for_extension(file_path.suffix)
    
    if not language:
        return {
            "symbols": [],
            "imports": [],
        }

    language_semantic = get_language(language)
    parser = Parser(language_semantic)

    tree = parser.parse(source_bytes)

    root = tree.root_node

    semantic_collector(root, symbols, source_bytes, language)
    collect_imports(root, imports, source_bytes, language)

   
    return {
        "symbols": symbols,
        "imports": imports
    }


def main() ->None:
    # file_path = Path("/Users/knotbott/Projects/Codebase_reliability_agent/scripts/sample.tsx")
    file_path = Path("/Users/knotbott/Projects/EnterPriseResourceDashboard/erd-web/src/app/pages/login/login.ts")
    
    content = file_path.read_text(encoding="utf-8", errors="ignore")
    # symbols = extract_ast_symbols(file_path,content)
    # imports = extract_ast_symbols(file_path,content)

    # for imported in imports:
    #     print(f"{imported['source']:10} : {imported['imported_symbols']}")

if __name__ == "__main__":
    main()