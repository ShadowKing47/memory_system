from pathlib import Path
import re


class PromptLoader:
    def __init__(self, prompts_dir: Path | str = "src/memory/prompts"):
        self._dir = Path(prompts_dir)
        if not self._dir.exists():
            raise FileNotFoundError(f"Prompts directory not found: {self._dir}")
    
    def load(self, name: str, version: str = "latest") -> str:
        if version == "latest":
            return self._load_latest(name)
        return self._load_specific(name, version)
    
    def _load_latest(self, name: str) -> str:
        pattern = f"{name}_v*.txt"
        files = list(self._dir.glob(pattern))
        if not files:
            raise FileNotFoundError(f"No prompt files found for {name} in {self._dir}")
        
        # Extract version numbers and sort
        versioned = []
        for f in files:
            match = re.search(r"_v(\d+)\.txt$", f.name)
            if match:
                versioned.append((int(match.group(1)), f))
        
        if not versioned:
            raise ValueError(f"No valid versioned prompt files for {name}")
        
        versioned.sort(key=lambda x: x[0], reverse=True)
        latest_file = versioned[0][1]
        return latest_file.read_text(encoding="utf-8")
    
    def _load_specific(self, name: str, version: str) -> str:
        # Support "v1", "1", "v2", "2" formats
        version = version.lstrip("v")
        if not version.isdigit():
            raise ValueError(f"Invalid version format: {version}")
        
        file_path = self._dir / f"{name}_v{version}.txt"
        if not file_path.exists():
            raise FileNotFoundError(f"Prompt version not found: {file_path}")
        
        return file_path.read_text(encoding="utf-8")
    
    def list_versions(self, name: str) -> list[int]:
        pattern = f"{name}_v*.txt"
        files = list(self._dir.glob(pattern))
        versions = []
        for f in files:
            match = re.search(r"_v(\d+)\.txt$", f.name)
            if match:
                versions.append(int(match.group(1)))
        return sorted(versions)