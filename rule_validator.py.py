
#!/usr/bin/env python3
import sys
import yaml
from typing import Dict, List, Any

class DetectionValidator:
    def __init__(self, rule_yaml_path: str):
        with open(rule_yaml_path, 'r', encoding='utf-8') as f:
            self.rule_data = yaml.safe_load(f)
        self.title = self.rule_data.get('title', 'Untitled Rule')
        self.detection = self.rule_data.get('detection', {})
        self.condition = self.detection.get('condition', '')

    def _match_field(self, log_value: Any, rule_pattern: Any, modifier: str) -> bool:
        if log_value is None:
            return False
        log_str = str(log_value)
        patterns = [str(p)] if not isinstance(rule_pattern, list) else [str(p) for p in rule_pattern]

        for pattern in patterns:
            if modifier == 'contains' and pattern.lower() in log_str.lower():
                return True
            elif modifier == 'endswith' and log_str.lower().endswith(pattern.lower()):
                return True
            elif modifier == 'startswith' and log_str.lower().startswith(pattern.lower()):
                return True
            elif modifier == 'exact' and log_str.lower() == pattern.lower():
                return True
        return False

    def evaluate_selection(self, log: Dict[str, Any], selection_dict: Dict[str, Any]) -> bool:
        for field_key, rule_pattern in selection_dict.items():
            field, modifier = (field_key.split('|', 1) if '|' in field_key else (field_key, 'exact'))
            val = log
            for part in field.split('.'):
                val = val.get(part) if isinstance(val, dict) else None
                if val is None: break
            if not self._match_field(val, rule_pattern, modifier):
                return False
        return True

    def test_log(self, log: Dict[str, Any]) -> bool:
        active_selection = self.condition.strip()
        if active_selection in self.detection:
            return self.evaluate_selection(log, self.detection[active_selection])
        return False

    def validate_test_suite(self, test_cases_path: str) -> dict:
        with open(test_cases_path, 'r', encoding='utf-8') as f:
            test_suite = yaml.safe_load(f)

        results = {"rule": self.title, "tp": 0, "tn": 0, "fp": 0, "fn": 0, "details": [], "passed": True}

        for idx, case in enumerate(test_suite.get('test_cases', []), 1):
            log, expected, desc = case.get('log', {}), case.get('expected_match', False), case.get('description', f'Test {idx}')
            actual = self.test_log(log)

            if expected and actual:
                results["tp"] += 1; cat, status = "True Positive (TP)", "PASS"
            elif not expected and not actual:
                results["tn"] += 1; cat, status = "True Negative (TN)", "PASS"
            elif not expected and actual:
                results["fp"] += 1; cat, status = "False Positive (FP)", "FAIL"; results["passed"] = False
            else:
                results["fn"] += 1; cat, status = "False Negative (FN)", "FAIL"; results["passed"] = False

            results["details"].append({"id": idx, "desc": desc, "expected": expected, "actual": actual, "category": cat, "status": status})
        return results

if __name__ == "__main__":
    if len(sys.argv) < 3:
        print("Usage: python rule_validator.py <rule.yml> <tests.yml>")
        sys.exit(1)
    validator = DetectionValidator(sys.argv[1])
    report = validator.validate_test_suite(sys.argv[2])
    
    print(f"\n--- Validation Report: {report['rule']} ---")
    for d in report['details']:
        print(f"[{d['status']}] Test #{d['id']}: {d['desc']} ({d['category']})")
    print(f"\nSummary: TP={report['tp']} | TN={report['tn']} | FP={report['fp']} | FN={report['fn']}")
    print(f"Overall Result: {'PASSED' if report['passed'] else 'FAILED'}\n")
    sys.exit(0 if report['passed'] else 1)