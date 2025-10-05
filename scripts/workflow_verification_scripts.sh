#!/usr/bin/env python3
"""
Workflow Verification Script
Checks if the workflow is using new agents or old nodes
"""

import os
import sys
from pathlib import Path
from typing import List, Tuple, Dict
import re

class WorkflowVerifier:
    def __init__(self, project_root: str = "."):
        self.project_root = Path(project_root)
        self.results = {
            "workflow_uses_agents": False,
            "workflow_uses_nodes": False,
            "old_node_references": [],
            "agent_references": [],
            "test_references": [],
            "warnings": [],
            "errors": []
        }
    
    def check_workflow_file(self) -> Dict:
        """Check the workflow file for imports and usage"""
        workflow_file = self.project_root / "src" / "workflow" / "ai_receptionist_workflow.py"
        
        if not workflow_file.exists():
            self.results["errors"].append(f"Workflow file not found: {workflow_file}")
            return self.results
        
        with open(workflow_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for old node imports
        old_node_patterns = [
            r'from\s+src\.nodes\.identity_checker\s+import',
            r'from\s+src\.nodes\.intent_analyzer\s+import',
            r'from\s+src\.nodes\.response_generator\s+import',
            r'IdentityChecker\(',
            r'IntentAnalyzer\(',
            r'ResponseGenerator\('
        ]
        
        for pattern in old_node_patterns:
            matches = re.findall(pattern, content)
            if matches:
                self.results["workflow_uses_nodes"] = True
                self.results["old_node_references"].append({
                    "file": "ai_receptionist_workflow.py",
                    "pattern": pattern,
                    "matches": matches
                })
        
        # Check for new agent imports
        agent_patterns = [
            r'from\s+src\.agents\.receptionist_l1\s+import',
            r'from\s+src\.agents\.l2_agent_factory\s+import',
            r'from\s+src\.agents\.l3_agent_factory\s+import',
            r'ReceptionistL1\(',
            r'L2AgentFactory\(',
            r'L3AgentFactory\('
        ]
        
        for pattern in agent_patterns:
            matches = re.findall(pattern, content)
            if matches:
                self.results["workflow_uses_agents"] = True
                self.results["agent_references"].append({
                    "file": "ai_receptionist_workflow.py",
                    "pattern": pattern,
                    "matches": matches
                })
        
        return self.results
    
    def check_test_files(self) -> Dict:
        """Check test files for references to old nodes"""
        tests_dir = self.project_root / "tests"
        
        if not tests_dir.exists():
            self.results["warnings"].append(f"Tests directory not found: {tests_dir}")
            return self.results
        
        old_node_patterns = [
            (r'from\s+src\.nodes\.identity_checker\s+import', "identity_checker import"),
            (r'from\s+src\.nodes\.intent_analyzer\s+import', "intent_analyzer import"),
            (r'from\s+src\.nodes\.response_generator\s+import', "response_generator import"),
            (r'IdentityChecker\(', "IdentityChecker usage"),
            (r'IntentAnalyzer\(', "IntentAnalyzer usage"),
            (r'ResponseGenerator\(', "ResponseGenerator usage")
        ]
        
        for test_file in tests_dir.glob("test_*.py"):
            with open(test_file, 'r', encoding='utf-8') as f:
                content = f.read()
            
            for pattern, description in old_node_patterns:
                matches = re.findall(pattern, content)
                if matches:
                    self.results["test_references"].append({
                        "file": test_file.name,
                        "pattern": description,
                        "count": len(matches)
                    })
        
        return self.results
    
    def check_main_file(self) -> Dict:
        """Check main.py for old node usage"""
        main_file = self.project_root / "main.py"
        
        if not main_file.exists():
            self.results["warnings"].append(f"main.py not found: {main_file}")
            return self.results
        
        with open(main_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for old imports
        if "from src.nodes" in content:
            self.results["old_node_references"].append({
                "file": "main.py",
                "pattern": "imports from src.nodes",
                "matches": re.findall(r'from src\.nodes\.[a-z_]+', content)
            })
        
        return self.results
    
    def scan_all_files(self) -> Dict:
        """Scan all Python files for old node references"""
        python_files = []
        
        # Scan src directory
        src_dir = self.project_root / "src"
        if src_dir.exists():
            python_files.extend(src_dir.rglob("*.py"))
        
        old_references = {}
        
        for py_file in python_files:
            # Skip the old node files themselves
            if "src/nodes/" in str(py_file) and py_file.stem in ["identity_checker", "intent_analyzer", "response_generator"]:
                continue
            
            try:
                with open(py_file, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Look for imports
                old_imports = re.findall(
                    r'from\s+src\.nodes\.(identity_checker|intent_analyzer|response_generator)\s+import',
                    content
                )
                
                if old_imports:
                    rel_path = py_file.relative_to(self.project_root)
                    old_references[str(rel_path)] = old_imports
            
            except Exception as e:
                self.results["warnings"].append(f"Could not read {py_file}: {e}")
        
        if old_references:
            self.results["old_node_references"].append({
                "scan_type": "full_project_scan",
                "files_with_old_imports": old_references
            })
        
        return self.results
    
    def generate_report(self) -> str:
        """Generate a human-readable report"""
        report = []
        report.append("=" * 80)
        report.append("WORKFLOW VERIFICATION REPORT")
        report.append("=" * 80)
        report.append("")
        
        # Status Summary
        report.append("STATUS SUMMARY:")
        report.append("-" * 80)
        
        if self.results["workflow_uses_agents"]:
            report.append("✅ Workflow IS using new agents (src/agents/)")
        else:
            report.append("❌ Workflow NOT using new agents")
        
        if self.results["workflow_uses_nodes"]:
            report.append("⚠️  Workflow STILL using old nodes (src/nodes/)")
        else:
            report.append("✅ Workflow NOT using old nodes")
        
        report.append("")
        
        # Errors
        if self.results["errors"]:
            report.append("ERRORS:")
            report.append("-" * 80)
            for error in self.results["errors"]:
                report.append(f"❌ {error}")
            report.append("")
        
        # Old Node References
        if self.results["old_node_references"]:
            report.append("OLD NODE REFERENCES FOUND:")
            report.append("-" * 80)
            for ref in self.results["old_node_references"]:
                if "file" in ref:
                    report.append(f"📄 File: {ref['file']}")
                    report.append(f"   Pattern: {ref['pattern']}")
                    if "matches" in ref:
                        report.append(f"   Matches: {len(ref['matches'])} occurrences")
                elif "scan_type" in ref:
                    report.append(f"🔍 Full Project Scan Results:")
                    for file, imports in ref["files_with_old_imports"].items():
                        report.append(f"   📄 {file}: {', '.join(imports)}")
            report.append("")
        else:
            report.append("✅ NO OLD NODE REFERENCES FOUND")
            report.append("")
        
        # Agent References
        if self.results["agent_references"]:
            report.append("NEW AGENT REFERENCES FOUND:")
            report.append("-" * 80)
            for ref in self.results["agent_references"]:
                report.append(f"📄 File: {ref['file']}")
                report.append(f"   Pattern: {ref['pattern']}")
                report.append(f"   Matches: {len(ref['matches'])} occurrences")
            report.append("")
        
        # Test References
        if self.results["test_references"]:
            report.append("TEST FILE REFERENCES TO OLD NODES:")
            report.append("-" * 80)
            for ref in self.results["test_references"]:
                report.append(f"📄 Test: {ref['file']}")
                report.append(f"   Pattern: {ref['pattern']}")
                report.append(f"   Count: {ref['count']}")
            report.append("")
        
        # Warnings
        if self.results["warnings"]:
            report.append("WARNINGS:")
            report.append("-" * 80)
            for warning in self.results["warnings"]:
                report.append(f"⚠️  {warning}")
            report.append("")
        
        # Recommendations
        report.append("RECOMMENDATIONS:")
        report.append("-" * 80)
        
        if self.results["workflow_uses_nodes"] and not self.results["workflow_uses_agents"]:
            report.append("❗ CRITICAL: Workflow needs to be updated!")
            report.append("   1. Update src/workflow/ai_receptionist_workflow.py")
            report.append("   2. Replace old node imports with agent imports")
            report.append("   3. Update workflow graph to use 3-tier routing")
        elif self.results["workflow_uses_nodes"] and self.results["workflow_uses_agents"]:
            report.append("⚠️  WARNING: Workflow has mixed old/new references!")
            report.append("   1. Remove old node imports completely")
            report.append("   2. Verify all nodes use agent system")
        elif not self.results["workflow_uses_agents"]:
            report.append("❗ Workflow doesn't use agents or nodes!")
            report.append("   Check if workflow file is correct")
        else:
            report.append("✅ Workflow is properly using new agent system!")
        
        if self.results["test_references"]:
            report.append("")
            report.append("📝 Update test files:")
            report.append("   - Update imports to use src.agents instead of src.nodes")
            report.append("   - Update test assertions for new agent system")
        
        if self.results["old_node_references"]:
            report.append("")
            report.append("🗑️  After verification, you can delete:")
            report.append("   - src/nodes/identity_checker.py")
            report.append("   - src/nodes/intent_analyzer.py")
            report.append("   - src/nodes/response_generator.py")
        
        report.append("")
        report.append("=" * 80)
        
        return "\n".join(report)


def main():
    """Run the verification"""
    print("Starting Workflow Verification...\n")
    
    verifier = WorkflowVerifier(".")
    
    print("1. Checking workflow file...")
    verifier.check_workflow_file()
    
    print("2. Checking test files...")
    verifier.check_test_files()
    
    print("3. Checking main.py...")
    verifier.check_main_file()
    
    print("4. Scanning all files...")
    verifier.scan_all_files()
    
    print("\n")
    report = verifier.generate_report()
    print(report)
    
    # Write report to file
    with open("workflow_verification_report.txt", "w") as f:
        f.write(report)
    
    print("\nReport saved to: workflow_verification_report.txt")
    
    # Exit code based on status
    if verifier.results["workflow_uses_agents"] and not verifier.results["workflow_uses_nodes"]:
        print("\n✅ Verification PASSED - Workflow is properly migrated!")
        sys.exit(0)
    else:
        print("\n⚠️  Verification INCOMPLETE - Action required!")
        sys.exit(1)


if __name__ == "__main__":
    main()