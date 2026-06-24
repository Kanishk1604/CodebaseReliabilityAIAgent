import re

def extract_symbol_metadata(chunk_content: str, extension: str) -> dict:

    #typescript file detection
    if extension in {".ts", ".tsx"}:
        match_class = re.search(r"class\s+(\w+)", chunk_content)
        if match_class: 
            return{
                "symbol": match_class.group(1),
                "symbol_type": "class",
            }

        match_interface = re.search(r"interface\s+(\w+)",chunk_content) 
        if match_interface:
            return{
                "symbol": match_interface.group(1),
                "symbol_type": "interface",
            }

        match_function = re.search(r"function\s+(\w+)",chunk_content)
        if match_function:
            return{
                "symbol":match_function.group(1),
                "symbol_type": "function",
            }
        
    if extension == ".cs":
        match_class2 = re.search(r"class\s+(\w+)", chunk_content)
        if match_class2: 
            return{
                "symbol": match_class2.group(1),
                "symbol_type": "class",
            }

        match_interface2 = re.search(r"interface\s+(\w+)",chunk_content) 
        if match_interface2:
            return{
                "symbol": match_interface2.group(1),
                "symbol_type": "interface",
            }

        match_method = re.search(r"Task<IActionResult>\s+(\w+)",chunk_content)
        if match_method:
            return{
                "symbol":match_method.group(1),
                "symbol_type": "method",
            }
        
        match_method2 = re.search(r"public\s+void\s+(\w+)",chunk_content)
        if match_method2:
            return{
                "symbol":match_method2.group(1),
                "symbol_type": "method",
            }

        
    
    return{
        "symbol": None,
        "symbol_type": "unknown",
    }