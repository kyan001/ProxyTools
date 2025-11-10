#! .venv/bin/python
import os
import sys
import tempfile
import tomllib

import consoleiotools as cit
import consolecmdtools as cct

RULES_FILE = "MyRules.toml"
CLASH_RULESET_FILENAME = "Clash-Rules-MyRules.yaml"
SHADOWROCKET_MODULE_FILENAME = "Shadowrocket-Module-MyRules.sgmodule"
DIST_DIR = "autogen"


class RuleSet:
    def __init__(self) -> None:
        self.rules: list[dict] = []
        self.version: str = ""

    def from_toml(self, filename: str):
        if not filename:
            raise ValueError("filename is required")
        path = cct.get_path(filename)
        if not path.exists:
            raise FileNotFoundError(f"file not found: {path}")
        with open(path, "rb") as fl:
            toml_data = tomllib.load(fl)
        default = toml_data.get('default') or {}
        count = 0
        for r in toml_data.get('rules') or []:
            rule = {**default, **r}  # kv in r overwrites kv in default
            if not rule.get('arg'):
                cit.warn(f"Skipped! Rule has no argument: {rule}")
                continue
            if rule['policy'] not in ["PROXY", "DIRECT"]:
                cit.warn(f"Skipped! Rule policy is not supported: {rule}")
                continue
            if rule['disabled'] is True:
                cit.warn(f"Skipped! Rule is disabled: {rule}")
                continue
            count += 1
            self.rules.append(rule)
        self.version = toml_data.get('version') or "Unknown"
        cit.info(f"{count}/{len(toml_data['rules'])} rules loaded. Version {self.version}")

    @staticmethod
    def rule_comment(rule) -> str:
        comment = ["#"]
        if rule['blocked']:
            comment.append("BLOCKED!")
        if rule['redirected']:
            comment.append("REDIRECTED!")
        if rule['desc']:
            comment.append(rule['desc'])
        if len(comment) == 1:
            return ""
        return " ".join(comment)

    def to_clash_ruleset(self) -> str:
        result = [
            f"# Version {self.version}",
            "payload:"
        ]
        for rule in self.rules:
            if rule['policy'] != "PROXY":  # Clash ruleset can only be assigned a certain policy, which is usually `PROXY`
                cit.warn(f"Skipped! Rule policy is not `PROXY`: {rule}")
                continue
            text = f"  - {rule['type']},{rule['arg']}"
            comment = self.rule_comment(rule)
            if comment:
                text += "  " + comment
            result.append(text)
        return "\n".join(result)

    def to_shadowrocket_module(self) -> str:
        result = [
            "#!name=ShadowRocket My Rules",
            "#!desc=ShadowRocket My Rules",
            f"#!version={self.version}",
            "",
            "[Rule]"
        ]
        for rule in self.rules:
            if rule['policy'] != "PROXY":
                cit.warn(f"Skipped! Rule policy is not `PROXY`: {rule}")
                continue
            text = f"{rule['type']}, {rule['arg']}, {rule['policy']}"
            comment = self.rule_comment(rule)
            if comment:
                text += "  " + comment
            result.append(text)
        return "\n".join(result)

    def save_to_file(self, content: str, filepath: str):
        if not filepath:
            cit.err("No filepath specified.")
            return False
        if not content:
            cit.err("No content to save.")
            return False
        with tempfile.TemporaryDirectory() as tmp_filedir:
            path = cct.get_path(filepath)
            tmp_filepath = os.path.join(tmp_filedir, path.basename)
            current_dir = path.parent
            filepath = os.path.join(current_dir, path.basename)
            with open(tmp_filepath, "wt", encoding='utf-8') as tmp_file:
                tmp_file.write(content)
            cct.move_file(tmp_filepath, filepath, ensure=True)
            cit.info(f"File saved to {filepath}")
        return True


def main():
    rules = RuleSet()
    current_dir = cct.get_path(__file__).parent
    cit.title("Parse Rules File")
    rules_path = os.path.join(current_dir, RULES_FILE)
    cit.info(f"Rules File: {rules_path}")
    rules.from_toml(rules_path)
    # Clash
    cit.title("Generate Clash Yaml File")
    clash_ruleset_path = os.path.join(current_dir, DIST_DIR, CLASH_RULESET_FILENAME)
    clash_ruleset = rules.to_clash_ruleset()
    rules.save_to_file(clash_ruleset, clash_ruleset_path)
    # ShadowRocket
    cit.title("Generate ShadowRocket sgmodule File")
    shadowrocket_module_path = os.path.join(current_dir, DIST_DIR, SHADOWROCKET_MODULE_FILENAME)
    shadowrocket_module = rules.to_shadowrocket_module()
    rules.save_to_file(shadowrocket_module, shadowrocket_module_path)


if __name__ == "__main__":
    main()
    if "--no-pause" not in sys.argv:
        cit.pause()
