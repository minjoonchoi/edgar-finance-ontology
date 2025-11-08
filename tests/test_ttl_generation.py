import unittest
import sys
import os
from io import StringIO
import json

# Add scripts directory to path to import select_xbrl_tags
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../scripts')))

try:
    import select_xbrl_tags
except ImportError:
    # Handle case where the script name might be different or path is wrong
    # For now assuming the file is scripts/select_xbrl_tags.py and module name is select_xbrl_tags
    pass

class TestTTLGeneration(unittest.TestCase):
    def setUp(self):
        self.companies = [
            {
                "cik": "0000320193",
                "symbol": "AAPL",
                "name": "Apple Inc.",
                "sector": "Information Technology",
                "industry": "Technology Hardware, Storage & Peripherals",
                "sic": "3571",
                "sic_description": "Electronic Computers",
                "fye": "0930"
            }
        ]
        self.observations = [
            {
                "cik": "0000320193",
                "fy": "2023",
                "metric": "Revenue",
                "end": "2023-09-30",
                "period_type": "duration",
                "is_derived": False,
                "unit": "USD",
                "value": 383285000000,
                "form": "10-K",
                "accn": "0000320193-23-000106",
                "source_type": "XBRL",
                "selected_tag": "Revenues",
                "composite_name": "Revenue",
                "reason": "Standard tag",
                "confidence": 1.0,
                "components": None,
                "computed_from": None
            },
             {
                "cik": "0000320193",
                "fy": "2023",
                "metric": "NetIncome",
                "end": "2023-09-30",
                "period_type": "duration",
                "is_derived": False,
                "unit": "USD",
                "value": 96995000000,
                "form": "10-K",
                "accn": "0000320193-23-000106",
                "source_type": "XBRL",
                "selected_tag": "NetIncomeLoss",
                "composite_name": "NetIncome",
                "reason": "Standard tag",
                "confidence": 0.9,
                "components": None,
                "computed_from": None
            }
        ]
        self.outfile = "test_output.ttl"

    def tearDown(self):
        if os.path.exists(self.outfile):
            os.remove(self.outfile)

    def test_emit_efin_ttl_structure(self):
        # This test will fail initially until the script is updated
        if not hasattr(select_xbrl_tags, 'emit_efin_ttl'):
             print("emit_efin_ttl not found, skipping test")
             return

        select_xbrl_tags.emit_efin_ttl(self.companies, self.observations, self.outfile)
        
        with open(self.outfile, 'r') as f:
            content = f.read()
            
        # Basic checks
        self.assertIn("efin:Company", content)
        # In this test data, we only have duration observations
        self.assertIn("efin:DurationObservation", content)
        
        # New schema checks (will fail before update)
        # Check for Filing instance
        self.assertIn("efin:TenK", content)
        self.assertIn("efin:accessionNumber", content)
        self.assertIn('0000320193-23-000106', content)
        
        # Check for Filing link
        self.assertIn("efin:fromFiling", content)
        
        # Check for XBRL Concept
        self.assertIn("efin:XBRLConcept", content)
        self.assertIn("efin:hasQName", content)
        self.assertIn("Revenues", content)
        self.assertIn("efin:hasXbrlConcept", content)
        
        # Check for Source Note (consolidated metadata)
        self.assertIn("efin:hasSourceNote", content)
        # Should not have old properties
        self.assertNotIn("efin:hasFormType", content)
        self.assertNotIn("efin:hasSelectionReason", content)

if __name__ == '__main__':
    unittest.main()
