# 1. Load evals/retrieval_cases.json
# 2. For each case, call search_codebase(question, limit=5)
# 3. Collect retrieved file_path values
# 4. Check if any expected_files appear in top 5
# 5. Print PASS/FAIL
# 6. Print final accuracy

import json

from app.retriever import search_codebase

from pathlib import Path

def show_eval() -> list[dict]:
    project_root = Path(__file__).parent.parent
    eval_file = project_root/"evals"/"retrieval_cases.json"

    # with open(eval_file, "r") as f:
    retrieval_cases = json.loads(eval_file.read_text())

    # print(type(retrieval_cases))
    
    eval_rating = []
    
    for case in retrieval_cases:
        file_status = "FAIL"
        symbol_status = "FAIL"
        file_names_found = []
        retrieved_symbols = []
        chunks = search_codebase(case["question"], 5)
        retrieved_files = [chunk["file_path"] for chunk in chunks]
        top_1 = retrieved_files[:1]
        top_3 = retrieved_files[:3]
        top_5 = retrieved_files[:5]

        top_1_file_status = "FAIL"
        top_3_file_status = "FAIL"
        top_5_file_status = "FAIL"

        for chunk in chunks:  
            if chunk["file_path"] in case["expected_files"]:
                if chunk["file_path"] in top_1:
                    top_1_file_status = "PASS"
                if chunk["file_path"] in top_3:
                    top_3_file_status = "PASS"
                if chunk["file_path"] in top_5:
                    top_5_file_status = "PASS"
                
                file_status = "PASS"
                file_names_found.append(chunk["file_path"])
            
            for symbol in chunk.get("semantic_symbols", []):
                if symbol.get("symbol_name") in case["expected_symbols"]:
                    symbol_status = "PASS"
                    retrieved_symbols.append(symbol.get("symbol_name"))
                
        eval_rating.append({
            "question": case["question"],
            "file_status": file_status,
            "symbol_status": symbol_status,
            "files": file_names_found,
            "symbols": retrieved_symbols,
            "top_1_status": top_1_file_status,
            "top_3_status": top_3_file_status,
            "top_5_status": top_5_file_status,
        })

    return eval_rating    

def main() ->None:
    evaluated_rating = show_eval()

    passed = sum(1 for item in evaluated_rating if item["file_status"] == "PASS")
    passed_symbol = sum(1 for item in evaluated_rating if item["symbol_status"] == "PASS")
    
    passed_top_1 = sum(1 for item in evaluated_rating if item["top_1_status"] == "PASS")
    passed_top_3 = sum(1 for item in evaluated_rating if item["top_3_status"] == "PASS")
    passed_top_5 = sum(1 for item in evaluated_rating if item["top_5_status"] == "PASS")
    
    total = len(evaluated_rating)
    
    for item in evaluated_rating:
        print(
            f"{item['file_status']}/{item['symbol_status']}/{item['top_1_status']}/{item['top_3_status']}/{item['top_5_status']} | "
            f"{item['question']} | "
            f"files={item['files']} | "
            f"symbols={item['symbols']}"
        )
    
    print(f"\nFiles: Overall {passed}/{total} passed ({passed / total * 100:.1f})")
    print(f"\nSymbols: Overall {passed_symbol}/{total} passed ({passed_symbol / total * 100:.1f})")
    
    print(f"\nTop 1: {passed_top_1}/{total} passed")
    print(f"\nTop 3: {passed_top_3}/{total} passed")
    print(f"\nTop 5: {passed_top_5}/{total} passed")

if __name__ == "__main__":
    main()