"""
Synchronize build scripts and config files across multiple repositories.

Source directory:
- Has files
- If file is empty, only check if it exists in target directory

Target directories:
- Will certainly have additional files, those will not be removed.
- No particular solution for how to remove a previously synced file
- Change detection assumes text files and CR, CRLF differences are not significant
"""
import difflib
import shutil
from pathlib import Path
import logging

from rich.console import Console
from rich.text import Text

LOGGER = logging.getLogger(__name__)

class TemplateSync:
    """
    A class to synchronize template directories across multiple target directories, with detailed file comparison.
    """
    def __init__(self, template_dir: Path) -> None:
        """
        Initializes the TemplateSync with a source template directory.
        """
        self.template_dir = template_dir
        self.console = Console()
        self.project_name_token = "{{{PROJECT_NAME}}}"

    def report_differences(self, target_dirs: list[Path]) -> None:
        """
        Reports detailed differences between the template directory and each target directory.
        """
        differences = self._report_differences_data(target_dirs)
        print(differences)
        for target_dir, diff_files in differences.items():
            if diff_files:
                print(f"Differences in {target_dir}: {diff_files}")
            else:
                print(f"No differences in {target_dir}")

        self.report_content_differences(target_dirs)

    def _report_differences_data(self, target_dirs: list[Path]) -> dict[str, list[dict[str, str]]]:
        differences = {}
        for target_path in target_dirs:
            LOGGER.info(f"Comparing {self.template_dir} to {target_path}")
            if target_path.is_file():
                project_name = target_path.parent.name
            else:
                project_name = target_path.name
            differences[str(target_path)] = self._compare_directories(target_path,project_name)

        return differences

    def report_content_differences(self, target_dirs: list[Path]) -> None:
        """
        Reports detailed differences between the template directory and each target directory, displaying rich diffs for files with different contents.
        """
        for target_path in target_dirs:
            if target_path.is_file():
                project_name = target_path.parent.name
            else:
                project_name = target_path.name
            LOGGER.info(f"Comparing {project_name} to {target_path.name}")
            differences = self._compare_directories(target_path, project_name)
            for diff in differences:
                if diff.get('difference') == 'different contents':
                    self._display_diff(self.template_dir / diff['file'], target_path / diff['file'], project_name)
                elif diff.get('difference') == 'different length':
                    self.console.print(f"Files {self.template_dir / diff['file']} and {target_path / diff['file']} have different lengths.")
                elif diff.get('difference') == 'missing':
                    self.console.print(f"File {self.template_dir / diff['file']} is missing in {target_path / diff['file']}.")

    def sync_template(self, target_dirs: list[str]) -> None:
        """
        Synchronizes the template directory with each target directory.
        """
        for target_dir in target_dirs:
            target_path = Path(target_dir)
            # This is a convention that might not be true for all projects.
            if target_path.is_file():
                project_name = target_path.parent.name
            else:
                project_name = target_path.name
            self._copy_template(target_path, project_name)

    def _compare_directories(self, target_dir: Path, project_name:str="") -> list[dict[str, str]]:
        """
        Compares the template directory with a target directory to find detailed differences.
        """
        differences = []
        for template_file in self.template_dir.glob('**/*'):
            if template_file.is_file():
                relative_path = template_file.relative_to(self.template_dir)
                target_file = target_dir / relative_path
                if not target_file.exists():
                    differences.append({"file": str(relative_path), "difference": "missing"})
                else:
                    difference = self._compare_files(template_file, target_file, project_name)
                    if difference:
                        differences.append({"file": str(relative_path), **difference})

        return differences

    def _compare_files(self, template: Path, target: Path, project_name:str="") -> dict[str, str]:
        """
        Compares two files, insensitive to CR/LF differences, and returns the nature of the difference.
        """
        target_lines, template_lines = self.apply_light_templating(target, template, project_name)
        if not template_lines:
            return {"difference": "Empty templates match all file contents."}
        if template_lines != target_lines:
            if len(template_lines) != len(target_lines):
                return {"difference": "different length"}
            else:
                return {"difference": "different contents"}
        return {}

    def apply_light_templating(self, target:Path, template:Path, project_name:str)->tuple[list[str], list[str]]:
        with open(template, 'r', encoding='utf-8', newline=None) as template_handle, \
                open(target, 'r', encoding='utf-8', newline=None) as target_handle:
            template_lines = [line.replace(self.project_name_token, project_name) for line in
                              template_handle.readlines()]
            target_lines = target_handle.readlines()
        return target_lines, template_lines

    def _copy_template(self, target_dir: Path, project_name:str) -> None:
        """
        Copies the template directory to a target directory.
        """
        for template_file in self.template_dir.glob('**/*'):
            if template_file.is_file():
                relative_path = template_file.relative_to(self.template_dir)
                target_file = target_dir / relative_path
                target_file.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(template_file, target_file)
                LOGGER.info(f"Copied {template_file} to {target_file}")

    def _display_diff(self, template: Path, target: Path, project_name:str) -> None:
        """
        Displays a rich diff of the contents of two files.
        """
        target_lines, template_lines = self.apply_light_templating(target, template, project_name)
        diff = difflib.unified_diff(target_lines, template_lines, fromfile=str(template), tofile=str(target))
        diff_text = ''.join(diff)
        self.console.print(Text(diff_text, style="diff.removed"))

if __name__ == "__main__":
    def run()->None:
        logging.basicConfig(level=logging.INFO)
        sync = TemplateSync(Path("E:\\github\\build_templates\\pypi_library"))
        target_directories = [Path("E:\\github\\dedlin"), Path("E:\\github\\llm_build")]
        differences = sync.report_differences(target_directories)


        # sync.sync_template(target_directories)
    run()
