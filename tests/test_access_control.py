# ============================== tests/test_access_control.py ==============================
import pytest

def test_client_access_only_own_jobs(mock_db):
    # TODO: simulate client requesting another client's job
    pass

def test_vendor_cannot_access_other_clients(mock_db):
    # TODO: simulate vendor restricted query
    pass

def test_lead_has_no_private_access(mock_db):
    # TODO: simulate lead fetching KB
    pass