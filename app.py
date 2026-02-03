from __future__ import annotations

import os

from src.ui_main import launch_app


def main() -> None:
    root_dir = os.path.dirname(os.path.abspath(__file__))
    project_path = os.path.join(root_dir, "data", "project.json")
    profile_path = os.path.join(root_dir, "config", "parser_profiles.json")
    rules_path = os.path.join(root_dir, "config", "spec_rules.json")
    launch_app(project_path, profile_path, rules_path)


if __name__ == "__main__":
    main()
