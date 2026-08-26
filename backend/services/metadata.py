import os
import ast

def get_function_tags() -> list:
    """
    Scans the backend codebase for # DETERMINISTIC and # LLM-ASSISTED tags.
    Returns a list of dicts: {"function": str, "file": str, "type": str}
    """
    backend_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    tags = []
    
    for root, _, files in os.walk(backend_dir):
        if "venv" in root or "__pycache__" in root or "tests" in root:
            continue
            
        for file in files:
            if file.endswith(".py"):
                filepath = os.path.join(root, file)
                with open(filepath, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                    
                for i, line in enumerate(lines):
                    line_stripped = line.strip()
                    if line_stripped == "# DETERMINISTIC" or line_stripped == "# LLM-ASSISTED":
                        tag_type = line_stripped.replace("# ", "")
                        # The next non-empty line should be a def
                        func_name = "unknown"
                        for j in range(i + 1, min(i + 5, len(lines))):
                            next_line = lines[j].strip()
                            if next_line.startswith("def "):
                                func_name = next_line.split("def ")[1].split("(")[0]
                                break
                        
                        tags.append({
                            "function": func_name,
                            "file": os.path.relpath(filepath, backend_dir),
                            "type": tag_type
                        })
    return tags
